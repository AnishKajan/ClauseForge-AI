"""
FastAPI dependency injection for database and repositories
"""

from typing import Optional, AsyncGenerator
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db, set_org_context
from repositories import (
    OrganizationRepository,
    UserRepository,
    DocumentRepository,
    DocumentChunkRepository,
    ClauseRepository,
    AnalysisRepository,
    PlaybookRepository,
    UsageRecordRepository,
    AuditLogRepository,
)


async def get_org_id(request: Request) -> Optional[str]:
    """Get organization ID from request state"""
    return getattr(request.state, "org_id", None)


async def get_org_id_required(request: Request) -> str:
    """Get organization ID from request state (required)"""
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=400,
            detail="Organization ID is required. Please provide X-Org-ID header or valid JWT token."
        )
    return org_id


async def get_db_with_org_context(
    request: Request,
    session: AsyncSession = Depends(get_db)
) -> AsyncSession:
    """Get database session with organization context set"""
    org_id = getattr(request.state, "org_id", None)
    if org_id:
        await set_org_context(session, org_id)
    return session


# Repository dependencies
async def get_organization_repository(
    session: AsyncSession = Depends(get_db)
) -> OrganizationRepository:
    """Get organization repository"""
    return OrganizationRepository(session)


async def get_user_repository(
    session: AsyncSession = Depends(get_db)
) -> UserRepository:
    """Get user repository"""
    return UserRepository(session)


async def get_document_repository(
    session: AsyncSession = Depends(get_db)
) -> DocumentRepository:
    """Get document repository"""
    return DocumentRepository(session)


async def get_document_chunk_repository(
    session: AsyncSession = Depends(get_db)
) -> DocumentChunkRepository:
    """Get document chunk repository"""
    return DocumentChunkRepository(session)


async def get_clause_repository(
    session: AsyncSession = Depends(get_db)
) -> ClauseRepository:
    """Get clause repository"""
    return ClauseRepository(session)


async def get_analysis_repository(
    session: AsyncSession = Depends(get_db)
) -> AnalysisRepository:
    """Get analysis repository"""
    return AnalysisRepository(session)


async def get_playbook_repository(
    session: AsyncSession = Depends(get_db)
) -> PlaybookRepository:
    """Get playbook repository"""
    return PlaybookRepository(session)


async def get_usage_record_repository(
    session: AsyncSession = Depends(get_db)
) -> UsageRecordRepository:
    """Get usage record repository"""
    return UsageRecordRepository(session)


async def get_audit_log_repository(
    session: AsyncSession = Depends(get_db)
) -> AuditLogRepository:
    """Get audit log repository"""
    return AuditLogRepository(session)


# Combined dependencies for common use cases
class RepositoryDeps:
    """Container for all repository dependencies"""
    
    def __init__(
        self,
        org_repo: OrganizationRepository = Depends(get_organization_repository),
        user_repo: UserRepository = Depends(get_user_repository),
        doc_repo: DocumentRepository = Depends(get_document_repository),
        chunk_repo: DocumentChunkRepository = Depends(get_document_chunk_repository),
        clause_repo: ClauseRepository = Depends(get_clause_repository),
        analysis_repo: AnalysisRepository = Depends(get_analysis_repository),
        playbook_repo: PlaybookRepository = Depends(get_playbook_repository),
        usage_repo: UsageRecordRepository = Depends(get_usage_record_repository),
        audit_repo: AuditLogRepository = Depends(get_audit_log_repository),
    ):
        self.org = org_repo
        self.user = user_repo
        self.document = doc_repo
        self.chunk = chunk_repo
        self.clause = clause_repo
        self.analysis = analysis_repo
        self.playbook = playbook_repo
        self.usage = usage_repo
        self.audit = audit_repo


async def get_repositories() -> RepositoryDeps:
    """Get all repositories as a single dependency"""
    return RepositoryDeps()