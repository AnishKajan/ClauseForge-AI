"""
Celery application configuration for document processing.
"""

import os
from celery import Celery
from kombu import Queue

from core.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "lexiscan_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["worker.tasks"]
)

# Configure Celery
celery_app.conf.update(
    # Task routing
    task_routes={
        "worker.tasks.process_document": {"queue": "document_processing"},
        "worker.tasks.cleanup_failed_processing": {"queue": "maintenance"},
    },
    
    # Queue configuration
    task_default_queue="default",
    task_queues=(
        Queue("default", routing_key="default"),
        Queue("document_processing", routing_key="document_processing"),
        Queue("maintenance", routing_key="maintenance"),
    ),
    
    # Task execution
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task timeouts
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    
    # Retry configuration
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    
    # Worker settings
    worker_max_tasks_per_child=100,
    worker_disable_rate_limits=False,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# SQS configuration for production
if settings.SQS_QUEUE_URL:
    # Use SQS as broker in production
    celery_app.conf.update(
        broker_url=f"sqs://{settings.AWS_ACCESS_KEY_ID}:{settings.AWS_SECRET_ACCESS_KEY}@",
        broker_transport_options={
            "region": settings.AWS_REGION,
            "queue_name_prefix": "lexiscan-",
            "visibility_timeout": 300,
            "polling_interval": 1,
        },
    )

if __name__ == "__main__":
    celery_app.start()