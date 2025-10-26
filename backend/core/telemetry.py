"""
OpenTelemetry configuration for distributed tracing and metrics
"""

import logging
import os
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.boto3sqs import Boto3SQSInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

from core.config import settings

logger = logging.getLogger(__name__)


class TelemetryService:
    """Service for managing OpenTelemetry tracing and metrics"""
    
    def __init__(self):
        self.tracer_provider: Optional[TracerProvider] = None
        self.meter_provider: Optional[MeterProvider] = None
        self.tracer = None
        self.meter = None
        
    def initialize_telemetry(self, app_name: str = "lexiscan-backend"):
        """Initialize OpenTelemetry tracing and metrics"""
        try:
            # Create resource
            resource = Resource.create({
                ResourceAttributes.SERVICE_NAME: app_name,
                ResourceAttributes.SERVICE_VERSION: settings.VERSION,
                ResourceAttributes.DEPLOYMENT_ENVIRONMENT: settings.ENVIRONMENT,
            })
            
            # Initialize tracing
            self._setup_tracing(resource)
            
            # Initialize metrics
            self._setup_metrics(resource)
            
            # Instrument libraries
            self._instrument_libraries()
            
            logger.info("OpenTelemetry initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {str(e)}")
    
    def _setup_tracing(self, resource: Resource):
        """Setup distributed tracing"""
        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(self.tracer_provider)
        
        # Configure exporters based on environment
        if settings.ENVIRONMENT == "production":
            # Use OTLP exporter for production (CloudWatch, Jaeger, etc.)
            otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
            if otlp_endpoint:
                otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                self.tracer_provider.add_span_processor(
                    BatchSpanProcessor(otlp_exporter)
                )
            
            # Jaeger exporter as fallback
            jaeger_endpoint = os.getenv("JAEGER_ENDPOINT")
            if jaeger_endpoint:
                jaeger_exporter = JaegerExporter(
                    agent_host_name=jaeger_endpoint,
                    agent_port=14268,
                )
                self.tracer_provider.add_span_processor(
                    BatchSpanProcessor(jaeger_exporter)
                )
        else:
            # Use console exporter for development
            console_exporter = ConsoleSpanExporter()
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(console_exporter)
            )
        
        # Get tracer
        self.tracer = trace.get_tracer(__name__)
    
    def _setup_metrics(self, resource: Resource):
        """Setup metrics collection"""
        # Configure metric exporter
        if settings.ENVIRONMENT == "production":
            otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
            if otlp_endpoint:
                metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint)
                metric_reader = PeriodicExportingMetricReader(
                    exporter=metric_exporter,
                    export_interval_millis=30000  # 30 seconds
                )
                
                self.meter_provider = MeterProvider(
                    resource=resource,
                    metric_readers=[metric_reader]
                )
                metrics.set_meter_provider(self.meter_provider)
        
        # Get meter
        self.meter = metrics.get_meter(__name__)
    
    def _instrument_libraries(self):
        """Instrument common libraries for automatic tracing"""
        try:
            # FastAPI instrumentation
            FastAPIInstrumentor.instrument()
            
            # Database instrumentation
            SQLAlchemyInstrumentor().instrument()
            
            # Redis instrumentation
            RedisInstrumentor().instrument()
            
            # AWS SQS instrumentation
            Boto3SQSInstrumentor().instrument()
            
            # HTTP client instrumentation
            RequestsInstrumentor().instrument()
            HTTPXClientInstrumentor().instrument()
            
            logger.info("Library instrumentation completed")
            
        except Exception as e:
            logger.warning(f"Some instrumentations failed: {str(e)}")
    
    def get_tracer(self):
        """Get the configured tracer"""
        return self.tracer
    
    def get_meter(self):
        """Get the configured meter"""
        return self.meter
    
    def create_custom_metrics(self):
        """Create custom business metrics"""
        if not self.meter:
            return {}
        
        try:
            # Business metrics
            document_upload_counter = self.meter.create_counter(
                name="documents_uploaded_total",
                description="Total number of documents uploaded",
                unit="1"
            )
            
            document_processing_duration = self.meter.create_histogram(
                name="document_processing_duration_seconds",
                description="Time taken to process documents",
                unit="s"
            )
            
            rag_query_counter = self.meter.create_counter(
                name="rag_queries_total",
                description="Total number of RAG queries",
                unit="1"
            )
            
            rag_query_duration = self.meter.create_histogram(
                name="rag_query_duration_seconds",
                description="Time taken to process RAG queries",
                unit="s"
            )
            
            analysis_counter = self.meter.create_counter(
                name="analyses_completed_total",
                description="Total number of analyses completed",
                unit="1"
            )
            
            user_active_gauge = self.meter.create_up_down_counter(
                name="active_users",
                description="Number of active users",
                unit="1"
            )
            
            # System metrics
            api_request_counter = self.meter.create_counter(
                name="api_requests_total",
                description="Total number of API requests",
                unit="1"
            )
            
            api_request_duration = self.meter.create_histogram(
                name="api_request_duration_seconds",
                description="API request duration",
                unit="s"
            )
            
            error_counter = self.meter.create_counter(
                name="errors_total",
                description="Total number of errors",
                unit="1"
            )
            
            return {
                "document_upload_counter": document_upload_counter,
                "document_processing_duration": document_processing_duration,
                "rag_query_counter": rag_query_counter,
                "rag_query_duration": rag_query_duration,
                "analysis_counter": analysis_counter,
                "user_active_gauge": user_active_gauge,
                "api_request_counter": api_request_counter,
                "api_request_duration": api_request_duration,
                "error_counter": error_counter,
            }
            
        except Exception as e:
            logger.error(f"Failed to create custom metrics: {str(e)}")
            return {}


# Global telemetry service instance
telemetry_service = TelemetryService()


def get_tracer():
    """Get the global tracer instance"""
    return telemetry_service.get_tracer()


def get_meter():
    """Get the global meter instance"""
    return telemetry_service.get_meter()


# Decorator for tracing functions
def trace_function(name: Optional[str] = None):
    """Decorator to trace function execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if not tracer:
                return func(*args, **kwargs)
            
            span_name = name or f"{func.__module__}.{func.__name__}"
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add function attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    
                    result = func(*args, **kwargs)
                    span.set_attribute("function.result", "success")
                    return result
                    
                except Exception as e:
                    span.set_attribute("function.result", "error")
                    span.set_attribute("function.error", str(e))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


# Async version of the decorator
def trace_async_function(name: Optional[str] = None):
    """Decorator to trace async function execution"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if not tracer:
                return await func(*args, **kwargs)
            
            span_name = name or f"{func.__module__}.{func.__name__}"
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add function attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    
                    result = await func(*args, **kwargs)
                    span.set_attribute("function.result", "success")
                    return result
                    
                except Exception as e:
                    span.set_attribute("function.result", "error")
                    span.set_attribute("function.error", str(e))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator