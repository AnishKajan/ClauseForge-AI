"""
Compliance analysis service for rule-based contract evaluation
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from models.database import Document, DocumentChunk, Clause, Playbook, Analysis
from repositories.document import DocumentRepository
from repositories.document_chunk import DocumentChunkRepository
from repositories.clause import ClauseRepository
from repositories.playbook import PlaybookRepository
from repositories.analysis import AnalysisRepository


class RiskLevel(Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceStatus(Enum):
    """Compliance status enumeration"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    REVIEW_REQUIRED = "review_required"


@dataclass
class ClauseMatch:
    """Represents a matched clause in the document"""
    clause_type: str
    text: str
    confidence: float
    page: int
    risk_level: RiskLevel
    matched_rule: Optional[str] = None


@dataclass
class ComplianceRule:
    """Represents a compliance rule from playbook"""
    id: str
    name: str
    description: str
    clause_type: str
    required: bool
    patterns: List[str]
    risk_weight: float
    recommendations: List[str]


@dataclass
class ComplianceResult:
    """Result of compliance evaluation"""
    rule_id: str
    rule_name: str
    status: ComplianceStatus
    matched_clauses: List[ClauseMatch]
    missing_clause: bool
    risk_score: float
    recommendations: List[str]


@dataclass
class AnalysisResult:
    """Complete analysis result"""
    document_id: UUID
    playbook_id: UUID
    overall_risk_score: int
    compliance_status: ComplianceStatus
    compliance_results: List[ComplianceResult]
    missing_clauses: List[str]
    recommendations: List[str]
    summary: Dict[str, Any]


class ComplianceEngine:
    """Rule-based compliance engine for contract analysis"""
    
    def __init__(
        self,
        document_repo: DocumentRepository,
        chunk_repo: DocumentChunkRepository,
        clause_repo: ClauseRepository,
        playbook_repo: PlaybookRepository,
        analysis_repo: AnalysisRepository
    ):
        self.document_repo = document_repo
        self.chunk_repo = chunk_repo
        self.clause_repo = clause_repo
        self.playbook_repo = playbook_repo
        self.analysis_repo = analysis_repo
    
    def validate_playbook_schema(self, rules_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate playbook JSON schema
        
        Expected schema:
        {
            "version": "1.0",
            "name": "Standard Contract Playbook",
            "description": "...",
            "rules": [
                {
                    "id": "indemnity_clause",
                    "name": "Indemnity Clause",
                    "description": "...",
                    "clause_type": "indemnity",
                    "required": true,
                    "patterns": ["indemnify", "hold harmless", "defend"],
                    "risk_weight": 0.8,
                    "recommendations": ["Add mutual indemnity clause"]
                }
            ]
        }
        """
        errors = []
        
        # Check required top-level fields
        required_fields = ["version", "name", "rules"]
        for field in required_fields:
            if field not in rules_json:
                errors.append(f"Missing required field: {field}")
        
        # Validate rules array
        if "rules" in rules_json:
            if not isinstance(rules_json["rules"], list):
                errors.append("'rules' must be an array")
            else:
                for i, rule in enumerate(rules_json["rules"]):
                    rule_errors = self._validate_rule_schema(rule, i)
                    errors.extend(rule_errors)
        
        return len(errors) == 0, errors
    
    def _validate_rule_schema(self, rule: Dict[str, Any], index: int) -> List[str]:
        """Validate individual rule schema"""
        errors = []
        prefix = f"Rule {index}"
        
        # Required fields
        required_fields = ["id", "name", "clause_type", "required", "patterns", "risk_weight"]
        for field in required_fields:
            if field not in rule:
                errors.append(f"{prefix}: Missing required field '{field}'")
        
        # Type validations
        if "id" in rule and not isinstance(rule["id"], str):
            errors.append(f"{prefix}: 'id' must be a string")
        
        if "name" in rule and not isinstance(rule["name"], str):
            errors.append(f"{prefix}: 'name' must be a string")
        
        if "clause_type" in rule and not isinstance(rule["clause_type"], str):
            errors.append(f"{prefix}: 'clause_type' must be a string")
        
        if "required" in rule and not isinstance(rule["required"], bool):
            errors.append(f"{prefix}: 'required' must be a boolean")
        
        if "patterns" in rule:
            if not isinstance(rule["patterns"], list):
                errors.append(f"{prefix}: 'patterns' must be an array")
            elif not all(isinstance(p, str) for p in rule["patterns"]):
                errors.append(f"{prefix}: All patterns must be strings")
        
        if "risk_weight" in rule:
            if not isinstance(rule["risk_weight"], (int, float)):
                errors.append(f"{prefix}: 'risk_weight' must be a number")
            elif not 0 <= rule["risk_weight"] <= 1:
                errors.append(f"{prefix}: 'risk_weight' must be between 0 and 1")
        
        if "recommendations" in rule and not isinstance(rule["recommendations"], list):
            errors.append(f"{prefix}: 'recommendations' must be an array")
        
        return errors
    
    def parse_playbook_rules(self, rules_json: Dict[str, Any]) -> List[ComplianceRule]:
        """Parse playbook JSON into ComplianceRule objects"""
        rules = []
        
        for rule_data in rules_json.get("rules", []):
            rule = ComplianceRule(
                id=rule_data["id"],
                name=rule_data["name"],
                description=rule_data.get("description", ""),
                clause_type=rule_data["clause_type"],
                required=rule_data["required"],
                patterns=rule_data["patterns"],
                risk_weight=rule_data["risk_weight"],
                recommendations=rule_data.get("recommendations", [])
            )
            rules.append(rule)
        
        return rules
    
    async def analyze_document(
        self, 
        document_id: UUID, 
        org_id: str,
        playbook_id: Optional[UUID] = None
    ) -> AnalysisResult:
        """
        Perform comprehensive compliance analysis on a document
        """
        # Get document
        document = await self.document_repo.get_by_id(document_id, org_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Get playbook (default if not specified)
        if playbook_id:
            playbook = await self.playbook_repo.get_by_id(playbook_id, org_id)
        else:
            playbook = await self.playbook_repo.get_default(org_id)
        
        if not playbook:
            raise ValueError("No playbook found for analysis")
        
        # Validate playbook schema
        is_valid, errors = self.validate_playbook_schema(playbook.rules_json)
        if not is_valid:
            raise ValueError(f"Invalid playbook schema: {', '.join(errors)}")
        
        # Parse rules
        rules = self.parse_playbook_rules(playbook.rules_json)
        
        # Get document content
        chunks = await self.chunk_repo.get_by_document(document_id, org_id)
        document_text = " ".join([chunk.text for chunk in chunks])
        
        # Run compliance evaluation
        compliance_results = []
        for rule in rules:
            result = await self._evaluate_rule(rule, document_text, chunks, org_id)
            compliance_results.append(result)
        
        # Calculate overall risk score and status
        overall_risk_score = self._calculate_overall_risk_score(compliance_results)
        compliance_status = self._determine_compliance_status(compliance_results)
        
        # Identify missing clauses
        missing_clauses = [
            result.rule_name for result in compliance_results 
            if result.missing_clause and result.status == ComplianceStatus.NON_COMPLIANT
        ]
        
        # Aggregate recommendations
        recommendations = []
        for result in compliance_results:
            recommendations.extend(result.recommendations)
        
        # Create summary
        summary = self._create_analysis_summary(compliance_results, overall_risk_score)
        
        return AnalysisResult(
            document_id=document_id,
            playbook_id=playbook.id,
            overall_risk_score=overall_risk_score,
            compliance_status=compliance_status,
            compliance_results=compliance_results,
            missing_clauses=missing_clauses,
            recommendations=recommendations,
            summary=summary
        )
    
    async def _evaluate_rule(
        self, 
        rule: ComplianceRule, 
        document_text: str, 
        chunks: List[DocumentChunk],
        org_id: str
    ) -> ComplianceResult:
        """Evaluate a single compliance rule against document"""
        matched_clauses = []
        
        # Search for pattern matches in document text
        for pattern in rule.patterns:
            matches = self._find_pattern_matches(pattern, document_text, chunks)
            for match in matches:
                matched_clauses.append(ClauseMatch(
                    clause_type=rule.clause_type,
                    text=match["text"],
                    confidence=match["confidence"],
                    page=match["page"],
                    risk_level=self._determine_clause_risk_level(match["confidence"]),
                    matched_rule=rule.id
                ))
        
        # Determine compliance status
        if rule.required and not matched_clauses:
            status = ComplianceStatus.NON_COMPLIANT
            missing_clause = True
            risk_score = rule.risk_weight * 100  # Full risk weight if missing required clause
        elif matched_clauses:
            # Check confidence levels
            avg_confidence = sum(m.confidence for m in matched_clauses) / len(matched_clauses)
            if avg_confidence >= 0.8:
                status = ComplianceStatus.COMPLIANT
                risk_score = 0
            elif avg_confidence >= 0.5:
                status = ComplianceStatus.REVIEW_REQUIRED
                risk_score = rule.risk_weight * 30  # Partial risk
            else:
                status = ComplianceStatus.NON_COMPLIANT
                risk_score = rule.risk_weight * 70  # High risk for low confidence
            missing_clause = False
        else:
            # Optional rule not found
            status = ComplianceStatus.COMPLIANT
            missing_clause = False
            risk_score = 0
        
        return ComplianceResult(
            rule_id=rule.id,
            rule_name=rule.name,
            status=status,
            matched_clauses=matched_clauses,
            missing_clause=missing_clause,
            risk_score=risk_score,
            recommendations=rule.recommendations if status != ComplianceStatus.COMPLIANT else []
        )
    
    def _find_pattern_matches(
        self, 
        pattern: str, 
        document_text: str, 
        chunks: List[DocumentChunk]
    ) -> List[Dict[str, Any]]:
        """Find pattern matches in document with context"""
        matches = []
        
        # Create case-insensitive regex pattern
        regex_pattern = re.compile(pattern, re.IGNORECASE)
        
        # Search in each chunk for better page tracking
        for chunk in chunks:
            chunk_matches = list(regex_pattern.finditer(chunk.text))
            
            for match in chunk_matches:
                # Extract context around match
                start = max(0, match.start() - 100)
                end = min(len(chunk.text), match.end() + 100)
                context = chunk.text[start:end].strip()
                
                # Calculate confidence based on context and pattern strength
                confidence = self._calculate_match_confidence(pattern, context, match.group())
                
                matches.append({
                    "text": context,
                    "matched_text": match.group(),
                    "confidence": confidence,
                    "page": chunk.page or 1,
                    "chunk_id": chunk.id
                })
        
        return matches
    
    def _calculate_match_confidence(self, pattern: str, context: str, matched_text: str) -> float:
        """Calculate confidence score for pattern match"""
        base_confidence = 0.7
        
        # Boost confidence for exact matches
        if pattern.lower() == matched_text.lower():
            base_confidence += 0.2
        
        # Boost confidence for legal context keywords
        legal_keywords = [
            "shall", "agreement", "contract", "party", "parties", 
            "liability", "damages", "breach", "termination", "clause"
        ]
        
        context_lower = context.lower()
        keyword_matches = sum(1 for keyword in legal_keywords if keyword in context_lower)
        confidence_boost = min(0.1, keyword_matches * 0.02)
        
        return min(1.0, base_confidence + confidence_boost)
    
    def _determine_clause_risk_level(self, confidence: float) -> RiskLevel:
        """Determine risk level based on confidence"""
        if confidence >= 0.9:
            return RiskLevel.LOW
        elif confidence >= 0.7:
            return RiskLevel.MEDIUM
        elif confidence >= 0.5:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def _calculate_overall_risk_score(self, compliance_results: List[ComplianceResult]) -> int:
        """Calculate overall risk score from compliance results"""
        if not compliance_results:
            return 0
        
        total_risk = sum(result.risk_score for result in compliance_results)
        max_possible_risk = len(compliance_results) * 100
        
        # Normalize to 0-100 scale
        normalized_score = int((total_risk / max_possible_risk) * 100) if max_possible_risk > 0 else 0
        
        return min(100, normalized_score)
    
    def _determine_compliance_status(self, compliance_results: List[ComplianceResult]) -> ComplianceStatus:
        """Determine overall compliance status"""
        if not compliance_results:
            return ComplianceStatus.COMPLIANT
        
        # Count status types
        non_compliant = sum(1 for r in compliance_results if r.status == ComplianceStatus.NON_COMPLIANT)
        review_required = sum(1 for r in compliance_results if r.status == ComplianceStatus.REVIEW_REQUIRED)
        
        # Determine overall status
        if non_compliant > 0:
            return ComplianceStatus.NON_COMPLIANT
        elif review_required > 0:
            return ComplianceStatus.REVIEW_REQUIRED
        else:
            return ComplianceStatus.COMPLIANT
    
    def _create_analysis_summary(
        self, 
        compliance_results: List[ComplianceResult], 
        overall_risk_score: int
    ) -> Dict[str, Any]:
        """Create analysis summary"""
        total_rules = len(compliance_results)
        compliant_rules = sum(1 for r in compliance_results if r.status == ComplianceStatus.COMPLIANT)
        non_compliant_rules = sum(1 for r in compliance_results if r.status == ComplianceStatus.NON_COMPLIANT)
        review_rules = sum(1 for r in compliance_results if r.status == ComplianceStatus.REVIEW_REQUIRED)
        
        return {
            "total_rules_evaluated": total_rules,
            "compliant_rules": compliant_rules,
            "non_compliant_rules": non_compliant_rules,
            "review_required_rules": review_rules,
            "compliance_percentage": int((compliant_rules / total_rules) * 100) if total_rules > 0 else 100,
            "overall_risk_score": overall_risk_score,
            "risk_category": self._get_risk_category(overall_risk_score),
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_risk_category(self, risk_score: int) -> str:
        """Get risk category from score"""
        if risk_score >= 80:
            return "Critical"
        elif risk_score >= 60:
            return "High"
        elif risk_score >= 30:
            return "Medium"
        else:
            return "Low"
    
    async def save_analysis_result(self, result: AnalysisResult, org_id: str) -> Analysis:
        """Save analysis result to database"""
        # Prepare summary JSON
        summary_json = result.summary.copy()
        summary_json["compliance_results"] = [
            {
                "rule_id": cr.rule_id,
                "rule_name": cr.rule_name,
                "status": cr.status.value,
                "risk_score": cr.risk_score,
                "missing_clause": cr.missing_clause,
                "matched_clauses_count": len(cr.matched_clauses)
            }
            for cr in result.compliance_results
        ]
        
        # Create analysis record
        analysis = await self.analysis_repo.create(
            document_id=result.document_id,
            playbook_id=result.playbook_id,
            risk_score=result.overall_risk_score,
            summary_json=summary_json,
            recommendations=result.recommendations,
            org_id=org_id
        )
        
        # Save individual clauses found during analysis
        for compliance_result in result.compliance_results:
            for matched_clause in compliance_result.matched_clauses:
                await self.clause_repo.create(
                    document_id=result.document_id,
                    clause_type=matched_clause.clause_type,
                    text=matched_clause.text,
                    confidence=matched_clause.confidence,
                    page=matched_clause.page,
                    risk_level=matched_clause.risk_level.value,
                    org_id=org_id
                )
        
        return analysis