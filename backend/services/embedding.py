"""
Embedding generation service for document processing.

Supports configurable embedding providers:
- OpenAI text-embedding-3-large
- AWS Bedrock (Titan Embeddings)
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio

import openai
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class TextChunk:
    """Container for text chunk with metadata."""
    text: str
    chunk_no: int
    page: Optional[int] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EmbeddingResult:
    """Container for embedding result."""
    embedding: List[float]
    chunk: TextChunk
    model: str
    dimensions: int


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass
    
    @abstractmethod
    def get_dimensions(self) -> int:
        """Get the dimension size of embeddings."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider using text-embedding-3-large."""
    
    def __init__(self, api_key: str):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = "text-embedding-3-large"
        self.dimensions = 3072  # text-embedding-3-large dimensions
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        try:
            # OpenAI allows batch processing up to 2048 texts
            batch_size = 100  # Conservative batch size
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    encoding_format="float"
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)
                
                # Small delay to respect rate limits
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise
    
    def get_dimensions(self) -> int:
        return self.dimensions
    
    def get_model_name(self) -> str:
        return self.model


class BedrockEmbeddingProvider(EmbeddingProvider):
    """AWS Bedrock embedding provider using Titan Embeddings."""
    
    def __init__(self, region_name: str = "us-east-1"):
        self.client = boto3.client('bedrock-runtime', region_name=region_name)
        self.model_id = "amazon.titan-embed-text-v1"
        self.dimensions = 1536  # Titan embeddings dimensions
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using AWS Bedrock."""
        try:
            import json
            
            embeddings = []
            
            # Bedrock requires individual calls for each text
            for text in texts:
                body = json.dumps({
                    "inputText": text
                })
                
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=body,
                    contentType="application/json",
                    accept="application/json"
                )
                
                response_body = json.loads(response['body'].read())
                embedding = response_body.get('embedding', [])
                embeddings.append(embedding)
                
                # Small delay to respect rate limits
                await asyncio.sleep(0.05)
            
            return embeddings
            
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Bedrock embedding generation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Bedrock embedding generation: {e}")
            raise
    
    def get_dimensions(self) -> int:
        return self.dimensions
    
    def get_model_name(self) -> str:
        return self.model_id


class TextChunkingService:
    """Service for chunking text using LangChain RecursiveCharacterTextSplitter."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None
    ):
        """
        Initialize text chunking service.
        
        Args:
            chunk_size: Maximum size of each chunk
            chunk_overlap: Number of characters to overlap between chunks
            separators: Custom separators for splitting
        """
        if separators is None:
            # Default separators optimized for legal documents
            separators = [
                "\n\n",  # Paragraph breaks
                "\n",    # Line breaks
                ". ",    # Sentence endings
                ", ",    # Clause separators
                " ",     # Word boundaries
                ""       # Character level
            ]
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            length_function=len,
            is_separator_regex=False
        )
    
    def chunk_text(
        self, 
        text: str, 
        pages: List[str], 
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[TextChunk]:
        """
        Chunk text into smaller pieces with metadata.
        
        Args:
            text: Full text to chunk
            pages: List of page texts for page number mapping
            metadata: Additional metadata to include
            
        Returns:
            List of TextChunk objects
        """
        # Create LangChain documents
        documents = [Document(page_content=text, metadata=metadata or {})]
        
        # Split the documents
        split_docs = self.text_splitter.split_documents(documents)
        
        chunks = []
        for i, doc in enumerate(split_docs):
            # Estimate page number for this chunk
            page_num = self._estimate_page_number(doc.page_content, text, pages)
            
            # Find character positions
            start_char = text.find(doc.page_content)
            end_char = start_char + len(doc.page_content) if start_char != -1 else None
            
            chunk = TextChunk(
                text=doc.page_content,
                chunk_no=i,
                page=page_num,
                start_char=start_char,
                end_char=end_char,
                metadata=doc.metadata
            )
            chunks.append(chunk)
        
        return chunks
    
    def _estimate_page_number(self, chunk_text: str, full_text: str, pages: List[str]) -> Optional[int]:
        """Estimate which page a chunk belongs to."""
        if not pages:
            return None
        
        # Find the chunk in the full text
        chunk_start = full_text.find(chunk_text)
        if chunk_start == -1:
            return None
        
        # Calculate cumulative character positions for each page
        current_pos = 0
        for i, page in enumerate(pages):
            current_pos += len(page)
            if chunk_start < current_pos:
                return i + 1
        
        return len(pages)


class EmbeddingService:
    """Main service for generating embeddings with configurable providers."""
    
    def __init__(self):
        self.provider = self._create_provider()
        self.chunking_service = TextChunkingService()
    
    def _create_provider(self) -> EmbeddingProvider:
        """Create embedding provider based on configuration."""
        provider_type = getattr(settings, 'EMBEDDING_PROVIDER', 'openai').lower()
        
        if provider_type == 'openai':
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
            return OpenAIEmbeddingProvider(api_key)
        
        elif provider_type == 'bedrock':
            region = getattr(settings, 'AWS_REGION', 'us-east-1')
            return BedrockEmbeddingProvider(region)
        
        else:
            raise ValueError(f"Unsupported embedding provider: {provider_type}")
    
    async def process_document(
        self, 
        text: str, 
        pages: List[str], 
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[EmbeddingResult]:
        """
        Process a document by chunking and generating embeddings.
        
        Args:
            text: Full document text
            pages: List of page texts
            metadata: Document metadata
            
        Returns:
            List of EmbeddingResult objects
        """
        logger.info(f"Processing document with {len(text)} characters into chunks")
        
        # Chunk the text
        chunks = self.chunking_service.chunk_text(text, pages, metadata)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Extract text from chunks for embedding
        chunk_texts = [chunk.text for chunk in chunks]
        
        # Generate embeddings
        logger.info(f"Generating embeddings using {self.provider.get_model_name()}")
        embeddings = await self.provider.generate_embeddings(chunk_texts)
        
        # Combine chunks with embeddings
        results = []
        for chunk, embedding in zip(chunks, embeddings):
            result = EmbeddingResult(
                embedding=embedding,
                chunk=chunk,
                model=self.provider.get_model_name(),
                dimensions=self.provider.get_dimensions()
            )
            results.append(result)
        
        logger.info(f"Successfully generated {len(results)} embeddings")
        return results
    
    async def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for a search query."""
        embeddings = await self.provider.generate_embeddings([query])
        return embeddings[0]
    
    def get_embedding_dimensions(self) -> int:
        """Get the dimension size of embeddings."""
        return self.provider.get_dimensions()
    
    def get_model_name(self) -> str:
        """Get the current model name."""
        return self.provider.get_model_name()


# Factory function for easy service creation
def create_embedding_service() -> EmbeddingService:
    """Create and return an EmbeddingService instance."""
    return EmbeddingService()