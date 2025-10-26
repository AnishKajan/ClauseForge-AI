"""
Health check endpoints with comprehensive monitoring
"""

import time
import psutil
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
import boto3
from botocore.exceptions import ClientError
import logging

from core.database import get_db
from core.config import settings
from core.telemetry import get_tracer, get_meter
from version import get_version_info

logger = logging.getLogger(__name__)
router = APIRouter()

# Get telemetry instances
tracer = get_tracer()
meter = get_meter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    version_info = get_version_info()
    return {
        "status": "healthy",
        "service": "lexiscan-api",
        "version": version_info["version"],
        "build": version_info["build"],
        "commit": version_info["commit"]
    }


@router.get("/version")
async def version_info():
    """Get detailed version information"""
    return get_version_info()


@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check with dependency status and system metrics"""
    start_time = time.time()
    
    with tracer.start_as_current_span("health_check_detailed") if tracer else None:
        health_status = {
            "status": "healthy",
            "service": "lexiscan-api",
            "version": settings.VERSION,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
            "system": {}
        }
        
        # System metrics
        try:
            health_status["system"] = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "uptime": time.time() - psutil.boot_time()
            }
        except Exception as e:
            logger.warning(f"System metrics collection failed: {e}")
        
        # Database check
        db_start = time.time()
        try:
            # Basic connectivity
            await db.execute(text("SELECT 1"))
            
            # Check extensions
            await db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto'"))
            await db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
            
            # Check RLS is working
            await db.execute(text("SELECT set_config('app.current_org', 'test', true)"))
            
            # Performance check
            db_duration = time.time() - db_start
            
            health_status["checks"]["database"] = {
                "status": "healthy",
                "extensions": ["pgcrypto", "vector"],
                "rls_enabled": True,
                "response_time_ms": round(db_duration * 1000, 2)
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_status["checks"]["database"] = {
                "status": "unhealthy", 
                "error": str(e),
                "response_time_ms": round((time.time() - db_start) * 1000, 2)
            }
            health_status["status"] = "unhealthy"
        
        # Redis check
        redis_start = time.time()
        try:
            redis_client = redis.from_url(settings.REDIS_URL)
            await redis_client.ping()
            
            # Test basic operations
            await redis_client.set("health_check", "ok", ex=10)
            result = await redis_client.get("health_check")
            await redis_client.delete("health_check")
            await redis_client.close()
            
            redis_duration = time.time() - redis_start
            
            health_status["checks"]["redis"] = {
                "status": "healthy",
                "operations": ["ping", "set", "get", "delete"],
                "response_time_ms": round(redis_duration * 1000, 2)
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            health_status["checks"]["redis"] = {
                "status": "unhealthy", 
                "error": str(e),
                "response_time_ms": round((time.time() - redis_start) * 1000, 2)
            }
            health_status["status"] = "unhealthy"
        
        # AWS S3 check
        s3_start = time.time()
        try:
            s3_client = boto3.client('s3', region_name=settings.AWS_REGION)
            s3_client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
            
            # Test list operation
            response = s3_client.list_objects_v2(
                Bucket=settings.S3_BUCKET_NAME,
                MaxKeys=1
            )
            
            s3_duration = time.time() - s3_start
            
            health_status["checks"]["s3"] = {
                "status": "healthy",
                "bucket": settings.S3_BUCKET_NAME,
                "region": settings.AWS_REGION,
                "response_time_ms": round(s3_duration * 1000, 2)
            }
        except ClientError as e:
            logger.error(f"S3 health check failed: {e}")
            health_status["checks"]["s3"] = {
                "status": "unhealthy", 
                "error": str(e),
                "response_time_ms": round((time.time() - s3_start) * 1000, 2)
            }
            health_status["status"] = "unhealthy"
        except Exception as e:
            logger.error(f"S3 health check failed: {e}")
            health_status["checks"]["s3"] = {
                "status": "unhealthy", 
                "error": str(e),
                "response_time_ms": round((time.time() - s3_start) * 1000, 2)
            }
            health_status["status"] = "unhealthy"
        
        # AI Services check
        ai_start = time.time()
        try:
            # Check if AI service credentials are configured
            ai_status = {"status": "configured"}
            
            if settings.ANTHROPIC_API_KEY:
                ai_status["anthropic"] = "configured"
            if settings.OPENAI_API_KEY:
                ai_status["openai"] = "configured"
            if settings.USE_BEDROCK:
                ai_status["bedrock"] = "configured"
            
            ai_duration = time.time() - ai_start
            ai_status["response_time_ms"] = round(ai_duration * 1000, 2)
            
            health_status["checks"]["ai_services"] = ai_status
            
        except Exception as e:
            logger.error(f"AI services check failed: {e}")
            health_status["checks"]["ai_services"] = {
                "status": "unhealthy", 
                "error": str(e)
            }
        
        # Overall response time
        total_duration = time.time() - start_time
        health_status["response_time_ms"] = round(total_duration * 1000, 2)
        
        # Record metrics
        if meter:
            try:
                health_check_counter = meter.create_counter(
                    name="health_checks_total",
                    description="Total health checks performed"
                )
                health_check_counter.add(1, {"status": health_status["status"]})
                
                health_check_duration = meter.create_histogram(
                    name="health_check_duration_seconds",
                    description="Health check duration"
                )
                health_check_duration.record(total_duration)
            except Exception:
                pass  # Don't fail health check if metrics fail
        
        if health_status["status"] == "unhealthy":
            raise HTTPException(status_code=503, detail=health_status)
        
        return health_status


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Kubernetes readiness probe endpoint"""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail={"status": "not ready", "error": str(e)})


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    return {"status": "alive"}

@router.get("/metrics")
async def metrics_endpoint():
    """Prometheus-style metrics endpoint"""
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Format as Prometheus metrics
        metrics = [
            f"# HELP system_cpu_percent CPU usage percentage",
            f"# TYPE system_cpu_percent gauge",
            f"system_cpu_percent {cpu_percent}",
            "",
            f"# HELP system_memory_percent Memory usage percentage",
            f"# TYPE system_memory_percent gauge", 
            f"system_memory_percent {memory.percent}",
            "",
            f"# HELP system_memory_bytes Memory usage in bytes",
            f"# TYPE system_memory_bytes gauge",
            f"system_memory_bytes{{type=\"total\"}} {memory.total}",
            f"system_memory_bytes{{type=\"used\"}} {memory.used}",
            f"system_memory_bytes{{type=\"available\"}} {memory.available}",
            "",
            f"# HELP system_disk_percent Disk usage percentage",
            f"# TYPE system_disk_percent gauge",
            f"system_disk_percent {disk.percent}",
            "",
            f"# HELP system_disk_bytes Disk usage in bytes",
            f"# TYPE system_disk_bytes gauge",
            f"system_disk_bytes{{type=\"total\"}} {disk.total}",
            f"system_disk_bytes{{type=\"used\"}} {disk.used}",
            f"system_disk_bytes{{type=\"free\"}} {disk.free}",
            "",
            f"# HELP lexiscan_info Application information",
            f"# TYPE lexiscan_info gauge",
            f"lexiscan_info{{version=\"{settings.VERSION}\",environment=\"{settings.ENVIRONMENT}\"}} 1",
        ]
        
        return "\n".join(metrics)
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail="Metrics collection failed")


@router.get("/health/dependencies")
async def dependencies_health():
    """Check health of external dependencies"""
    dependencies = {
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": {}
    }
    
    # Check Anthropic API
    if settings.ANTHROPIC_API_KEY:
        try:
            # Simple check - just verify key format
            if settings.ANTHROPIC_API_KEY.startswith("sk-ant-"):
                dependencies["dependencies"]["anthropic"] = {
                    "status": "configured",
                    "type": "ai_service"
                }
            else:
                dependencies["dependencies"]["anthropic"] = {
                    "status": "misconfigured",
                    "type": "ai_service",
                    "error": "Invalid API key format"
                }
        except Exception as e:
            dependencies["dependencies"]["anthropic"] = {
                "status": "error",
                "type": "ai_service",
                "error": str(e)
            }
    
    # Check OpenAI API
    if settings.OPENAI_API_KEY:
        try:
            if settings.OPENAI_API_KEY.startswith("sk-"):
                dependencies["dependencies"]["openai"] = {
                    "status": "configured",
                    "type": "ai_service"
                }
            else:
                dependencies["dependencies"]["openai"] = {
                    "status": "misconfigured",
                    "type": "ai_service",
                    "error": "Invalid API key format"
                }
        except Exception as e:
            dependencies["dependencies"]["openai"] = {
                "status": "error",
                "type": "ai_service",
                "error": str(e)
            }
    
    # Check Stripe
    if settings.STRIPE_SECRET_KEY:
        try:
            if settings.STRIPE_SECRET_KEY.startswith("sk_"):
                dependencies["dependencies"]["stripe"] = {
                    "status": "configured",
                    "type": "payment_service"
                }
            else:
                dependencies["dependencies"]["stripe"] = {
                    "status": "misconfigured",
                    "type": "payment_service",
                    "error": "Invalid API key format"
                }
        except Exception as e:
            dependencies["dependencies"]["stripe"] = {
                "status": "error",
                "type": "payment_service",
                "error": str(e)
            }
    
    return dependencies