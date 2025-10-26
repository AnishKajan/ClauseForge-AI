"""
Application configuration management
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "LexiScan AI Contract Analyzer"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API
    API_V1_STR: str = "/api"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BASE_URL: str = "http://localhost:8000"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://lexiscan:password@localhost:5432/lexiscan"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    
    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_STORAGE_ACCOUNT_NAME: Optional[str] = None
    AZURE_STORAGE_ACCOUNT_KEY: Optional[str] = None
    AZURE_STORAGE_CONTAINER_NAME: str = "contracts"
    
    # Azure Document Intelligence
    AZURE_DOC_INTEL_ENDPOINT: Optional[str] = None
    AZURE_DOC_INTEL_KEY: Optional[str] = None
    
    # Azure Service Bus (optional)
    AZURE_SERVICE_BUS_CONNECTION_STRING: Optional[str] = None
    AZURE_SERVICE_BUS_QUEUE_NAME: Optional[str] = None
    
    # AWS (legacy - for migration period)
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: str = "lexiscan-documents"
    SQS_QUEUE_URL: Optional[str] = None
    
    # AI Services
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    EMBEDDING_PROVIDER: str = "openai"  # "openai" or "bedrock"
    LLM_PROVIDER: str = "anthropic"  # "anthropic" or "bedrock"
    USE_BEDROCK: bool = False
    
    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRO_PRICE_ID: Optional[str] = None
    STRIPE_ENTERPRISE_PRICE_ID: Optional[str] = None
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://localhost:3000",
    ]
    
    # File upload limits
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: List[str] = [".pdf", ".docx", ".doc"]
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Security
    VIRUS_SCANNER_LAMBDA_FUNCTION: Optional[str] = None
    ENABLE_VIRUS_SCANNING: bool = True
    SECURITY_HEADERS_ENABLED: bool = True
    
    # Audit logging
    AUDIT_LOG_RETENTION_DAYS: int = 365
    ENABLE_AUDIT_LOGGING: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()