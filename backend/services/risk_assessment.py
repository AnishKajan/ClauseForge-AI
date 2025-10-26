"""
Risk assessment and recommendation system for contract analysis
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from uuid import UUID

from services.compliance import ComplianceResult, ComplianceStatus, AnalysisResult
from repositories.analysis import AnalysisRepository
from repositories.document import DocumentRepository


class RiskCategory(Enum):
    """Risk category enumeration"""
    CRITICAL = "critical"  # 80-100
    HIGH = "high"         # 60-79
    MEDIUM = "medium"     # 30-59
    LOW = "low"          # 0-29


class RecommendationPriority(Enum):
    """Recommendation priority levels"""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RiskFactor:
    """Individual risk factor"""
    factor_id: str
    name: str
    description: str
    weight: float
    score: float
    category: str
    recommendations: List[str]


@dataclass
class RiskScore:
    """Comprehensive risk score"""
    overall_score: int
    category: RiskCategory
    confidence: float
    factors: List[RiskFactor]
    trend: Optional[str] = None  # "improving", "stable", "deteriorating"


@dataclass
class Recommendation:
    """Risk mitigation recommendation"""
    id: str
    title: str
    description: str
    priority: RecommendationPriority
    category: str
    impact: str  # "high", "medium", "low"
    effort: str  # "high", "medium", "low"
    clause_types: List[str]
    suggested_language: Optional[str] = None


@dataclass
class RiskAssessment:
    """Complete risk assessment"""
    document_id: UUID
    risk_score: RiskScore
    recommendations: List[Recommendation]
    compliance_summary: Dict[str, Any]
    assessment_timestamp: datetime


class RiskScoringEngine:
    """Advanced risk scoring and recommendation engine"""
    
    def __init__(
        self,
        analysis_repo: AnalysisRepository,
        document_repo: DocumentRepository
    ):
        self.analysis_repo = analysis_repo
        self.document_repo = document_repo
    
    def calculate_risk_score(self, compliance_results: List[ComplianceResult]) -> RiskScore:
        """
        Calculate comprehensive risk score from compliance results
        """
        if not compliance_results:
            return RiskScore(
                overall_score=0,
                category=RiskCategory.LOW,
                confidence=1.0,
                factors=[]
            )
        
        # Calculate individual risk factors
        risk_factors = []
        total_weighted_score = 0
        total_weight = 0
        
        for result in compliance_results:
            factor = self._create_risk_factor(result)
            risk_factors.append(factor)
            
            total_weighted_score += factor.score * factor.weight
            total_weight += factor.weight
        
        # Calculate overall score
        if total_weight > 0:
            base_score = total_weighted_score / total_weight
        else:
            base_score = 0
        
        # Apply risk multipliers
        multiplied_score = self._apply_risk_multipliers(base_score, compliance_results)
        
        # Normalize to 0-100 scale
        overall_score = min(100, max(0, int(multiplied_score)))
        
        # Determine category
        category = self._get_risk_category(overall_score)
        
        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(compliance_results)
        
        return RiskScore(
            overall_score=overall_score,
            category=category,
            confidence=confidence,
            factors=risk_factors
        )
    
    def _create_risk_factor(self, compliance_result: ComplianceResult) -> RiskFactor:
        """Create risk factor from compliance result"""
        # Determine factor weight based on rule importance
        weight = self._get_factor_weight(compliance_result.rule_id)
        
        # Calculate factor score
        score = compliance_result.risk_score
        
        # Determine category
        category = self._categorize_risk_factor(compliance_result.rule_id)
        
        return RiskFactor(
            factor_id=compliance_result.rule_id,
            name=compliance_result.rule_name,
            description=f"Compliance status: {compliance_result.status.value}",
            weight=weight,
            score=score,
            category=category,
            recommendations=compliance_result.recommendations
        )
    
    def _get_factor_weight(self, rule_id: str) -> float:
        """Get weight for specific rule type"""
        weights = {
            # Critical legal protections
            "indemnity_clause": 1.0,
            "liability_cap": 0.9,
            "intellectual_property": 0.9,
            "data_security": 0.9,
            "data_ownership": 0.9,
            
            # Important operational terms
            "termination_clause": 0.8,
            "confidentiality_clause": 0.8,
            "service_level_agreement": 0.8,
            "uptime_guarantee": 0.8,
            
            # Standard provisions
            "governing_law": 0.7,
            "payment_terms": 0.7,
            "insurance_requirements": 0.7,
            
            # Optional but beneficial
            "force_majeure": 0.5,
            "non_compete": 0.6,
            "at_will_employment": 0.6
        }
        
        return weights.get(rule_id, 0.5)  # Default weight
    
    def _categorize_risk_factor(self, rule_id: str) -> str:
        """Categorize risk factor by type"""
        categories = {
            "indemnity_clause": "Legal Protection",
            "liability_cap": "Legal Protection",
            "intellectual_property": "IP & Data",
            "data_security": "IP & Data",
            "data_ownership": "IP & Data",
            "confidentiality_clause": "IP & Data",
            "termination_clause": "Operational",
            "service_level_agreement": "Operational",
            "uptime_guarantee": "Operational",
            "payment_terms": "Financial",
            "insurance_requirements": "Financial",
            "governing_law": "Legal Framework",
            "force_majeure": "Risk Management",
            "non_compete": "Employment",
            "at_will_employment": "Employment"
        }
        
        return categories.get(rule_id, "General")
    
    def _apply_risk_multipliers(
        self, 
        base_score: float, 
        compliance_results: List[ComplianceResult]
    ) -> float:
        """Apply risk multipliers based on specific conditions"""
        multiplier = 1.0
        
        # Critical missing clauses multiplier
        critical_missing = [
            r for r in compliance_results 
            if r.missing_clause and r.rule_id in ["indemnity_clause", "liability_cap", "data_security"]
        ]
        if critical_missing:
            multiplier += 0.2 * len(critical_missing)
        
        # Multiple non-compliant rules multiplier
        non_compliant_count = sum(
            1 for r in compliance_results 
            if r.status == ComplianceStatus.NON_COMPLIANT
        )
        if non_compliant_count >= 3:
            multiplier += 0.15
        
        # Low confidence matches multiplier
        low_confidence_matches = [
            r for r in compliance_results 
            if r.matched_clauses and any(m.confidence < 0.6 for m in r.matched_clauses)
        ]
        if low_confidence_matches:
            multiplier += 0.1
        
        return base_score * multiplier
    
    def _get_risk_category(self, score: int) -> RiskCategory:
        """Determine risk category from score"""
        if score >= 80:
            return RiskCategory.CRITICAL
        elif score >= 60:
            return RiskCategory.HIGH
        elif score >= 30:
            return RiskCategory.MEDIUM
        else:
            return RiskCategory.LOW
    
    def _calculate_confidence(self, compliance_results: List[ComplianceResult]) -> float:
        """Calculate confidence in risk assessment"""
        if not compliance_results:
            return 0.0
        
        # Base confidence
        confidence = 0.8
        
        # Boost confidence for more rules evaluated
        rule_count_boost = min(0.15, len(compliance_results) * 0.02)
        confidence += rule_count_boost
        
        # Reduce confidence for low-confidence matches
        total_matches = sum(len(r.matched_clauses) for r in compliance_results)
        if total_matches > 0:
            avg_match_confidence = sum(
                sum(m.confidence for m in r.matched_clauses) 
                for r in compliance_results if r.matched_clauses
            ) / total_matches
            
            confidence_adjustment = (avg_match_confidence - 0.7) * 0.2
            confidence += confidence_adjustment
        
        return min(1.0, max(0.0, confidence))
    
    def generate_recommendations(
        self, 
        compliance_results: List[ComplianceResult],
        risk_score: RiskScore
    ) -> List[Recommendation]:
        """Generate prioritized recommendations"""
        recommendations = []
        
        # Generate recommendations from compliance results
        for result in compliance_results:
            if result.status != ComplianceStatus.COMPLIANT:
                recs = self._create_recommendations_for_rule(result, risk_score)
                recommendations.extend(recs)
        
        # Add strategic recommendations based on overall risk
        strategic_recs = self._generate_strategic_recommendations(risk_score)
        recommendations.extend(strategic_recs)
        
        # Sort by priority and impact
        recommendations.sort(key=lambda r: (
            self._get_priority_weight(r.priority),
            self._get_impact_weight(r.impact)
        ), reverse=True)
        
        return recommendations
    
    def _create_recommendations_for_rule(
        self, 
        compliance_result: ComplianceResult,
        risk_score: RiskScore
    ) -> List[Recommendation]:
        """Create specific recommendations for a compliance rule"""
        recommendations = []
        
        # Determine priority based on rule importance and risk level
        priority = self._determine_recommendation_priority(
            compliance_result.rule_id,
            compliance_result.status,
            risk_score.category
        )
        
        # Get rule-specific recommendations
        rule_recommendations = self._get_rule_recommendations(compliance_result.rule_id)
        
        for i, rec_text in enumerate(compliance_result.recommendations):
            rec_id = f"{compliance_result.rule_id}_{i}"
            
            # Get additional details for this recommendation
            details = rule_recommendations.get(rec_text, {})
            
            recommendation = Recommendation(
                id=rec_id,
                title=f"Address {compliance_result.rule_name}",
                description=rec_text,
                priority=priority,
                category=self._categorize_risk_factor(compliance_result.rule_id),
                impact=details.get("impact", "medium"),
                effort=details.get("effort", "medium"),
                clause_types=[compliance_result.rule_id],
                suggested_language=details.get("suggested_language")
            )
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def _determine_recommendation_priority(
        self,
        rule_id: str,
        status: ComplianceStatus,
        risk_category: RiskCategory
    ) -> RecommendationPriority:
        """Determine recommendation priority"""
        # Critical rules always get high priority when non-compliant
        critical_rules = ["indemnity_clause", "liability_cap", "data_security", "intellectual_property"]
        
        if rule_id in critical_rules and status == ComplianceStatus.NON_COMPLIANT:
            return RecommendationPriority.URGENT
        
        # High-risk documents need urgent attention
        if risk_category == RiskCategory.CRITICAL:
            if status == ComplianceStatus.NON_COMPLIANT:
                return RecommendationPriority.URGENT
            elif status == ComplianceStatus.REVIEW_REQUIRED:
                return RecommendationPriority.HIGH
        
        # Standard priority mapping
        if status == ComplianceStatus.NON_COMPLIANT:
            return RecommendationPriority.HIGH
        elif status == ComplianceStatus.REVIEW_REQUIRED:
            return RecommendationPriority.MEDIUM
        else:
            return RecommendationPriority.LOW
    
    def _get_rule_recommendations(self, rule_id: str) -> Dict[str, Dict[str, str]]:
        """Get detailed recommendations for specific rules"""
        recommendations = {
            "indemnity_clause": {
                "Add mutual indemnity clause to protect both parties": {
                    "impact": "high",
                    "effort": "medium",
                    "suggested_language": "Each party shall indemnify, defend, and hold harmless the other party from and against any and all claims, damages, losses, and expenses arising out of or resulting from the indemnifying party's breach of this Agreement or negligent or wrongful acts."
                }
            },
            "liability_cap": {
                "Include reasonable liability caps to limit exposure": {
                    "impact": "high",
                    "effort": "low",
                    "suggested_language": "In no event shall either party's total liability under this Agreement exceed the total amount paid or payable by Customer under this Agreement in the twelve (12) months preceding the event giving rise to liability."
                }
            },
            "termination_clause": {
                "Include termination for cause provisions": {
                    "impact": "medium",
                    "effort": "low",
                    "suggested_language": "Either party may terminate this Agreement immediately upon written notice if the other party materially breaches this Agreement and fails to cure such breach within thirty (30) days after written notice."
                }
            }
        }
        
        return recommendations.get(rule_id, {})
    
    def _generate_strategic_recommendations(self, risk_score: RiskScore) -> List[Recommendation]:
        """Generate high-level strategic recommendations"""
        recommendations = []
        
        if risk_score.category == RiskCategory.CRITICAL:
            recommendations.append(Recommendation(
                id="strategic_legal_review",
                title="Immediate Legal Review Required",
                description="This contract presents critical risks that require immediate attention from legal counsel before execution.",
                priority=RecommendationPriority.URGENT,
                category="Strategic",
                impact="high",
                effort="high",
                clause_types=[]
            ))
        
        elif risk_score.category == RiskCategory.HIGH:
            recommendations.append(Recommendation(
                id="strategic_risk_mitigation",
                title="Comprehensive Risk Mitigation",
                description="Consider implementing additional risk mitigation strategies and obtaining appropriate insurance coverage.",
                priority=RecommendationPriority.HIGH,
                category="Strategic",
                impact="medium",
                effort="medium",
                clause_types=[]
            ))
        
        # Low confidence recommendations
        if risk_score.confidence < 0.7:
            recommendations.append(Recommendation(
                id="strategic_manual_review",
                title="Manual Review Recommended",
                description="The automated analysis has low confidence. Manual review by legal experts is recommended to validate findings.",
                priority=RecommendationPriority.HIGH,
                category="Process",
                impact="medium",
                effort="high",
                clause_types=[]
            ))
        
        return recommendations
    
    def _get_priority_weight(self, priority: RecommendationPriority) -> int:
        """Get numeric weight for priority sorting"""
        weights = {
            RecommendationPriority.URGENT: 4,
            RecommendationPriority.HIGH: 3,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 1
        }
        return weights[priority]
    
    def _get_impact_weight(self, impact: str) -> int:
        """Get numeric weight for impact sorting"""
        weights = {"high": 3, "medium": 2, "low": 1}
        return weights.get(impact, 1)
    
    async def calculate_risk_trend(
        self, 
        document_id: UUID, 
        org_id: str,
        days_back: int = 30
    ) -> Optional[str]:
        """Calculate risk trend for a document over time"""
        # Get historical analyses
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        analyses = await self.analysis_repo.get_by_document(document_id, org_id)
        recent_analyses = [
            a for a in analyses 
            if a.created_at >= cutoff_date and a.risk_score is not None
        ]
        
        if len(recent_analyses) < 2:
            return None
        
        # Sort by date
        recent_analyses.sort(key=lambda a: a.created_at)
        
        # Calculate trend
        first_score = recent_analyses[0].risk_score
        last_score = recent_analyses[-1].risk_score
        
        score_change = last_score - first_score
        
        if score_change > 10:
            return "deteriorating"
        elif score_change < -10:
            return "improving"
        else:
            return "stable"
    
    async def create_risk_assessment(
        self, 
        analysis_result: AnalysisResult,
        org_id: str
    ) -> RiskAssessment:
        """Create comprehensive risk assessment"""
        # Calculate risk score
        risk_score = self.calculate_risk_score(analysis_result.compliance_results)
        
        # Add trend information
        risk_score.trend = await self.calculate_risk_trend(
            analysis_result.document_id, 
            org_id
        )
        
        # Generate recommendations
        recommendations = self.generate_recommendations(
            analysis_result.compliance_results,
            risk_score
        )
        
        # Create compliance summary
        compliance_summary = {
            "total_rules": len(analysis_result.compliance_results),
            "compliant": sum(
                1 for r in analysis_result.compliance_results 
                if r.status == ComplianceStatus.COMPLIANT
            ),
            "non_compliant": sum(
                1 for r in analysis_result.compliance_results 
                if r.status == ComplianceStatus.NON_COMPLIANT
            ),
            "review_required": sum(
                1 for r in analysis_result.compliance_results 
                if r.status == ComplianceStatus.REVIEW_REQUIRED
            ),
            "missing_clauses": len(analysis_result.missing_clauses),
            "overall_status": analysis_result.compliance_status.value
        }
        
        return RiskAssessment(
            document_id=analysis_result.document_id,
            risk_score=risk_score,
            recommendations=recommendations,
            compliance_summary=compliance_summary,
            assessment_timestamp=datetime.utcnow()
        )