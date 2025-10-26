"""
Structured logging configuration for JSON output and CloudWatch integration
"""

import json
import logging
import logging.config
import sys
from datetime import datetime
from typing import Any, Dict, Optional
import structlog
from pythonjsonlogger import jsonlogger

from core.config import settings


class CustomJSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add service information
        log_record['service'] = 'lexiscan-backend'
        log_record['version'] = settings.VERSION
        log_record['environment'] = settings.ENVIRONMENT
        
        # Add level name
        log_record['level'] = record.levelname
        
        # Add logger name
        log_record['logger'] = record.name
        
        # Add thread and process info for debugging
        if settings.DEBUG:
            log_record['thread'] = record.thread
            log_record['process'] = record.process


class StructuredLogger:
    """Structured logger wrapper for consistent logging"""
    
    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
        self.name = name
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with structured data"""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with structured data"""
        self.logger.critical(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data"""
        self.logger.debug(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with structured data"""
        self.logger.exception(message, **kwargs)


def setup_logging():
    """Setup structured logging configuration"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Logging configuration
    log_level = "DEBUG" if settings.DEBUG else "INFO"
    
    # JSON formatter for structured logs
    json_formatter = CustomJSONFormatter(
        format='%(timestamp)s %(level)s %(name)s %(message)s'
    )
    
    # Console formatter for development
    console_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure handlers
    handlers = {}
    
    if settings.ENVIRONMENT == "production":
        # JSON handler for production (CloudWatch)
        handlers['json'] = {
            'class': 'logging.StreamHandler',
            'level': log_level,
            'formatter': 'json',
            'stream': sys.stdout
        }
    else:
        # Console handler for development
        handlers['console'] = {
            'class': 'logging.StreamHandler',
            'level': log_level,
            'formatter': 'console',
            'stream': sys.stdout
        }
    
    # Logging configuration dictionary
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': CustomJSONFormatter,
                'format': '%(timestamp)s %(level)s %(name)s %(message)s'
            },
            'console': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': handlers,
        'loggers': {
            # Application loggers
            'lexiscan': {
                'level': log_level,
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            'core': {
                'level': log_level,
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            'services': {
                'level': log_level,
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            'repositories': {
                'level': log_level,
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            'routers': {
                'level': log_level,
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            # Third-party loggers
            'uvicorn': {
                'level': 'INFO',
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            'uvicorn.access': {
                'level': 'INFO',
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            'sqlalchemy': {
                'level': 'WARNING',
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            'boto3': {
                'level': 'WARNING',
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            'botocore': {
                'level': 'WARNING',
                'handlers': list(handlers.keys()),
                'propagate': False
            }
        },
        'root': {
            'level': log_level,
            'handlers': list(handlers.keys())
        }
    }
    
    # Apply logging configuration
    logging.config.dictConfig(logging_config)
    
    # Set up request ID context
    structlog.contextvars.clear_contextvars()


def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)


def log_request_context(request_id: str, user_id: Optional[str] = None, org_id: Optional[str] = None):
    """Set request context for structured logging"""
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        user_id=user_id,
        org_id=org_id
    )


def clear_request_context():
    """Clear request context"""
    structlog.contextvars.clear_contextvars()


# Business event logging functions
def log_business_event(
    event_type: str,
    user_id: Optional[str] = None,
    org_id: Optional[str] = None,
    **kwargs
):
    """Log business events for analytics"""
    logger = get_structured_logger("business_events")
    
    event_data = {
        "event_type": event_type,
        "user_id": user_id,
        "org_id": org_id,
        "timestamp": datetime.utcnow().isoformat(),
        **kwargs
    }
    
    logger.info(f"Business event: {event_type}", **event_data)


def log_performance_metric(
    metric_name: str,
    value: float,
    unit: str = "seconds",
    **kwargs
):
    """Log performance metrics"""
    logger = get_structured_logger("performance")
    
    metric_data = {
        "metric_name": metric_name,
        "value": value,
        "unit": unit,
        "timestamp": datetime.utcnow().isoformat(),
        **kwargs
    }
    
    logger.info(f"Performance metric: {metric_name}", **metric_data)


def log_security_event(
    event_type: str,
    severity: str = "warning",
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    **kwargs
):
    """Log security events"""
    logger = get_structured_logger("security")
    
    event_data = {
        "event_type": event_type,
        "severity": severity,
        "user_id": user_id,
        "ip_address": ip_address,
        "timestamp": datetime.utcnow().isoformat(),
        **kwargs
    }
    
    if severity == "critical":
        logger.critical(f"Security event: {event_type}", **event_data)
    elif severity == "error":
        logger.error(f"Security event: {event_type}", **event_data)
    else:
        logger.warning(f"Security event: {event_type}", **event_data)