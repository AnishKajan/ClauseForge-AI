"""
Document comparison endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import logging

from core.database import get_db
from core.rbac import (
    require_document_read,
    require_org_access,
    protected_route,
    Permission
)
from models.database import User
from services.document_comparison import DocumentComparisonService, ChangeType

logger = logging.getLogger(__name__)
router = APIRouter()


class CompareRequest(BaseModel):
    document_a_id: str
    document_b_id: str


class TextChangeResponse(BaseModel):
    change_type: str
    text: str
    line_number: Optional[int] = None
    page_number: Optional[int] = None
    confidence: float = 1.0


class ClauseChangeResponse(BaseModel):
    change_type: str
    clause_type: str
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    risk_impact: str = "low"
    page_number: Optional[int] = None


class ComparisonResponse(BaseModel):
    comparison_id: str
    document_a_id: str
    document_b_id: str
    document_a_title: str
    document_b_title: str
    text_changes: List[TextChangeResponse]
    clause_changes: List[ClauseChangeResponse]
    similarity_score: float
    risk_assessment: Dict[str, Any]
    summary: str
    created_at: datetime
    created_by: str


class ComparisonHistoryResponse(BaseModel):
    comparisons: List[ComparisonResponse]
    total: int


class ComparisonSummaryResponse(BaseModel):
    comparison_id: str
    document_a_title: str
    document_b_title: str
    similarity_score: float
    overall_risk: str
    change_count: int
    created_at: datetime


@router.post("/compare", response_model=ComparisonResponse)
@protected_route(permissions=[Permission.DOCUMENT_READ])
async def compare_documents(
    request: CompareRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_document_read),
    _: User = Depends(require_org_access)
):
    """Compare two documents and analyze differences"""
    try:
        # Validate document IDs
        try:
            doc_a_id = UUID(request.document_a_id)
            doc_b_id = UUID(request.document_b_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document ID format"
            )
        
        if doc_a_id == doc_b_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot compare a document with itself"
            )
        
        # Initialize comparison service
        comparison_service = DocumentComparisonService(db)
        
        # Perform comparison
        result = await comparison_service.compare_documents(
            document_a_id=doc_a_id,
            document_b_id=doc_b_id,
            org_id=str(current_user.org_id),
            user_id=current_user.id
        )
        
        # Get document titles for response
        from repositories.document import DocumentRepository
        doc_repo = DocumentRepository(db)
        
        doc_a = await doc_repo.get(doc_a_id, str(current_user.org_id))
        doc_b = await doc_repo.get(doc_b_id, str(current_user.org_id))
        
        if not doc_a or not doc_b:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or both documents not found"
            )
        
        # Convert to response format
        text_changes = [
            TextChangeResponse(
                change_type=change.change_type.value,
                text=change.text,
                line_number=change.line_number,
                page_number=change.page_number,
                confidence=change.confidence
            )
            for change in result.text_changes
        ]
        
        clause_changes = [
            ClauseChangeResponse(
                change_type=change.change_type.value,
                clause_type=change.clause_type,
                old_text=change.old_text,
                new_text=change.new_text,
                risk_impact=change.risk_impact,
                page_number=change.page_number
            )
            for change in result.clause_changes
        ]
        
        logger.info(f"Document comparison completed: {doc_a_id} vs {doc_b_id} by user {current_user.id}")
        
        return ComparisonResponse(
            comparison_id=str(doc_a_id),  # Using doc_a_id as comparison ID for now
            document_a_id=str(result.document_a_id),
            document_b_id=str(result.document_b_id),
            document_a_title=doc_a.title,
            document_b_title=doc_b.title,
            text_changes=text_changes,
            clause_changes=clause_changes,
            similarity_score=result.similarity_score,
            risk_assessment=result.risk_assessment,
            summary=result.summary,
            created_at=datetime.utcnow(),
            created_by=str(current_user.id)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare documents: {str(e)}"
        )


@router.get("/history", response_model=ComparisonHistoryResponse)
@protected_route(permissions=[Permission.DOCUMENT_READ])
async def get_comparison_history(
    limit: int = Query(10, ge=1, le=50, description="Number of comparisons to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_document_read),
    _: User = Depends(require_org_access)
):
    """Get comparison history for the organization"""
    try:
        comparison_service = DocumentComparisonService(db)
        
        # Get comparison history
        stored_comparisons = await comparison_service.get_comparison_history(
            org_id=str(current_user.org_id),
            limit=limit
        )
        
        # Convert to response format
        comparisons = []
        for stored_comparison in stored_comparisons:
            # Parse the stored comparison
            result = comparison_service._parse_stored_comparison(stored_comparison)
            
            text_changes = [
                TextChangeResponse(
                    change_type=change.change_type.value,
                    text=change.text,
                    line_number=change.line_number,
                    page_number=change.page_number,
                    confidence=change.confidence
                )
                for change in result.text_changes
            ]
            
            clause_changes = [
                ClauseChangeResponse(
                    change_type=change.change_type.value,
                    clause_type=change.clause_type,
                    old_text=change.old_text,
                    new_text=change.new_text,
                    risk_impact=change.risk_impact,
                    page_number=change.page_number
                )
                for change in result.clause_changes
            ]
            
            comparisons.append(ComparisonResponse(
                comparison_id=str(stored_comparison.id),
                document_a_id=str(stored_comparison.document_a_id),
                document_b_id=str(stored_comparison.document_b_id),
                document_a_title=stored_comparison.document_a.title,
                document_b_title=stored_comparison.document_b.title,
                text_changes=text_changes,
                clause_changes=clause_changes,
                similarity_score=result.similarity_score,
                risk_assessment=result.risk_assessment,
                summary=result.summary,
                created_at=stored_comparison.created_at,
                created_by=str(stored_comparison.created_by)
            ))
        
        return ComparisonHistoryResponse(
            comparisons=comparisons,
            total=len(comparisons)
        )
        
    except Exception as e:
        logger.error(f"Error getting comparison history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get comparison history: {str(e)}"
        )


@router.get("/document/{document_id}", response_model=ComparisonHistoryResponse)
@protected_route(permissions=[Permission.DOCUMENT_READ])
async def get_document_comparisons(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_document_read),
    _: User = Depends(require_org_access)
):
    """Get all comparisons involving a specific document"""
    try:
        # Validate document ID
        try:
            doc_id = UUID(document_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document ID format"
            )
        
        comparison_service = DocumentComparisonService(db)
        
        # Get document comparisons
        stored_comparisons = await comparison_service.get_document_comparisons(
            document_id=doc_id,
            org_id=str(current_user.org_id)
        )
        
        # Convert to response format
        comparisons = []
        for stored_comparison in stored_comparisons:
            # Parse the stored comparison
            result = comparison_service._parse_stored_comparison(stored_comparison)
            
            text_changes = [
                TextChangeResponse(
                    change_type=change.change_type.value,
                    text=change.text,
                    line_number=change.line_number,
                    page_number=change.page_number,
                    confidence=change.confidence
                )
                for change in result.text_changes
            ]
            
            clause_changes = [
                ClauseChangeResponse(
                    change_type=change.change_type.value,
                    clause_type=change.clause_type,
                    old_text=change.old_text,
                    new_text=change.new_text,
                    risk_impact=change.risk_impact,
                    page_number=change.page_number
                )
                for change in result.clause_changes
            ]
            
            comparisons.append(ComparisonResponse(
                comparison_id=str(stored_comparison.id),
                document_a_id=str(stored_comparison.document_a_id),
                document_b_id=str(stored_comparison.document_b_id),
                document_a_title=stored_comparison.document_a.title,
                document_b_title=stored_comparison.document_b.title,
                text_changes=text_changes,
                clause_changes=clause_changes,
                similarity_score=result.similarity_score,
                risk_assessment=result.risk_assessment,
                summary=result.summary,
                created_at=stored_comparison.created_at,
                created_by=str(stored_comparison.created_by)
            ))
        
        return ComparisonHistoryResponse(
            comparisons=comparisons,
            total=len(comparisons)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document comparisons: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document comparisons: {str(e)}"
        )


@router.get("/{comparison_id}", response_model=ComparisonResponse)
@protected_route(permissions=[Permission.DOCUMENT_READ])
async def get_comparison(
    comparison_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_document_read),
    _: User = Depends(require_org_access)
):
    """Get a specific comparison by ID"""
    try:
        # Validate comparison ID
        try:
            comp_id = UUID(comparison_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid comparison ID format"
            )
        
        from repositories.document_comparison import DocumentComparisonRepository
        comparison_repo = DocumentComparisonRepository(db)
        
        # Get comparison
        stored_comparison = await comparison_repo.get_by_id(comp_id, str(current_user.org_id))
        
        if not stored_comparison:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comparison not found"
            )
        
        # Parse the stored comparison
        comparison_service = DocumentComparisonService(db)
        result = comparison_service._parse_stored_comparison(stored_comparison)
        
        text_changes = [
            TextChangeResponse(
                change_type=change.change_type.value,
                text=change.text,
                line_number=change.line_number,
                page_number=change.page_number,
                confidence=change.confidence
            )
            for change in result.text_changes
        ]
        
        clause_changes = [
            ClauseChangeResponse(
                change_type=change.change_type.value,
                clause_type=change.clause_type,
                old_text=change.old_text,
                new_text=change.new_text,
                risk_impact=change.risk_impact,
                page_number=change.page_number
            )
            for change in result.clause_changes
        ]
        
        return ComparisonResponse(
            comparison_id=str(stored_comparison.id),
            document_a_id=str(stored_comparison.document_a_id),
            document_b_id=str(stored_comparison.document_b_id),
            document_a_title=stored_comparison.document_a.title,
            document_b_title=stored_comparison.document_b.title,
            text_changes=text_changes,
            clause_changes=clause_changes,
            similarity_score=result.similarity_score,
            risk_assessment=result.risk_assessment,
            summary=result.summary,
            created_at=stored_comparison.created_at,
            created_by=str(stored_comparison.created_by)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting comparison {comparison_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get comparison: {str(e)}"
        )


@router.post("/{comparison_id}/export")
@protected_route(permissions=[Permission.DOCUMENT_READ])
async def export_comparison(
    comparison_id: str,
    format: str = Query("json", description="Export format: json, pdf, or csv"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_document_read),
    _: User = Depends(require_org_access)
):
    """Export comparison results in various formats"""
    try:
        # Validate comparison ID
        try:
            comp_id = UUID(comparison_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid comparison ID format"
            )
        
        if format not in ["json", "pdf", "csv"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported export format. Use json, pdf, or csv"
            )
        
        from repositories.document_comparison import DocumentComparisonRepository
        comparison_repo = DocumentComparisonRepository(db)
        
        # Get comparison
        stored_comparison = await comparison_repo.get_by_id(comp_id, str(current_user.org_id))
        
        if not stored_comparison:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comparison not found"
            )
        
        # For now, return JSON format
        # In a full implementation, you would generate PDF or CSV based on the format parameter
        comparison_service = DocumentComparisonService(db)
        result = comparison_service._parse_stored_comparison(stored_comparison)
        
        export_data = {
            "comparison_id": str(stored_comparison.id),
            "document_a": {
                "id": str(stored_comparison.document_a_id),
                "title": stored_comparison.document_a.title
            },
            "document_b": {
                "id": str(stored_comparison.document_b_id),
                "title": stored_comparison.document_b.title
            },
            "similarity_score": result.similarity_score,
            "summary": result.summary,
            "risk_assessment": result.risk_assessment,
            "text_changes": [
                {
                    "change_type": change.change_type.value,
                    "text": change.text,
                    "line_number": change.line_number,
                    "page_number": change.page_number
                }
                for change in result.text_changes
            ],
            "clause_changes": [
                {
                    "change_type": change.change_type.value,
                    "clause_type": change.clause_type,
                    "old_text": change.old_text,
                    "new_text": change.new_text,
                    "risk_impact": change.risk_impact,
                    "page_number": change.page_number
                }
                for change in result.clause_changes
            ],
            "exported_at": datetime.utcnow().isoformat(),
            "exported_by": str(current_user.id)
        }
        
        logger.info(f"Comparison exported: {comparison_id} in {format} format by user {current_user.id}")
        
        return {
            "export_data": export_data,
            "format": format,
            "filename": f"comparison_{comparison_id}.{format}",
            "exported_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting comparison {comparison_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export comparison: {str(e)}"
        )