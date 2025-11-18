"""Ingestion Agent: PDF → Text + Metadata."""

import fitz  # PyMuPDF
import logging
from typing import List, Dict, Any
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.extraction_patterns import extract_well_names

logger = logging.getLogger(__name__)

class IngestionAgent:
    """
    Handles PDF ingestion and extracts text with metadata.
    
    Responsibilities:
    - Extract text from PDF pages
    - Preserve page numbers for citation
    - Extract well names using regex patterns
    - Generate document metadata
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize IngestionAgent.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        logger.info("IngestionAgent initialized")
    
    def process(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Process PDF files and extract text with metadata.
        
        Args:
            file_paths: List of paths to PDF files
            
        Returns:
            List of documents with structure:
            [
                {
                    'content': 'full text...',
                    'pages': 27,
                    'wells': ['ADK-GT-01'],
                    'metadata': {
                        'filename': 'ADK-GT-01.pdf',
                        'source': '/path/to/file.pdf',
                        'page_contents': {1: 'page 1 text...', 2: 'page 2 text...'}
                    }
                },
                ...
            ]
        """
        processed_docs = []
        
        for file_path in file_paths:
            try:
                doc_data = self._process_single_pdf(file_path)
                processed_docs.append(doc_data)
                logger.info(f"✓ Processed: {file_path} ({doc_data['pages']} pages, "
                          f"{len(doc_data['wells'])} wells found)")
            except Exception as e:
                logger.error(f"✗ Failed to process {file_path}: {str(e)}")
                continue
        
        return processed_docs
    
    def _process_single_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Process a single PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Document dictionary with text and metadata
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        # Open PDF with PyMuPDF
        doc = fitz.open(str(file_path))
        
        # Extract text from each page
        page_contents = {}
        full_text_parts = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            
            page_contents[page_num + 1] = page_text  # 1-indexed pages
            full_text_parts.append(f"\n--- Page {page_num + 1} ---\n{page_text}")
        
        full_text = "\n".join(full_text_parts)
        
        # Extract well names from full text
        well_names = extract_well_names(full_text)
        
        # Create document data structure
        doc_data = {
            'content': full_text,
            'pages': len(doc),
            'wells': well_names,
            'metadata': {
                'filename': file_path.name,
                'source': str(file_path.absolute()),
                'page_contents': page_contents
            }
        }
        
        doc.close()
        
        return doc_data
    
    def get_page_text(self, doc_data: Dict[str, Any], page_num: int) -> str:
        """
        Get text from a specific page.
        
        Args:
            doc_data: Document data from process()
            page_num: Page number (1-indexed)
            
        Returns:
            Text from the specified page
        """
        page_contents = doc_data.get('metadata', {}).get('page_contents', {})
        return page_contents.get(page_num, '')
