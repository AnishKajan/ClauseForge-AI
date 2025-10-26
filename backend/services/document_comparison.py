"""
Document comparison service for analyzing differences between contract versions
"""

import difflib
import re
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Document, DocumentChunk, Clause
from repositories.document import DocumentRepository
from repositories.document_chunk import DocumentChunkRepository
from repositories.clause import ClauseRepository
from repositories.document_comparison import DocumentComparisonRepository
from services.risk_assessment import RiskAssessmentService


class ChangeType(Enum):
    """Types of changes detected in document comparison"""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class TextChange:
    """Represents a text change between documents"""
    change_type: ChangeType
    text: str
    line_number: Optional[int] = None
    page_number: Optional[int] = None
    confidence: float = 1.0


@dataclass
class ClauseChange:
    """Represents a clause-level change between documents"""
    change_type: ChangeType
    clause_type: str
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    risk_impact: str = "low"
    page_number: Optional[int] = None


@dataclass
class ComparisonResult:
    """Complete comparison result between two documents"""
    document_a_id: UUID
    document_b_id: UUID
    text_changes: List[TextChange]
    clause_changes: List[ClauseChange]
    similarity_score: float
    risk_assessment: Dict[str, Any]
    summary: str


class DocumentComparisonService:
    """Service for comparing contract documents and analyzing changes"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.document_repo = DocumentRepository(session)
        self.chunk_repo = DocumentChunkRepository(session)
        self.clause_repo = ClauseRepository(session)
        self.comparison_repo = DocumentComparisonRepository(session)
        self.risk_service = RiskAssessmentService(session)
    
    async def compare_documents(
        self,
        document_a_id: UUID,
        document_b_id: UUID,
        org_id: str,
        user_id: UUID
    ) -> ComparisonResult:
        """
        Compare two documents and return detailed analysis of changes
        
        Args:
            document_a_id: First document ID (baseline)
            document_b_id: Second document ID (comparison)
            org_id: Organization ID
            user_id: User performing the comparison
            
        Returns:
            ComparisonResult with detailed change analysis
        """
        # Check if comparison already exists
        existing_comparison = await self.comparison_repo.get_by_documents(
            document_a_id, document_b_id, org_id
        )
        
        if existing_comparison:
            return self._parse_stored_comparison(existing_comparison)
        
        # Get documents with their content
        doc_a = await self.document_repo.get_with_chunks(document_a_id, org_id)
        doc_b = await self.document_repo.get_with_chunks(document_b_id, org_id)
        
        if not doc_a or not doc_b:
            raise ValueError("One or both documents not found")
        
        # Get clauses for both documents
        clauses_a = await self.clause_repo.get_by_document(document_a_id, org_id)
        clauses_b = await self.clause_repo.get_by_document(document_b_id, org_id)
        
        # Perform text-level comparison
        text_changes = await self._compare_text_content(doc_a, doc_b)
        
        # Perform clause-level comparison
        clause_changes = await self._compare_clauses(clauses_a, clauses_b)
        
        # Calculate similarity score
        similarity_score = self._calculate_similarity_score(text_changes)
        
        # Assess risk of changes
        risk_assessment = await self._assess_change_risks(clause_changes, text_changes)
        
        # Generate summary
        summary = self._generate_comparison_summary(text_changes, clause_changes, similarity_score)
        
        # Create comparison result
        result = ComparisonResult(
            document_a_id=document_a_id,
            document_b_id=document_b_id,
            text_changes=text_changes,
            clause_changes=clause_changes,
            similarity_score=similarity_score,
            risk_assessment=risk_assessment,
            summary=summary
        )
        
        # Store comparison result
        await self._store_comparison_result(result, org_id, user_id)
        
        return result
    
    async def _compare_text_content(self, doc_a: Document, doc_b: Document) -> List[TextChange]:
        """Compare text content between two documents"""
        # Combine chunks into full text for each document
        text_a = self._combine_chunks_to_text(doc_a.chunks)
        text_b = self._combine_chunks_to_text(doc_b.chunks)
        
        # Split into lines for comparison
        lines_a = text_a.split('\n')
        lines_b = text_b.split('\n')
        
        # Use difflib for detailed comparison
        differ = difflib.unified_diff(lines_a, lines_b, lineterm='')
        
        changes = []
        line_num = 0
        
        for line in differ:
            if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
                continue
            
            line_num += 1
            
            if line.startswith('+'):
                changes.append(TextChange(
                    change_type=ChangeType.ADDED,
                    text=line[1:],
                    line_number=line_num
                ))
            elif line.startswith('-'):
                changes.append(TextChange(
                    change_type=ChangeType.REMOVED,
                    text=line[1:],
                    line_number=line_num
                ))
        
        return changes
    
    async def _compare_clauses(self, clauses_a: List[Clause], clauses_b: List[Clause]) -> List[ClauseChange]:
        """Compare clauses between two documents"""
        changes = []
        
        # Group clauses by type
        clauses_a_by_type = self._group_clauses_by_type(clauses_a)
        clauses_b_by_type = self._group_clauses_by_type(clauses_b)
        
        # Find all clause types
        all_types = set(clauses_a_by_type.keys()) | set(clauses_b_by_type.keys())
        
        for clause_type in all_types:
            clauses_a_type = clauses_a_by_type.get(clause_type, [])
            clauses_b_type = clauses_b_by_type.get(clause_type, [])
            
            if not clauses_a_type and clauses_b_type:
                # New clause type added
                for clause in clauses_b_type:
                    changes.append(ClauseChange(
                        change_type=ChangeType.ADDED,
                        clause_type=clause_type,
                        new_text=clause.text,
                        risk_impact=self._assess_clause_risk_impact(clause_type, ChangeType.ADDED),
                        page_number=clause.page
                    ))
            elif clauses_a_type and not clauses_b_type:
                # Clause type removed
                for clause in clauses_a_type:
                    changes.append(ClauseChange(
                        change_type=ChangeType.REMOVED,
                        clause_type=clause_type,
                        old_text=clause.text,
                        risk_impact=self._assess_clause_risk_impact(clause_type, ChangeType.REMOVED),
                        page_number=clause.page
                    ))
            elif clauses_a_type and clauses_b_type:
                # Compare existing clauses
                clause_changes = self._compare_clause_texts(clauses_a_type, clauses_b_type, clause_type)
                changes.extend(clause_changes)
        
        return changes
    
    def _compare_clause_texts(self, clauses_a: List[Clause], clauses_b: List[Clause], clause_type: str) -> List[ClauseChange]:
        """Compare text content of clauses of the same type"""
        changes = []
        
        # For simplicity, compare the first clause of each type
        # In a more sophisticated implementation, we could use fuzzy matching
        if clauses_a and clauses_b:
            clause_a = clauses_a[0]
            clause_b = clauses_b[0]
            
            # Calculate text similarity
            similarity = difflib.SequenceMatcher(None, clause_a.text, clause_b.text).ratio()
            
            if similarity < 0.8:  # Threshold for considering it modified
                changes.append(ClauseChange(
                    change_type=ChangeType.MODIFIED,
                    clause_type=clause_type,
                    old_text=clause_a.text,
                    new_text=clause_b.text,
                    risk_impact=self._assess_clause_risk_impact(clause_type, ChangeType.MODIFIED),
                    page_number=clause_b.page
                ))
        
        return changes
    
    def _group_clauses_by_type(self, clauses: List[Clause]) -> Dict[str, List[Clause]]:
        """Group clauses by their type"""
        grouped = {}
        for clause in clauses:
            clause_type = clause.clause_type or "unknown"
            if clause_type not in grouped:
                grouped[clause_type] = []
            grouped[clause_type].append(clause)
        return grouped
    
    def _combine_chunks_to_text(self, chunks: List[DocumentChunk]) -> str:
        """Combine document chunks into full text"""
        if not chunks:
            return ""
        
        # Sort chunks by chunk number
        sorted_chunks = sorted(chunks, key=lambda x: x.chunk_no)
        return "\n".join(chunk.text for chunk in sorted_chunks)
    
    def _calculate_similarity_score(self, text_changes: List[TextChange]) -> float:
        """Calculate overall similarity score between documents"""
        if not text_changes:
            return 1.0
        
        # Simple calculation based on number of changes
        # In practice, this could be more sophisticated
        total_changes = len(text_changes)
        
        # Assume documents are similar if they have few changes
        if total_changes < 10:
            return 0.9
        elif total_changes < 50:
            return 0.7
        elif total_changes < 100:
            return 0.5
        else:
            return 0.3
    
    async def _assess_change_risks(self, clause_changes: List[ClauseChange], text_changes: List[TextChange]) -> Dict[str, Any]:
        """Assess the risk impact of document changes"""
        risk_assessment = {
            "overall_risk": "low",
            "high_risk_changes": [],
            "recommendations": [],
            "change_summary": {
                "clauses_added": 0,
                "clauses_removed": 0,
                "clauses_modified": 0,
                "text_changes": len(text_changes)
            }
        }
        
        high_risk_clause_types = {
            "liability", "indemnity", "termination", "payment", "intellectual_property",
            "confidentiality", "warranty", "limitation_of_liability"
        }
        
        high_risk_changes = []
        
        for change in clause_changes:
            if change.change_type == ChangeType.ADDED:
                risk_assessment["change_summary"]["clauses_added"] += 1
            elif change.change_type == ChangeType.REMOVED:
                risk_assessment["change_summary"]["clauses_removed"] += 1
                # Removed clauses are generally high risk
                if change.clause_type.lower() in high_risk_clause_types:
                    high_risk_changes.append({
                        "type": "clause_removed",
                        "clause_type": change.clause_type,
                        "risk": "high",
                        "description": f"Critical {change.clause_type} clause was removed"
                    })
            elif change.change_type == ChangeType.MODIFIED:
                risk_assessment["change_summary"]["clauses_modified"] += 1
                if change.clause_type.lower() in high_risk_clause_types:
                    high_risk_changes.append({
                        "type": "clause_modified",
                        "clause_type": change.clause_type,
                        "risk": "medium",
                        "description": f"Important {change.clause_type} clause was modified"
                    })
        
        risk_assessment["high_risk_changes"] = high_risk_changes
        
        # Determine overall risk
        if len(high_risk_changes) > 3:
            risk_assessment["overall_risk"] = "high"
        elif len(high_risk_changes) > 0:
            risk_assessment["overall_risk"] = "medium"
        
        # Generate recommendations
        recommendations = []
        if risk_assessment["change_summary"]["clauses_removed"] > 0:
            recommendations.append("Review removed clauses carefully to ensure no critical protections were lost")
        if risk_assessment["change_summary"]["clauses_modified"] > 2:
            recommendations.append("Have legal counsel review modified clauses for potential impact")
        if len(high_risk_changes) > 0:
            recommendations.append("Pay special attention to changes in liability, indemnity, and termination clauses")
        
        risk_assessment["recommendations"] = recommendations
        
        return risk_assessment
    
    def _assess_clause_risk_impact(self, clause_type: str, change_type: ChangeType) -> str:
        """Assess risk impact of a specific clause change"""
        high_risk_types = {"liability", "indemnity", "termination", "payment"}
        medium_risk_types = {"warranty", "confidentiality", "intellectual_property"}
        
        clause_type_lower = clause_type.lower()
        
        if clause_type_lower in high_risk_types:
            if change_type == ChangeType.REMOVED:
                return "high"
            else:
                return "medium"
        elif clause_type_lower in medium_risk_types:
            return "medium"
        else:
            return "low"
    
    def _generate_comparison_summary(
        self,
        text_changes: List[TextChange],
        clause_changes: List[ClauseChange],
        similarity_score: float
    ) -> str:
        """Generate a human-readable summary of the comparison"""
        added_changes = len([c for c in text_changes if c.change_type == ChangeType.ADDED])
        removed_changes = len([c for c in text_changes if c.change_type == ChangeType.REMOVED])
        
        clause_added = len([c for c in clause_changes if c.change_type == ChangeType.ADDED])
        clause_removed = len([c for c in clause_changes if c.change_type == ChangeType.REMOVED])
        clause_modified = len([c for c in clause_changes if c.change_type == ChangeType.MODIFIED])
        
        summary_parts = []
        
        # Overall similarity
        if similarity_score > 0.9:
            summary_parts.append("The documents are very similar with minimal changes.")
        elif similarity_score > 0.7:
            summary_parts.append("The documents have moderate differences.")
        else:
            summary_parts.append("The documents have significant differences.")
        
        # Text changes
        if added_changes > 0 or removed_changes > 0:
            summary_parts.append(f"Text changes: {added_changes} additions, {removed_changes} removals.")
        
        # Clause changes
        if clause_added > 0 or clause_removed > 0 or clause_modified > 0:
            clause_summary = f"Clause changes: {clause_added} added, {clause_removed} removed, {clause_modified} modified."
            summary_parts.append(clause_summary)
        
        return " ".join(summary_parts)
    
    async def _store_comparison_result(self, result: ComparisonResult, org_id: str, user_id: UUID):
        """Store comparison result in database"""
        comparison_data = {
            "org_id": UUID(org_id),
            "document_a_id": result.document_a_id,
            "document_b_id": result.document_b_id,
            "comparison_result": {
                "text_changes": [
                    {
                        "change_type": change.change_type.value,
                        "text": change.text,
                        "line_number": change.line_number,
                        "page_number": change.page_number,
                        "confidence": change.confidence
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
                "similarity_score": result.similarity_score
            },
            "risk_assessment": result.risk_assessment,
            "summary": result.summary,
            "created_by": user_id
        }
        
        await self.comparison_repo.create(comparison_data, org_id)
    
    def _parse_stored_comparison(self, stored_comparison) -> ComparisonResult:
        """Parse stored comparison back to ComparisonResult object"""
        comparison_data = stored_comparison.comparison_result
        
        text_changes = [
            TextChange(
                change_type=ChangeType(change["change_type"]),
                text=change["text"],
                line_number=change.get("line_number"),
                page_number=change.get("page_number"),
                confidence=change.get("confidence", 1.0)
            )
            for change in comparison_data.get("text_changes", [])
        ]
        
        clause_changes = [
            ClauseChange(
                change_type=ChangeType(change["change_type"]),
                clause_type=change["clause_type"],
                old_text=change.get("old_text"),
                new_text=change.get("new_text"),
                risk_impact=change.get("risk_impact", "low"),
                page_number=change.get("page_number")
            )
            for change in comparison_data.get("clause_changes", [])
        ]
        
        return ComparisonResult(
            document_a_id=stored_comparison.document_a_id,
            document_b_id=stored_comparison.document_b_id,
            text_changes=text_changes,
            clause_changes=clause_changes,
            similarity_score=comparison_data.get("similarity_score", 0.0),
            risk_assessment=stored_comparison.risk_assessment or {},
            summary=stored_comparison.summary or ""
        )
    
    async def get_comparison_history(self, org_id: str, limit: int = 10):
        """Get recent comparison history for organization"""
        return await self.comparison_repo.get_recent(org_id, limit)
    
    async def get_document_comparisons(self, document_id: UUID, org_id: str):
        """Get all comparisons involving a specific document"""
        return await self.comparison_repo.get_by_document(document_id, org_id)