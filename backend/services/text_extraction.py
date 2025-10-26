"""
Text extraction service for document processing.

Handles text extraction from various document formats using:
- PyPDF2 for standard PDFs
- Apache Tika as fallback
- AWS Textract for scanned documents
"""

import io
import logging
import mimetypes
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

import boto3
import PyPDF2
from botocore.exceptions import ClientError, BotoCoreError
from tika import parser as tika_parser

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ExtractedText:
    """Container for extracted text and metadata."""
    text: str
    page_count: int
    pages: List[str]  # Text per page
    metadata: Dict
    extraction_method: str
    confidence: Optional[float] = None


@dataclass
class ClauseCandidate:
    """Identified clause candidate from text analysis."""
    text: str
    clause_type: str
    page: int
    confidence: float
    start_pos: int
    end_pos: int


class TextExtractionService:
    """Service for extracting text from documents."""
    
    def __init__(self):
        self.textract_client = None
        if settings.AWS_ACCESS_KEY_ID:
            self.textract_client = boto3.client(
                'textract',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
    
    async def extract_text(self, file_content: bytes, file_type: str, filename: str) -> ExtractedText:
        """
        Extract text from document using appropriate method.
        
        Args:
            file_content: Raw file bytes
            file_type: MIME type of the file
            filename: Original filename
            
        Returns:
            ExtractedText object with extracted content
        """
        logger.info(f"Starting text extraction for {filename} (type: {file_type})")
        
        try:
            # Try PyPDF first for PDF files
            if file_type == 'application/pdf':
                try:
                    result = await self._extract_with_pypdf(file_content, filename)
                    if result and result.text.strip():
                        logger.info(f"Successfully extracted text using PyPDF for {filename}")
                        return result
                except Exception as e:
                    logger.warning(f"PyPDF extraction failed for {filename}: {e}")
            
            # Try Tika as fallback
            try:
                result = await self._extract_with_tika(file_content, filename)
                if result and result.text.strip():
                    logger.info(f"Successfully extracted text using Tika for {filename}")
                    return result
            except Exception as e:
                logger.warning(f"Tika extraction failed for {filename}: {e}")
            
            # Use Textract for scanned documents or as last resort
            if self.textract_client and file_type == 'application/pdf':
                try:
                    result = await self._extract_with_textract(file_content, filename)
                    if result:
                        logger.info(f"Successfully extracted text using Textract for {filename}")
                        return result
                except Exception as e:
                    logger.error(f"Textract extraction failed for {filename}: {e}")
            
            # If all methods fail, return empty result
            logger.error(f"All text extraction methods failed for {filename}")
            return ExtractedText(
                text="",
                page_count=0,
                pages=[],
                metadata={"filename": filename, "error": "Text extraction failed"},
                extraction_method="none"
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during text extraction for {filename}: {e}")
            raise
    
    async def _extract_with_pypdf(self, file_content: bytes, filename: str) -> Optional[ExtractedText]:
        """Extract text using PyPDF2."""
        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            if pdf_reader.is_encrypted:
                logger.warning(f"PDF {filename} is encrypted, cannot extract with PyPDF")
                return None
            
            pages = []
            full_text = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    pages.append(page_text)
                    full_text.append(page_text)
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num} from {filename}: {e}")
                    pages.append("")
            
            text = "\n\n".join(full_text)
            
            # Get metadata
            metadata = {
                "filename": filename,
                "creator": getattr(pdf_reader.metadata, 'creator', None) if pdf_reader.metadata else None,
                "producer": getattr(pdf_reader.metadata, 'producer', None) if pdf_reader.metadata else None,
                "subject": getattr(pdf_reader.metadata, 'subject', None) if pdf_reader.metadata else None,
                "title": getattr(pdf_reader.metadata, 'title', None) if pdf_reader.metadata else None,
            }
            
            return ExtractedText(
                text=text,
                page_count=len(pdf_reader.pages),
                pages=pages,
                metadata=metadata,
                extraction_method="pypdf"
            )
            
        except Exception as e:
            logger.error(f"PyPDF extraction error for {filename}: {e}")
            return None
    
    async def _extract_with_tika(self, file_content: bytes, filename: str) -> Optional[ExtractedText]:
        """Extract text using Apache Tika."""
        try:
            # Parse with Tika
            parsed = tika_parser.from_buffer(file_content)
            
            if not parsed or 'content' not in parsed:
                logger.warning(f"Tika returned no content for {filename}")
                return None
            
            text = parsed['content'] or ""
            metadata = parsed.get('metadata', {})
            metadata['filename'] = filename
            
            # For PDFs, try to estimate page count from metadata
            page_count = 1
            if 'xmpTPg:NPages' in metadata:
                try:
                    page_count = int(metadata['xmpTPg:NPages'])
                except (ValueError, TypeError):
                    pass
            elif 'meta:page-count' in metadata:
                try:
                    page_count = int(metadata['meta:page-count'])
                except (ValueError, TypeError):
                    pass
            
            # Split text into approximate pages (rough estimation)
            pages = self._split_text_into_pages(text, page_count)
            
            return ExtractedText(
                text=text,
                page_count=page_count,
                pages=pages,
                metadata=metadata,
                extraction_method="tika"
            )
            
        except Exception as e:
            logger.error(f"Tika extraction error for {filename}: {e}")
            return None
    
    async def _extract_with_textract(self, file_content: bytes, filename: str) -> Optional[ExtractedText]:
        """Extract text using AWS Textract."""
        try:
            if len(file_content) > 10 * 1024 * 1024:  # 10MB limit for synchronous calls
                logger.warning(f"File {filename} too large for Textract synchronous processing")
                return None
            
            response = self.textract_client.detect_document_text(
                Document={'Bytes': file_content}
            )
            
            # Extract text blocks
            text_blocks = []
            pages = {}
            
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    page_num = block.get('Page', 1)
                    if page_num not in pages:
                        pages[page_num] = []
                    pages[page_num].append(block['Text'])
                    text_blocks.append(block['Text'])
            
            # Combine all text
            full_text = '\n'.join(text_blocks)
            
            # Create page list
            page_list = []
            for page_num in sorted(pages.keys()):
                page_list.append('\n'.join(pages[page_num]))
            
            # Calculate average confidence
            confidences = [
                block.get('Confidence', 0) 
                for block in response.get('Blocks', []) 
                if 'Confidence' in block
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else None
            
            metadata = {
                "filename": filename,
                "textract_job_id": response.get('JobId'),
                "document_metadata": response.get('DocumentMetadata', {}),
            }
            
            return ExtractedText(
                text=full_text,
                page_count=len(page_list),
                pages=page_list,
                metadata=metadata,
                extraction_method="textract",
                confidence=avg_confidence
            )
            
        except (ClientError, BotoCoreError) as e:
            logger.error(f"AWS Textract error for {filename}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected Textract error for {filename}: {e}")
            return None
    
    def _split_text_into_pages(self, text: str, estimated_pages: int) -> List[str]:
        """Split text into approximate pages."""
        if estimated_pages <= 1:
            return [text]
        
        # Simple heuristic: split by length
        text_length = len(text)
        chars_per_page = text_length // estimated_pages
        
        pages = []
        start = 0
        
        for i in range(estimated_pages):
            if i == estimated_pages - 1:  # Last page gets remainder
                pages.append(text[start:])
            else:
                end = start + chars_per_page
                # Try to break at a sentence or paragraph
                break_point = text.rfind('.', start, end + 100)
                if break_point == -1 or break_point < start:
                    break_point = end
                pages.append(text[start:break_point])
                start = break_point
        
        return pages
    
    def identify_clauses(self, extracted_text: ExtractedText) -> List[ClauseCandidate]:
        """
        Identify potential clauses in extracted text.
        
        This is a basic implementation using pattern matching.
        In production, this could be enhanced with ML models.
        """
        clause_patterns = {
            'indemnity': [
                r'indemnif\w+',
                r'hold\s+harmless',
                r'defend\s+and\s+hold',
                r'liability\s+for\s+damages'
            ],
            'limitation_of_liability': [
                r'limitation\s+of\s+liability',
                r'limit\s+of\s+liability',
                r'liability\s+cap',
                r'maximum\s+liability'
            ],
            'termination': [
                r'terminat\w+',
                r'end\s+this\s+agreement',
                r'expire\w+',
                r'breach\s+of\s+contract'
            ],
            'confidentiality': [
                r'confidential\w+',
                r'non.disclosure',
                r'proprietary\s+information',
                r'trade\s+secret'
            ],
            'governing_law': [
                r'governing\s+law',
                r'jurisdiction',
                r'laws\s+of\s+\w+',
                r'courts\s+of\s+\w+'
            ]
        }
        
        import re
        
        clauses = []
        text = extracted_text.text.lower()
        
        for clause_type, patterns in clause_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Find the sentence containing this match
                    start = max(0, text.rfind('.', 0, match.start()) + 1)
                    end = text.find('.', match.end())
                    if end == -1:
                        end = len(text)
                    
                    clause_text = extracted_text.text[start:end].strip()
                    
                    # Estimate page number
                    page_num = self._estimate_page_number(
                        match.start(), 
                        extracted_text.pages
                    )
                    
                    clauses.append(ClauseCandidate(
                        text=clause_text,
                        clause_type=clause_type,
                        page=page_num,
                        confidence=0.7,  # Basic pattern matching confidence
                        start_pos=start,
                        end_pos=end
                    ))
        
        return clauses
    
    def _estimate_page_number(self, char_position: int, pages: List[str]) -> int:
        """Estimate which page a character position falls on."""
        current_pos = 0
        for i, page in enumerate(pages):
            current_pos += len(page)
            if char_position <= current_pos:
                return i + 1
        return len(pages)