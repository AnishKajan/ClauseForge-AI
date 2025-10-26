"""
Document analysis and RAG query endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import logging

from core.database import get_db
from core.auth_dependencies import get_current_user_with_org
from core.rbac import require_role
from models.database import User
from repositories.document import DocumentRepository
from repositories.document_chunk import DocumentChunkRepository
from repositories.clause import ClauseRepository
from repositories.playbook import PlaybookRepository
from repositories.analysis import AnalysisRepository
from services.compliance import ComplianceEngine
from services.risk_assessment import RiskScoringEngine, RiskAssessment
from services.playbook_templates import get_playbook_by_type, get_available_playbook_types

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response Models
class AnalysisRequest(BaseModel):
    document_id: str
    playbook_id: Optional[str] = None


class ClauseMatchResponse(BaseModel):
    clause_type: str
    text: str
    confidence: float
    page: int
    risk_level: str
    matched_rule: Optional[str] = None


class ComplianceResultResponse(BaseModel):
    rule_id: str
    rule_name: str
    status: str
    matched_clauses: List[ClauseMatchResponse]
    missing_clause: bool
    risk_score: float
    recommendations: List[str]


class RiskFactorResponse(BaseModel):
    factor_id: str
    name: str
    description: str
    weight: float
    score: float
    category: str
    recommendations: List[str]


class RiskScoreResponse(BaseModel):
    overall_score: int
    category: str
    confidence: float
    factors: List[RiskFactorResponse]
    trend: Optional[str] = None


class RecommendationResponse(BaseModel):
    id: str
    title: str
    description: str
    priority: str
    category: str
    impact: str
    effort: str
    clause_types: List[str]
    suggested_language: Optional[str] = None


class AnalysisResponse(BaseModel):
    id: str
    document_id: str
    playbook_id: str
    risk_score: RiskScoreResponse
    compliance_results: List[ComplianceResultResponse]
    recommendations: List[RecommendationResponse]
    missing_clauses: List[str]
    compliance_summary: Dict[str, Any]
    created_at: datetime


class AnalysisHistoryResponse(BaseModel):
    analyses: List[AnalysisResponse]
    total_count: int


class PlaybookResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_default: bool
    rules_count: int
    created_at: datetime


class PlaybookCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    playbook_type: str  # "standard", "employment", "vendor", "saas"
    is_default: bool = False


class ComparisonRequest(BaseModel):
    document_id_1: str
    document_id_2: str
    playbook_id: Optional[str] = None


# Helper functions
def _convert_analysis_to_response(analysis_result, risk_assessment: RiskAssessment) -> AnalysisResponse:
    """Convert internal analysis result to API response"""
    
    # Convert compliance results
    compliance_results = []
    for cr in analysis_result.compliance_results:
        matched_clauses = [
            ClauseMatchResponse(
                clause_type=mc.clause_type,
                text=mc.text,
                confidence=mc.confidence,
                page=mc.page,
                risk_level=mc.risk_level.value,
                matched_rule=mc.matched_rule
            )
            for mc in cr.matched_clauses
        ]
        
        compliance_results.append(ComplianceResultResponse(
            rule_id=cr.rule_id,
            rule_name=cr.rule_name,
            status=cr.status.value,
            matched_clauses=matched_clauses,
            missing_clause=cr.missing_clause,
            risk_score=cr.risk_score,
            recommendations=cr.recommendations
        ))
    
    # Convert risk factors
    risk_factors = [
        RiskFactorResponse(
            factor_id=rf.factor_id,
            name=rf.name,
            description=rf.description,
            weight=rf.weight,
            score=rf.score,
            category=rf.category,
            recommendations=rf.recommendations
        )
        for rf in risk_assessment.risk_score.factors
    ]
    
    # Convert risk score
    risk_score_response = RiskScoreResponse(
        overall_score=risk_assessment.risk_score.overall_score,
        category=risk_assessment.risk_score.category.value,
        confidence=risk_assessment.risk_score.confidence,
        factors=risk_factors,
        trend=risk_assessment.risk_score.trend
    )
    
    # Convert recommendations
    recommendations = [
        RecommendationResponse(
            id=rec.id,
            title=rec.title,
            description=rec.description,
            priority=rec.priority.value,
            category=rec.category,
            impact=rec.impact,
            effort=rec.effort,
            clause_types=rec.clause_types,
            suggested_language=rec.suggested_language
        )
        for rec in risk_assessment.recommendations
    ]
    
    return AnalysisResponse(
        id=str(analysis_result.document_id),  # Using document_id as analysis ID for now
        document_id=str(analysis_result.document_id),
        playbook_id=str(analysis_result.playbook_id),
        risk_score=risk_score_response,
        compliance_results=compliance_results,
        recommendations=recommendations,
        missing_clauses=analysis_result.missing_clauses,
        compliance_summary=risk_assessment.compliance_summary,
        created_at=risk_assessment.assessment_timestamp
    )


# API Endpoints
@router.post("/documents/{document_id}/analyze", response_model=AnalysisResponse)
@require_role(["admin", "reviewer"])
async def analyze_document(
    document_id: str,
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    user_org: tuple[User, str] = Depends(get_current_user_with_org),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze document for compliance and risks
    
    This endpoint performs comprehensive compliance analysis on a document using
    the specified playbook (or default if not provided).
    """
    user, org_id = user_org
    
    try:
        # Initialize repositories
        document_repo = DocumentRepository(db)
        chunk_repo = DocumentChunkRepository(db)
        clause_repo = ClauseRepository(db)
        playbook_repo = PlaybookRepository(db)
        analysis_repo = AnalysisRepository(db)
        
        # Verify document exists and belongs to org
        document = await document_repo.get_by_id(UUID(document_id), org_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check if document is processed
        if document.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document must be fully processed before analysis"
            )
        
        # Initialize compliance engine
        compliance_engine = ComplianceEngine(
            document_repo=document_repo,
            chunk_repo=chunk_repo,
            clause_repo=clause_repo,
            playbook_repo=playbook_repo,
            analysis_repo=analysis_repo
        )
        
        # Initialize risk scoring engine
        risk_engine = RiskScoringEngine(
            analysis_repo=analysis_repo,
            document_repo=document_repo
        )
        
        # Parse playbook_id if provided
        playbook_id = UUID(request.playbook_id) if request.playbook_id else None
        
        # Perform analysis
        analysis_result = await compliance_engine.analyze_document(
            document_id=UUID(document_id),
            org_id=org_id,
            playbook_id=playbook_id
        )
        
        # Create risk assessment
        risk_assessment = await risk_engine.create_risk_assessment(
            analysis_result=analysis_result,
            org_id=org_id
        )
        
        # Save analysis to database
        saved_analysis = await compliance_engine.save_analysis_result(
            analysis_result, org_id
        )
        
        # Convert to response format
        response = _convert_analysis_to_response(analysis_result, risk_assessment)
        response.id = str(saved_analysis.id)
        
        logger.info(f"Document {document_id} analyzed successfully. Risk score: {risk_assessment.risk_score.overall_score}")
        
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error analyzing document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed"
        )


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
@require_role(["admin", "reviewer", "viewer"])
async def get_analysis(
    analysis_id: str,
    user_org: tuple[User, str] = Depends(get_current_user_with_org),
    db: AsyncSession = Depends(get_db)
):
    """Get analysis results by ID"""
    user, org_id = user_org
    
    try:
        analysis_repo = AnalysisRepository(db)
        analysis = await analysis_repo.get_by_id(UUID(analysis_id), org_id)
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        # Convert stored analysis to response format
        # Note: This is a simplified conversion since we're working with stored data
        risk_score_response = RiskScoreResponse(
            overall_score=analysis.risk_score or 0,
            category="unknown",  # Would need to recalculate or store
            confidence=0.8,  # Default confidence
            factors=[],  # Would need to reconstruct from summary_json
            trend=None
        )
        
        response = AnalysisResponse(
            id=str(analysis.id),
            document_id=str(analysis.document_id),
            playbook_id=str(analysis.playbook_id) if analysis.playbook_id else "",
            risk_score=risk_score_response,
            compliance_results=[],  # Would reconstruct from summary_json
            recommendations=analysis.recommendations or [],
            missing_clauses=[],  # Would extract from summary_json
            compliance_summary=analysis.summary_json or {},
            created_at=analysis.created_at
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving analysis {analysis_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analysis"
        )


@router.get("/documents/{document_id}/analyses", response_model=AnalysisHistoryResponse)
@require_role(["admin", "reviewer", "viewer"])
async def get_document_analyses(
    document_id: str,
    limit: int = 10,
    offset: int = 0,
    user_org: tuple[User, str] = Depends(get_current_user_with_org),
    db: AsyncSession = Depends(get_db)
):
    """Get analysis history for a document"""
    user, org_id = user_org
    
    try:
        analysis_repo = AnalysisRepository(db)
        analyses = await analysis_repo.get_by_document(UUID(document_id), org_id)
        
        # Apply pagination
        total_count = len(analyses)
        paginated_analyses = analyses[offset:offset + limit]
        
        # Convert to response format (simplified)
        analysis_responses = []
        for analysis in paginated_analyses:
            risk_score_response = RiskScoreResponse(
                overall_score=analysis.risk_score or 0,
                category="unknown",
                confidence=0.8,
                factors=[],
                trend=None
            )
            
            response = AnalysisResponse(
                id=str(analysis.id),
                document_id=str(analysis.document_id),
                playbook_id=str(analysis.playbook_id) if analysis.playbook_id else "",
                risk_score=risk_score_response,
                compliance_results=[],
                recommendations=analysis.recommendations or [],
                missing_clauses=[],
                compliance_summary=analysis.summary_json or {},
                created_at=analysis.created_at
            )
            analysis_responses.append(response)
        
        return AnalysisHistoryResponse(
            analyses=analysis_responses,
            total_count=total_count
        )
        
    except Exception as e:
        logger.error(f"Error retrieving analyses for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analysis history"
        )


@router.get("/playbooks", response_model=List[PlaybookResponse])
@require_role(["admin", "reviewer", "viewer"])
async def get_playbooks(
    user_org: tuple[User, str] = Depends(get_current_user_with_org),
    db: AsyncSession = Depends(get_db)
):
    """Get available playbooks for organization"""
    user, org_id = user_org
    
    try:
        playbook_repo = PlaybookRepository(db)
        playbooks = await playbook_repo.get_by_org(org_id)
        
        response = []
        for playbook in playbooks:
            rules_count = len(playbook.rules_json.get("rules", [])) if playbook.rules_json else 0
            
            response.append(PlaybookResponse(
                id=str(playbook.id),
                name=playbook.name,
                description=playbook.rules_json.get("description") if playbook.rules_json else None,
                is_default=playbook.is_default,
                rules_count=rules_count,
                created_at=playbook.created_at
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving playbooks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve playbooks"
        )


@router.post("/playbooks", response_model=PlaybookResponse)
@require_role(["admin"])
async def create_playbook(
    request: PlaybookCreateRequest,
    user_org: tuple[User, str] = Depends(get_current_user_with_org),
    db: AsyncSession = Depends(get_db)
):
    """Create a new playbook from template"""
    user, org_id = user_org
    
    try:
        # Validate playbook type
        available_types = get_available_playbook_types()
        if request.playbook_type not in available_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid playbook type. Available types: {', '.join(available_types)}"
            )
        
        # Get playbook template
        playbook_template = get_playbook_by_type(request.playbook_type)
        
        # Override name and description if provided
        if request.name:
            playbook_template["name"] = request.name
        if request.description:
            playbook_template["description"] = request.description
        
        # Create playbook
        playbook_repo = PlaybookRepository(db)
        playbook = await playbook_repo.create_with_validation(
            org_id=org_id,
            name=playbook_template["name"],
            rules_json=playbook_template,
            is_default=request.is_default
        )
        
        # If this is set as default, update other playbooks
        if request.is_default:
            await playbook_repo.set_as_default(playbook.id, org_id)
        
        await db.commit()
        
        rules_count = len(playbook_template.get("rules", []))
        
        return PlaybookResponse(
            id=str(playbook.id),
            name=playbook.name,
            description=playbook_template.get("description"),
            is_default=playbook.is_default,
            rules_count=rules_count,
            created_at=playbook.created_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating playbook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create playbook"
        )


@router.get("/playbook-types")
@require_role(["admin", "reviewer"])
async def get_playbook_types():
    """Get available playbook template types"""
    return {
        "types": get_available_playbook_types(),
        "descriptions": {
            "standard": "Comprehensive compliance rules for standard business contracts",
            "employment": "Compliance rules for employment agreements",
            "vendor": "Compliance rules for vendor and supplier agreements",
            "saas": "Compliance rules for Software as a Service agreements"
        }
    }


@router.post("/compare", response_model=Dict[str, Any])
@require_role(["admin", "reviewer"])
async def compare_documents(
    request: ComparisonRequest,
    user_org: tuple[User, str] = Depends(get_current_user_with_org),
    db: AsyncSession = Depends(get_db)
):
    """Compare two documents (placeholder for future implementation)"""
    user, org_id = user_org
    
    # This is a placeholder for document comparison functionality
    # which would be implemented in a future task
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Document comparison will be implemented in task 8"
    )