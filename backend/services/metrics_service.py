"""
Business metrics and KPI tracking service
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from core.telemetry import get_meter, get_tracer
from core.logging_config import log_business_event, log_performance_metric
from models.database import Document, Analysis, User, Organization, UsageRecord
from repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for tracking business metrics and KPIs"""
    
    def __init__(self):
        self.meter = get_meter()
        self.tracer = get_tracer()
        self.repo = BaseRepository()
        
        # Initialize custom metrics
        self.metrics = self._initialize_metrics()
    
    def _initialize_metrics(self) -> Dict[str, Any]:
        """Initialize custom business metrics"""
        if not self.meter:
            return {}
        
        try:
            return {
                # Document metrics
                "documents_uploaded": self.meter.create_counter(
                    name="documents_uploaded_total",
                    description="Total documents uploaded",
                    unit="1"
                ),
                "documents_processed": self.meter.create_counter(
                    name="documents_processed_total", 
                    description="Total documents processed",
                    unit="1"
                ),
                "document_processing_time": self.meter.create_histogram(
                    name="document_processing_duration_seconds",
                    description="Document processing duration",
                    unit="s"
                ),
                
                # Analysis metrics
                "analyses_completed": self.meter.create_counter(
                    name="analyses_completed_total",
                    description="Total analyses completed",
                    unit="1"
                ),
                "analysis_processing_time": self.meter.create_histogram(
                    name="analysis_duration_seconds",
                    description="Analysis processing duration", 
                    unit="s"
                ),
                
                # RAG query metrics
                "rag_queries": self.meter.create_counter(
                    name="rag_queries_total",
                    description="Total RAG queries",
                    unit="1"
                ),
                "rag_query_time": self.meter.create_histogram(
                    name="rag_query_duration_seconds",
                    description="RAG query processing duration",
                    unit="s"
                ),
                
                # User metrics
                "user_registrations": self.meter.create_counter(
                    name="user_registrations_total",
                    description="Total user registrations",
                    unit="1"
                ),
                "active_users": self.meter.create_up_down_counter(
                    name="active_users_current",
                    description="Currently active users",
                    unit="1"
                ),
                
                # Business metrics
                "subscription_changes": self.meter.create_counter(
                    name="subscription_changes_total",
                    description="Total subscription changes",
                    unit="1"
                ),
                "revenue_events": self.meter.create_counter(
                    name="revenue_events_total",
                    description="Revenue generating events",
                    unit="1"
                ),
                
                # Error metrics
                "errors": self.meter.create_counter(
                    name="application_errors_total",
                    description="Total application errors",
                    unit="1"
                ),
                
                # API metrics
                "api_requests": self.meter.create_counter(
                    name="api_requests_total",
                    description="Total API requests",
                    unit="1"
                ),
                "api_response_time": self.meter.create_histogram(
                    name="api_response_duration_seconds",
                    description="API response duration",
                    unit="s"
                )
            }
        except Exception as e:
            logger.error(f"Failed to initialize metrics: {str(e)}")
            return {}
    
    def track_document_upload(
        self,
        user_id: str,
        org_id: str,
        file_size: int,
        file_type: str,
        processing_time: Optional[float] = None
    ):
        """Track document upload metrics"""
        try:
            # Increment counter
            if "documents_uploaded" in self.metrics:
                self.metrics["documents_uploaded"].add(1, {
                    "org_id": org_id,
                    "file_type": file_type
                })
            
            # Log business event
            log_business_event(
                event_type="document_upload",
                user_id=user_id,
                org_id=org_id,
                file_size=file_size,
                file_type=file_type
            )
            
            # Track processing time if provided
            if processing_time and "document_processing_time" in self.metrics:
                self.metrics["document_processing_time"].record(processing_time, {
                    "org_id": org_id,
                    "file_type": file_type
                })
                
                log_performance_metric(
                    metric_name="document_upload_processing_time",
                    value=processing_time,
                    user_id=user_id,
                    org_id=org_id
                )
                
        except Exception as e:
            logger.error(f"Failed to track document upload metrics: {str(e)}")
    
    def track_document_processing(
        self,
        document_id: str,
        user_id: str,
        org_id: str,
        processing_time: float,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Track document processing metrics"""
        try:
            if success and "documents_processed" in self.metrics:
                self.metrics["documents_processed"].add(1, {
                    "org_id": org_id,
                    "status": "success"
                })
            elif not success and "errors" in self.metrics:
                self.metrics["errors"].add(1, {
                    "org_id": org_id,
                    "type": "document_processing",
                    "error": error or "unknown"
                })
            
            # Track processing time
            if "document_processing_time" in self.metrics:
                self.metrics["document_processing_time"].record(processing_time, {
                    "org_id": org_id,
                    "status": "success" if success else "error"
                })
            
            # Log business event
            log_business_event(
                event_type="document_processing_complete",
                user_id=user_id,
                org_id=org_id,
                document_id=document_id,
                processing_time=processing_time,
                success=success,
                error=error
            )
            
        except Exception as e:
            logger.error(f"Failed to track document processing metrics: {str(e)}")
    
    def track_analysis_completion(
        self,
        analysis_id: str,
        user_id: str,
        org_id: str,
        processing_time: float,
        risk_score: Optional[int] = None
    ):
        """Track analysis completion metrics"""
        try:
            if "analyses_completed" in self.metrics:
                self.metrics["analyses_completed"].add(1, {
                    "org_id": org_id
                })
            
            if "analysis_processing_time" in self.metrics:
                self.metrics["analysis_processing_time"].record(processing_time, {
                    "org_id": org_id
                })
            
            # Log business event
            log_business_event(
                event_type="analysis_complete",
                user_id=user_id,
                org_id=org_id,
                analysis_id=analysis_id,
                processing_time=processing_time,
                risk_score=risk_score
            )
            
        except Exception as e:
            logger.error(f"Failed to track analysis metrics: {str(e)}")
    
    def track_rag_query(
        self,
        user_id: str,
        org_id: str,
        query_time: float,
        model_used: str,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Track RAG query metrics"""
        try:
            if "rag_queries" in self.metrics:
                self.metrics["rag_queries"].add(1, {
                    "org_id": org_id,
                    "model": model_used,
                    "status": "success" if success else "error"
                })
            
            if "rag_query_time" in self.metrics:
                self.metrics["rag_query_time"].record(query_time, {
                    "org_id": org_id,
                    "model": model_used,
                    "status": "success" if success else "error"
                })
            
            # Log business event
            log_business_event(
                event_type="rag_query",
                user_id=user_id,
                org_id=org_id,
                query_time=query_time,
                model_used=model_used,
                success=success,
                error=error
            )
            
        except Exception as e:
            logger.error(f"Failed to track RAG query metrics: {str(e)}")
    
    def track_user_registration(self, user_id: str, org_id: str, provider: str):
        """Track user registration metrics"""
        try:
            if "user_registrations" in self.metrics:
                self.metrics["user_registrations"].add(1, {
                    "org_id": org_id,
                    "provider": provider
                })
            
            log_business_event(
                event_type="user_registration",
                user_id=user_id,
                org_id=org_id,
                provider=provider
            )
            
        except Exception as e:
            logger.error(f"Failed to track user registration metrics: {str(e)}")
    
    def track_subscription_change(
        self,
        org_id: str,
        old_plan: Optional[str],
        new_plan: str,
        user_id: Optional[str] = None
    ):
        """Track subscription change metrics"""
        try:
            if "subscription_changes" in self.metrics:
                self.metrics["subscription_changes"].add(1, {
                    "org_id": org_id,
                    "old_plan": old_plan or "none",
                    "new_plan": new_plan
                })
            
            log_business_event(
                event_type="subscription_change",
                user_id=user_id,
                org_id=org_id,
                old_plan=old_plan,
                new_plan=new_plan
            )
            
        except Exception as e:
            logger.error(f"Failed to track subscription change metrics: {str(e)}")
    
    def track_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time: float,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None
    ):
        """Track API request metrics"""
        try:
            if "api_requests" in self.metrics:
                self.metrics["api_requests"].add(1, {
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": str(status_code),
                    "org_id": org_id or "anonymous"
                })
            
            if "api_response_time" in self.metrics:
                self.metrics["api_response_time"].record(response_time, {
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": str(status_code)
                })
            
        except Exception as e:
            logger.error(f"Failed to track API request metrics: {str(e)}")
    
    def track_error(
        self,
        error_type: str,
        error_message: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        endpoint: Optional[str] = None
    ):
        """Track application errors"""
        try:
            if "errors" in self.metrics:
                self.metrics["errors"].add(1, {
                    "type": error_type,
                    "org_id": org_id or "unknown",
                    "endpoint": endpoint or "unknown"
                })
            
            log_business_event(
                event_type="application_error",
                user_id=user_id,
                org_id=org_id,
                error_type=error_type,
                error_message=error_message,
                endpoint=endpoint
            )
            
        except Exception as e:
            logger.error(f"Failed to track error metrics: {str(e)}")
    
    async def get_business_kpis(self, db: Session, org_id: Optional[str] = None) -> Dict[str, Any]:
        """Get business KPIs for dashboard"""
        try:
            with self.tracer.start_as_current_span("get_business_kpis") if self.tracer else None:
                kpis = {}
                
                # Time ranges
                now = datetime.utcnow()
                last_30_days = now - timedelta(days=30)
                last_7_days = now - timedelta(days=7)
                
                # Document metrics
                doc_query = db.query(Document)
                if org_id:
                    doc_query = doc_query.filter(Document.org_id == org_id)
                
                kpis["documents"] = {
                    "total": doc_query.count(),
                    "last_30_days": doc_query.filter(Document.created_at >= last_30_days).count(),
                    "last_7_days": doc_query.filter(Document.created_at >= last_7_days).count()
                }
                
                # Analysis metrics
                analysis_query = db.query(Analysis)
                if org_id:
                    analysis_query = analysis_query.join(Document).filter(Document.org_id == org_id)
                
                kpis["analyses"] = {
                    "total": analysis_query.count(),
                    "last_30_days": analysis_query.filter(Analysis.created_at >= last_30_days).count(),
                    "last_7_days": analysis_query.filter(Analysis.created_at >= last_7_days).count()
                }
                
                # User metrics
                if not org_id:  # Global metrics only
                    user_query = db.query(User)
                    kpis["users"] = {
                        "total": user_query.count(),
                        "last_30_days": user_query.filter(User.created_at >= last_30_days).count(),
                        "last_7_days": user_query.filter(User.created_at >= last_7_days).count(),
                        "active_last_7_days": user_query.filter(User.last_login >= last_7_days).count()
                    }
                    
                    # Organization metrics
                    org_query = db.query(Organization)
                    kpis["organizations"] = {
                        "total": org_query.count(),
                        "last_30_days": org_query.filter(Organization.created_at >= last_30_days).count()
                    }
                
                # Usage metrics
                usage_query = db.query(UsageRecord)
                if org_id:
                    usage_query = usage_query.filter(UsageRecord.org_id == org_id)
                
                usage_stats = usage_query.filter(
                    UsageRecord.period_start >= last_30_days
                ).group_by(UsageRecord.usage_type).all()
                
                kpis["usage"] = {}
                for usage_type, total in usage_stats:
                    kpis["usage"][usage_type] = total
                
                return kpis
                
        except Exception as e:
            logger.error(f"Failed to get business KPIs: {str(e)}")
            return {}


# Global metrics service instance
metrics_service = MetricsService()


# Convenience functions
def track_document_upload(user_id: str, org_id: str, file_size: int, file_type: str, processing_time: Optional[float] = None):
    """Track document upload"""
    metrics_service.track_document_upload(user_id, org_id, file_size, file_type, processing_time)


def track_rag_query(user_id: str, org_id: str, query_time: float, model_used: str, success: bool = True, error: Optional[str] = None):
    """Track RAG query"""
    metrics_service.track_rag_query(user_id, org_id, query_time, model_used, success, error)


def track_api_request(endpoint: str, method: str, status_code: int, response_time: float, user_id: Optional[str] = None, org_id: Optional[str] = None):
    """Track API request"""
    metrics_service.track_api_request(endpoint, method, status_code, response_time, user_id, org_id)