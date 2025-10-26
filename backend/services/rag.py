"""
RAG (Retrieval-Augmented Generation) service for semantic search and AI-powered responses.

This service implements:
- Semantic search using pgvector similarity search
- Context window assembly with nearby chunks
- MMR (Maximal Marginal Relevance) reranking for diverse results
- Integration with Claude API for response generation
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from uuid import UUID
import asyncio
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from repositories.document_chunk import DocumentChunkRepository
from repositories.document import DocumentRepository
from services.embedding import EmbeddingService
from models.database import DocumentChunk, Document
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class SearchResult:
    """Container for search result with metadata."""
    chunk: DocumentChunk
    similarity_score: float
    document: Optional[Document] = None
    context_chunks: Optional[List[DocumentChunk]] = None


@dataclass
class Citation:
    """Container for citation information."""
    document_id: UUID
    document_title: str
    page: Optional[int]
    chunk_id: UUID
    text: str
    relevance_score: float


@dataclass
class RAGResponse:
    """Container for RAG query response."""
    answer: str
    citations: List[Citation]
    confidence: float
    model_used: str
    processing_time: float
    context_used: str


class SemanticSearchService:
    """Service for semantic search and retrieval operations."""
    
    def __init__(
        self,
        chunk_repository: DocumentChunkRepository,
        document_repository: DocumentRepository,
        embedding_service: EmbeddingService
    ):
        self.chunk_repository = chunk_repository
        self.document_repository = document_repository
        self.embedding_service = embedding_service
    
    async def search(
        self,
        query: str,
        org_id: str,
        document_ids: Optional[List[UUID]] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        include_context: bool = True,
        context_size: int = 2
    ) -> List[SearchResult]:
        """
        Perform semantic search across document chunks.
        
        Args:
            query: Search query text
            org_id: Organization ID for multi-tenant isolation
            document_ids: Optional list of document IDs to search within
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score threshold
            include_context: Whether to include nearby chunks for context
            context_size: Number of chunks before/after to include as context
            
        Returns:
            List of SearchResult objects ordered by relevance
        """
        logger.info(f"Performing semantic search for query: '{query[:100]}...'")
        
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_query_embedding(query)
        
        # Perform similarity search
        chunk_results = await self.chunk_repository.similarity_search(
            query_embedding=query_embedding,
            org_id=org_id,
            document_ids=document_ids,
            limit=limit * 2,  # Get more results for MMR reranking
            similarity_threshold=similarity_threshold
        )
        
        if not chunk_results:
            logger.info("No chunks found matching the query")
            return []
        
        logger.info(f"Found {len(chunk_results)} initial chunk matches")
        
        # Apply MMR reranking for diversity
        reranked_chunks = await self._apply_mmr_reranking(
            chunk_results, query_embedding, limit
        )
        
        # Build search results with context and document info
        search_results = []
        for chunk, similarity_score in reranked_chunks:
            # Get document information
            document = await self.document_repository.get_by_id(chunk.document_id, org_id)
            
            # Get context chunks if requested
            context_chunks = None
            if include_context:
                context_chunks = await self.chunk_repository.get_nearby_chunks(
                    chunk.id, org_id, context_size
                )
            
            result = SearchResult(
                chunk=chunk,
                similarity_score=similarity_score,
                document=document,
                context_chunks=context_chunks
            )
            search_results.append(result)
        
        logger.info(f"Returning {len(search_results)} search results")
        return search_results
    
    async def _apply_mmr_reranking(
        self,
        chunk_results: List[Tuple[DocumentChunk, float]],
        query_embedding: List[float],
        limit: int,
        lambda_param: float = 0.7
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Apply Maximal Marginal Relevance (MMR) reranking for diverse results.
        
        MMR balances relevance to the query with diversity among selected results.
        
        Args:
            chunk_results: List of (chunk, similarity_score) tuples
            query_embedding: Query embedding vector
            limit: Maximum number of results to return
            lambda_param: Balance parameter (0=diversity, 1=relevance)
            
        Returns:
            Reranked list of (chunk, similarity_score) tuples
        """
        if len(chunk_results) <= limit:
            return chunk_results
        
        logger.info(f"Applying MMR reranking to {len(chunk_results)} results")
        
        # Extract embeddings and convert to numpy arrays
        query_vec = np.array(query_embedding).reshape(1, -1)
        chunk_embeddings = []
        
        for chunk, _ in chunk_results:
            if chunk.embedding:
                chunk_embeddings.append(chunk.embedding)
            else:
                # If no embedding, use zero vector (shouldn't happen in practice)
                chunk_embeddings.append([0.0] * len(query_embedding))
        
        chunk_vecs = np.array(chunk_embeddings)
        
        # MMR algorithm
        selected_indices = []
        remaining_indices = list(range(len(chunk_results)))
        
        # Select first result (highest similarity)
        first_idx = 0  # Already sorted by similarity
        selected_indices.append(first_idx)
        remaining_indices.remove(first_idx)
        
        # Select remaining results using MMR
        while len(selected_indices) < limit and remaining_indices:
            mmr_scores = []
            
            for idx in remaining_indices:
                # Relevance score (similarity to query)
                relevance = cosine_similarity(
                    query_vec, 
                    chunk_vecs[idx].reshape(1, -1)
                )[0][0]
                
                # Diversity score (max similarity to already selected)
                if selected_indices:
                    selected_vecs = chunk_vecs[selected_indices]
                    similarities = cosine_similarity(
                        chunk_vecs[idx].reshape(1, -1),
                        selected_vecs
                    )[0]
                    max_similarity = np.max(similarities)
                else:
                    max_similarity = 0
                
                # MMR score
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity
                mmr_scores.append((idx, mmr_score))
            
            # Select chunk with highest MMR score
            best_idx, _ = max(mmr_scores, key=lambda x: x[1])
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)
        
        # Return reranked results
        reranked = [chunk_results[i] for i in selected_indices]
        logger.info(f"MMR reranking complete, selected {len(reranked)} diverse results")
        
        return reranked
    
    async def get_context_window(
        self,
        search_results: List[SearchResult],
        max_context_length: int = 4000
    ) -> str:
        """
        Assemble context window from search results with nearby chunks.
        
        Args:
            search_results: List of search results
            max_context_length: Maximum length of context in characters
            
        Returns:
            Assembled context string
        """
        context_parts = []
        current_length = 0
        
        for result in search_results:
            # Build context for this result
            chunks_to_include = []
            
            # Add context chunks if available
            if result.context_chunks:
                # Sort context chunks by chunk number
                sorted_context = sorted(result.context_chunks, key=lambda c: c.chunk_no)
                chunks_to_include.extend(sorted_context)
            else:
                # Just use the main chunk
                chunks_to_include.append(result.chunk)
            
            # Build context text for this document section
            document_title = result.document.title if result.document else "Unknown Document"
            section_text = f"\n--- From: {document_title} ---\n"
            
            for chunk in chunks_to_include:
                chunk_text = chunk.text.strip()
                page_info = f" (Page {chunk.page})" if chunk.page else ""
                section_text += f"{chunk_text}{page_info}\n"
            
            # Check if adding this section would exceed limit
            if current_length + len(section_text) > max_context_length:
                if current_length == 0:
                    # If this is the first section and it's too long, truncate it
                    remaining_space = max_context_length - 100  # Leave space for truncation notice
                    section_text = section_text[:remaining_space] + "\n[... truncated ...]"
                    context_parts.append(section_text)
                break
            
            context_parts.append(section_text)
            current_length += len(section_text)
        
        context = "\n".join(context_parts)
        logger.info(f"Assembled context window of {len(context)} characters from {len(context_parts)} sections")
        
        return context
    
    async def extract_citations(
        self,
        search_results: List[SearchResult],
        response_text: str
    ) -> List[Citation]:
        """
        Extract citations from search results that were likely used in the response.
        
        Args:
            search_results: List of search results used for context
            response_text: Generated response text
            
        Returns:
            List of Citation objects
        """
        citations = []
        
        for result in search_results:
            if not result.document:
                continue
            
            # Create citation
            citation = Citation(
                document_id=result.chunk.document_id,
                document_title=result.document.title,
                page=result.chunk.page,
                chunk_id=result.chunk.id,
                text=result.chunk.text[:200] + "..." if len(result.chunk.text) > 200 else result.chunk.text,
                relevance_score=result.similarity_score
            )
            citations.append(citation)
        
        # Sort citations by relevance score
        citations.sort(key=lambda c: c.relevance_score, reverse=True)
        
        logger.info(f"Extracted {len(citations)} citations")
        return citations


# Factory function for easy service creation
def create_semantic_search_service(
    chunk_repository: DocumentChunkRepository,
    document_repository: DocumentRepository,
    embedding_service: EmbeddingService
) -> SemanticSearchService:
    """Create and return a SemanticSearchService instance."""
    return SemanticSearchService(
        chunk_repository=chunk_repository,
        document_repository=document_repository,
        embedding_service=embedding_service
    )

class ClaudeAPIService:
    """Service for integrating with Anthropic Claude API for response generation."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Claude integration")
        
        # Import anthropic here to avoid import errors if not installed
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic package is required for Claude integration")
        
        # Model configuration based on plan
        self.model_config = {
            'free': 'claude-3-haiku-20240307',
            'pro': 'claude-3-sonnet-20240229', 
            'enterprise': 'claude-3-opus-20240229'
        }
        
        # Fallback model if primary fails
        self.fallback_model = 'claude-3-sonnet-20240229'
    
    def _get_model_for_plan(self, plan: str) -> str:
        """Get appropriate Claude model based on subscription plan."""
        return self.model_config.get(plan.lower(), self.fallback_model)
    
    async def generate_response(
        self,
        query: str,
        context: str,
        plan: str = 'pro',
        max_tokens: int = 1000,
        temperature: float = 0.1
    ) -> Tuple[str, str, float]:
        """
        Generate response using Claude API with structured prompting.
        
        Args:
            query: User's question
            context: Retrieved context from documents
            plan: Subscription plan (determines model)
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0.0-1.0)
            
        Returns:
            Tuple of (response_text, model_used, confidence_score)
        """
        primary_model = self._get_model_for_plan(plan)
        
        # Structured prompt for legal document analysis
        system_prompt = """You are an expert legal AI assistant specializing in contract analysis. Your role is to:

1. Provide accurate, precise answers based solely on the provided document context
2. Include specific citations with page numbers when available
3. Highlight potential risks, missing clauses, or important legal considerations
4. Use clear, professional language appropriate for legal professionals
5. If information is not in the provided context, clearly state this limitation

Always structure your responses with:
- Direct answer to the question
- Supporting evidence from the documents with citations
- Any relevant legal considerations or risks
- Confidence level in your analysis"""

        user_prompt = f"""Based on the following contract documents, please answer this question:

QUESTION: {query}

DOCUMENT CONTEXT:
{context}

Please provide a comprehensive answer with specific citations to page numbers where available. If the documents don't contain sufficient information to fully answer the question, please indicate what information is missing."""

        try:
            # Try primary model first
            response = await self._make_api_call(
                model=primary_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            confidence = self._calculate_confidence(response, context)
            return response, primary_model, confidence
            
        except Exception as e:
            logger.warning(f"Primary model {primary_model} failed: {e}")
            
            # Fallback to Sonnet if Opus fails
            if primary_model != self.fallback_model:
                try:
                    logger.info(f"Falling back to {self.fallback_model}")
                    response = await self._make_api_call(
                        model=self.fallback_model,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    
                    confidence = self._calculate_confidence(response, context)
                    return response, self.fallback_model, confidence
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback model also failed: {fallback_error}")
                    raise
            else:
                raise
    
    async def _make_api_call(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float
    ) -> str:
        """Make API call to Claude."""
        try:
            message = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )
            
            # Extract text content from response
            if message.content and len(message.content) > 0:
                return message.content[0].text
            else:
                raise ValueError("Empty response from Claude API")
                
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise
    
    def _calculate_confidence(self, response: str, context: str) -> float:
        """
        Calculate confidence score based on response characteristics.
        
        This is a heuristic approach - in production you might want more sophisticated
        confidence estimation.
        """
        confidence = 0.5  # Base confidence
        
        # Increase confidence if response contains citations
        if "page" in response.lower() or "section" in response.lower():
            confidence += 0.2
        
        # Increase confidence if response is detailed
        if len(response) > 200:
            confidence += 0.1
        
        # Decrease confidence if response indicates uncertainty
        uncertainty_phrases = [
            "not clear", "unclear", "insufficient information", 
            "cannot determine", "may be", "might be", "possibly"
        ]
        
        for phrase in uncertainty_phrases:
            if phrase in response.lower():
                confidence -= 0.1
                break
        
        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))


class RAGService:
    """Main RAG service that combines semantic search with AI response generation."""
    
    def __init__(
        self,
        search_service: SemanticSearchService,
        claude_service: ClaudeAPIService
    ):
        self.search_service = search_service
        self.claude_service = claude_service
    
    async def query(
        self,
        query: str,
        org_id: str,
        plan: str = 'pro',
        document_ids: Optional[List[UUID]] = None,
        max_results: int = 10,
        similarity_threshold: float = 0.7,
        max_context_length: int = 4000
    ) -> RAGResponse:
        """
        Perform complete RAG query: search + generation.
        
        Args:
            query: User's question
            org_id: Organization ID for multi-tenant isolation
            plan: Subscription plan (affects model selection)
            document_ids: Optional list of document IDs to search within
            max_results: Maximum search results to consider
            similarity_threshold: Minimum similarity score for search
            max_context_length: Maximum context length for generation
            
        Returns:
            RAGResponse with answer, citations, and metadata
        """
        import time
        start_time = time.time()
        
        logger.info(f"Starting RAG query for org {org_id}: '{query[:100]}...'")
        
        try:
            # Step 1: Semantic search
            search_results = await self.search_service.search(
                query=query,
                org_id=org_id,
                document_ids=document_ids,
                limit=max_results,
                similarity_threshold=similarity_threshold,
                include_context=True,
                context_size=2
            )
            
            if not search_results:
                return RAGResponse(
                    answer="I couldn't find any relevant information in the uploaded documents to answer your question. Please make sure the documents contain information related to your query, or try rephrasing your question.",
                    citations=[],
                    confidence=0.0,
                    model_used="none",
                    processing_time=time.time() - start_time,
                    context_used=""
                )
            
            # Step 2: Assemble context window
            context = await self.search_service.get_context_window(
                search_results, max_context_length
            )
            
            # Step 3: Generate response using Claude
            answer, model_used, confidence = await self.claude_service.generate_response(
                query=query,
                context=context,
                plan=plan
            )
            
            # Step 4: Extract citations
            citations = await self.search_service.extract_citations(
                search_results, answer
            )
            
            processing_time = time.time() - start_time
            
            logger.info(f"RAG query completed in {processing_time:.2f}s using {model_used}")
            
            return RAGResponse(
                answer=answer,
                citations=citations,
                confidence=confidence,
                model_used=model_used,
                processing_time=processing_time,
                context_used=context[:500] + "..." if len(context) > 500 else context
            )
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            processing_time = time.time() - start_time
            
            return RAGResponse(
                answer=f"I encountered an error while processing your question: {str(e)}. Please try again or contact support if the issue persists.",
                citations=[],
                confidence=0.0,
                model_used="error",
                processing_time=processing_time,
                context_used=""
            )
    
    async def get_subscription_plan(self, org_id: str) -> str:
        """
        Get subscription plan for organization.
        This is a placeholder - in practice you'd query the subscription service.
        """
        # TODO: Implement actual subscription lookup
        return 'pro'  # Default to pro plan


# Factory functions for easy service creation
def create_claude_service() -> ClaudeAPIService:
    """Create and return a ClaudeAPIService instance."""
    return ClaudeAPIService()


def create_rag_service(
    search_service: SemanticSearchService,
    claude_service: Optional[ClaudeAPIService] = None
) -> RAGService:
    """Create and return a RAGService instance."""
    if claude_service is None:
        claude_service = create_claude_service()
    
    return RAGService(
        search_service=search_service,
        claude_service=claude_service
    )