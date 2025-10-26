"""
Analysis repository
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.database import Analysis
from .base import BaseRepository


class AnalysisRepository(BaseRepository[Analysis]):
    """Repository for Analysis model"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Analysis, session)
    
    async def get_by_document(self, document_id: UUID, org_id: str) -> List[Analysis]:
        """Get all analyses for a document"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .where(self.model.document_id == document_id)
            .order_by(self.model.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_latest_by_document(self, document_id: UUID, org_id: str) -> Optional[Analysis]:
        """Get the latest analysis for a document"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .where(self.model.document_id == document_id)
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_by_playbook(self, playbook_id: UUID, org_id: str) -> List[Analysis]:
        """Get analyses by playbook"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .where(self.model.playbook_id == playbook_id)
            .order_by(self.model.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_by_risk_score_range(
        self, 
        min_score: int, 
        max_score: int, 
        org_id: str
    ) -> List[Analysis]:
        """Get analyses by risk score range"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model).where(
                and_(
                    self.model.risk_score >= min_score,
                    self.model.risk_score <= max_score
                )
            )
        )
        return result.scalars().all()
    
    async def get_high_risk(self, org_id: str, risk_threshold: int = 70) -> List[Analysis]:
        """Get high risk analyses"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .where(self.model.risk_score >= risk_threshold)
            .order_by(self.model.risk_score.desc())
        )
        return result.scalars().all()
    
    async def get_recent(self, org_id: str, limit: int = 10) -> List[Analysis]:
        """Get recent analyses"""
        await self.set_org_context(org_id)
        
        result = await self.session.execute(
            select(self.model)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_analysis_stats(self, org_id: str) -> dict:
        """Get analysis statistics for organization"""
        await self.set_org_context(org_id)
        
        # Get all analyses
        result = await self.session.execute(select(self.model))
        analyses = result.scalars().all()
        
        if not analyses:
            return {
                "total_analyses": 0,
                "avg_risk_score": 0,
                "high_risk_count": 0,
                "medium_risk_count": 0,
                "low_risk_count": 0
            }
        
        risk_scores = [a.risk_score for a in analyses if a.risk_score is not None]
        
        return {
            "total_analyses": len(analyses),
            "avg_risk_score": sum(risk_scores) / len(risk_scores) if risk_scores else 0,
            "high_risk_count": len([s for s in risk_scores if s >= 70]),
            "medium_risk_count": len([s for s in risk_scores if 30 <= s < 70]),
            "low_risk_count": len([s for s in risk_scores if s < 30])
        }
    
    async def delete_by_document(self, document_id: UUID, org_id: str) -> int:
        """Delete all analyses for a document"""
        await self.set_org_context(org_id)
        
        analyses = await self.get_by_document(document_id, org_id)
        count = len(analyses)
        
        for analysis in analyses:
            await self.session.delete(analysis)
        
        await self.session.flush()
        return count