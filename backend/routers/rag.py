"""
RAG (Retrieval-Augmented Generation) query endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional, AsyncGenerator
from uuid import UUID
from datetime import datetime
import logging
import json
import asyncio
import time

from core.database import get_db
from core.rbac import (
    require_document_read,
    require_org_access,
    protected_route,
    Permission
)
from models.database import User
from repositories.document_chunk import DocumentChunkRepository
from repositories.document import DocumentRepository
from services.embedding import create_embedding_service
from services.rag import (
    create_semantic_search_service,
    create_claude_service,
    create_rag_service,
    RAGResponse,
    Citation
)
from services.cache import get_cache_service

logger = logging.getLogger(__name__)
router = APIRouter()


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="The question to ask about the documents")
    document_ids: Optional[List[str]] = Field(None, description="Optional list of document IDs to search within")
    max_results: int = Field(10, ge=1, le=50, description="Maximum number of search results to consider")
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score for search results")
    stream: bool = Field(False, description="Whether to stream the response")


class CitationResponse(BaseModel):
    document_id: str
    document_title: str
    page: Optional[int]
    chunk_id: str
    text: str
    relevance_score: float


class RAGQueryResponse(BaseModel):
    answer: str
    citations: List[CitationResponse]
    confidence: float
    model_used: str
    processing_time: float
    query_id: str
    timestamp: datetime


class RAGStreamChunk(BaseModel):
    type: str  # "start", "content", "citation", "end", "error"
    content: Optional[str] = None
    citation: Optional[CitationResponse] = None
    metadata: Optional[dict] = None


# Rate limiting is now handled by Redis cache service


@router.post("/query", response_model=RAGQueryResponse)
@protected_route(permissions=[Permission.DOCUMENT_READ])
async def rag_query(
    request: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_document_read),
    _: User = Depends(require_org_access)
):
    """
    Perform RAG query on uploaded documents.
    
    This endpoint searches through document chunks using semantic similarity
    and generates AI-powered responses using Claude.
    """
    try:
        # Get cache service and check rate limiting
        cache_service = await get_cache_service()
        is_allowed, remaining = await cache_service.check_rate_limit(
            str(current_user.id), limit=10, window_seconds=60, action="rag_query"
        )
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Please wait before making another request. Remaining: {remaining}"
            )
        
        logger.info(f"RAG query from user {current_user.id}: '{request.query[:100]}...'")
        
        # Convert document IDs to UUIDs if provided
        document_uuids = None
        if request.document_ids:
            try:
                document_uuids = [UUID(doc_id) for doc_id in request.document_ids]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid document ID format"
                )
        
        # Check cache first
        cached_response = await cache_service.get_rag_response(
            query=request.query,
            org_id=str(current_user.org_id),
            document_ids=request.document_ids,
            similarity_threshold=request.similarity_threshold
        )
        
        if cached_response:
            logger.info(f"Returning cached RAG response for user {current_user.id}")
            
            # Convert cached response to proper format
            citation_responses = [
                CitationResponse(**citation) for citation in cached_response.get("citations", [])
            ]
            
            return RAGQueryResponse(
                answer=cached_response["answer"],
                citations=citation_responses,
                confidence=cached_response["confidence"],
                model_used=cached_response["model_used"],
                processing_time=cached_response["processing_time"],
                query_id=cached_response.get("query_id", f"cached_{int(time.time())}"),
                timestamp=datetime.fromisoformat(cached_response["timestamp"])
            )
        
        # Initialize services
        chunk_repo = DocumentChunkRepository(db)
        doc_repo = DocumentRepository(db)
        embedding_service = create_embedding_service()
        search_service = create_semantic_search_service(chunk_repo, doc_repo, embedding_service)
        claude_service = create_claude_service()
        rag_service = create_rag_service(search_service, claude_service)
        
        # Get user's subscription plan (placeholder - implement actual lookup)
        plan = "pro"  # TODO: Get from subscription service
        
        # Perform RAG query
        rag_response = await rag_service.query(
            query=request.query,
            org_id=str(current_user.org_id),
            plan=plan,
            document_ids=document_uuids,
            max_results=request.max_results,
            similarity_threshold=request.similarity_threshold
        )
        
        # Convert citations to response format
        citation_responses = [
            CitationResponse(
                document_id=str(citation.document_id),
                document_title=citation.document_title,
                page=citation.page,
                chunk_id=str(citation.chunk_id),
                text=citation.text,
                relevance_score=citation.relevance_score
            )
            for citation in rag_response.citations
        ]
        
        # Generate query ID for tracking
        query_id = f"q_{int(time.time())}_{current_user.id}"
        
        response = RAGQueryResponse(
            answer=rag_response.answer,
            citations=citation_responses,
            confidence=rag_response.confidence,
            model_used=rag_response.model_used,
            processing_time=rag_response.processing_time,
            query_id=query_id,
            timestamp=datetime.utcnow()
        )
        
        # Cache the response for future queries
        await cache_service.set_rag_response(
            query=request.query,
            org_id=str(current_user.org_id),
            response_data=response.dict(),
            document_ids=request.document_ids,
            similarity_threshold=request.similarity_threshold,
            ttl_seconds=3600  # 1 hour cache
        )
        
        # Track usage
        await cache_service.increment_usage(
            str(current_user.id), "queries", 1, "daily"
        )
        
        logger.info(f"RAG query completed: {query_id} in {rag_response.processing_time:.2f}s")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in RAG query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}"
        )


@router.post("/query/stream")
@protected_route(permissions=[Permission.DOCUMENT_READ])
async def rag_query_stream(
    request: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_document_read),
    _: User = Depends(require_org_access)
):
    """
    Perform streaming RAG query on uploaded documents.
    
    This endpoint provides real-time streaming of the RAG response,
    sending chunks as they are generated.
    """
    try:
        # Get cache service and check rate limiting for streaming
        cache_service = await get_cache_service()
        is_allowed, remaining = await cache_service.check_rate_limit(
            str(current_user.id), limit=5, window_seconds=60, action="rag_stream"
        )
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for streaming queries. Remaining: {remaining}"
            )
        
        logger.info(f"Streaming RAG query from user {current_user.id}: '{request.query[:100]}...'")
        
        # Convert document IDs to UUIDs if provided
        document_uuids = None
        if request.document_ids:
            try:
                document_uuids = [UUID(doc_id) for doc_id in request.document_ids]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid document ID format"
                )
        
        async def generate_stream() -> AsyncGenerator[str, None]:
            """Generate streaming response."""
            try:
                # Send start event
                start_chunk = RAGStreamChunk(
                    type="start",
                    metadata={"query": request.query, "timestamp": datetime.utcnow().isoformat()}
                )
                yield f"data: {start_chunk.json()}\n\n"
                
                # Initialize services
                chunk_repo = DocumentChunkRepository(db)
                doc_repo = DocumentRepository(db)
                embedding_service = create_embedding_service()
                search_service = create_semantic_search_service(chunk_repo, doc_repo, embedding_service)
                claude_service = create_claude_service()
                rag_service = create_rag_service(search_service, claude_service)
                
                # Get user's subscription plan
                plan = "pro"  # TODO: Get from subscription service
                
                # Perform RAG query
                rag_response = await rag_service.query(
                    query=request.query,
                    org_id=str(current_user.org_id),
                    plan=plan,
                    document_ids=document_uuids,
                    max_results=request.max_results,
                    similarity_threshold=request.similarity_threshold
                )
                
                # Stream the answer in chunks
                answer_words = rag_response.answer.split()
                chunk_size = 5  # Words per chunk
                
                for i in range(0, len(answer_words), chunk_size):
                    chunk_words = answer_words[i:i + chunk_size]
                    content_chunk = RAGStreamChunk(
                        type="content",
                        content=" ".join(chunk_words) + " "
                    )
                    yield f"data: {content_chunk.json()}\n\n"
                    
                    # Small delay to simulate streaming
                    await asyncio.sleep(0.1)
                
                # Send citations
                for citation in rag_response.citations:
                    citation_response = CitationResponse(
                        document_id=str(citation.document_id),
                        document_title=citation.document_title,
                        page=citation.page,
                        chunk_id=str(citation.chunk_id),
                        text=citation.text,
                        relevance_score=citation.relevance_score
                    )
                    
                    citation_chunk = RAGStreamChunk(
                        type="citation",
                        citation=citation_response
                    )
                    yield f"data: {citation_chunk.json()}\n\n"
                
                # Send end event
                end_chunk = RAGStreamChunk(
                    type="end",
                    metadata={
                        "confidence": rag_response.confidence,
                        "model_used": rag_response.model_used,
                        "processing_time": rag_response.processing_time,
                        "citations_count": len(rag_response.citations)
                    }
                )
                yield f"data: {end_chunk.json()}\n\n"
                
            except Exception as e:
                logger.error(f"Error in streaming RAG query: {str(e)}")
                error_chunk = RAGStreamChunk(
                    type="error",
                    content=f"Error processing query: {str(e)}"
                )
                yield f"data: {error_chunk.json()}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up streaming RAG query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup streaming query: {str(e)}"
        )


@router.get("/models")
@protected_route(permissions=[Permission.DOCUMENT_READ])
async def get_available_models(
    current_user: User = Depends(require_document_read),
    _: User = Depends(require_org_access)
):
    """Get available AI models based on subscription plan."""
    try:
        # TODO: Get actual subscription plan
        plan = "pro"
        
        model_config = {
            'free': {
                'models': ['claude-3-haiku-20240307'],
                'features': ['Basic Q&A', 'Limited queries per day']
            },
            'pro': {
                'models': ['claude-3-sonnet-20240229'],
                'features': ['Advanced Q&A', 'Unlimited queries', 'Citation highlighting']
            },
            'enterprise': {
                'models': ['claude-3-opus-20240229', 'claude-3-sonnet-20240229'],
                'features': ['Premium Q&A', 'Unlimited queries', 'Priority processing', 'Custom models']
            }
        }
        
        return {
            "plan": plan,
            "available_models": model_config.get(plan, model_config['free'])
        }
        
    except Exception as e:
        logger.error(f"Error getting available models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available models: {str(e)}"
        )


@router.get("/usage")
@protected_route(permissions=[Permission.DOCUMENT_READ])
async def get_query_usage(
    current_user: User = Depends(require_document_read),
    _: User = Depends(require_org_access)
):
    """Get RAG query usage statistics for the organization."""
    try:
        # TODO: Implement actual usage tracking
        # This would query the usage_records table
        
        return {
            "org_id": str(current_user.org_id),
            "current_period": {
                "queries_used": 45,
                "queries_limit": 1000,
                "tokens_used": 125000,
                "tokens_limit": 500000
            },
            "rate_limits": {
                "queries_per_minute": 10,
                "streaming_queries_per_minute": 5
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting query usage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get query usage: {str(e)}"
        )