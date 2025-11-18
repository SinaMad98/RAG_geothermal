"""Preprocessing Agent: Text → Chunks with multi-strategy approach."""

import logging
from typing import List, Dict, Any
import re

logger = logging.getLogger(__name__)

class PreprocessingAgent:
    """
    Handles text preprocessing and multi-strategy chunking.
    
    Strategies:
    1. factual_qa: Small chunks (800 words) for precise Q&A
    2. technical_extraction: Large chunks (2500 words) to keep tables intact
    3. summary: Medium chunks (1500 words) for context
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PreprocessingAgent.
        
        Args:
            config: Configuration dictionary with chunking settings
        """
        self.config = config
        self.chunking_config = config.get('chunking', {})
        logger.info("PreprocessingAgent initialized")
    
    def chunk_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Chunk documents using multiple strategies.
        
        Args:
            documents: List of document dictionaries from IngestionAgent
            
        Returns:
            Dictionary with strategy names as keys:
            {
                'factual_qa': [chunks...],
                'technical_extraction': [chunks...],
                'summary': [chunks...]
            }
        """
        all_chunks = {
            'factual_qa': [],
            'technical_extraction': [],
            'summary': []
        }
        
        for doc in documents:
            content = doc['content']
            metadata = doc['metadata']
            well_names = doc.get('wells', [])
            
            # Apply each chunking strategy
            for strategy in ['factual_qa', 'technical_extraction', 'summary']:
                strategy_config = self.chunking_config.get(strategy, {})
                chunk_size = strategy_config.get('chunk_size', 1000)
                chunk_overlap = strategy_config.get('chunk_overlap', 200)
                
                chunks = self._chunk_text(
                    content, 
                    chunk_size, 
                    chunk_overlap,
                    metadata,
                    well_names,
                    strategy
                )
                
                all_chunks[strategy].extend(chunks)
                logger.info(f"✓ Strategy '{strategy}': {len(chunks)} chunks created")
        
        total = sum(len(chunks) for chunks in all_chunks.values())
        logger.info(f"✓ Total chunks across all strategies: {total}")
        
        return all_chunks
    
    def _chunk_text(self, text: str, chunk_size: int, chunk_overlap: int,
                   metadata: Dict[str, Any], well_names: List[str], 
                   strategy: str) -> List[Dict[str, Any]]:
        """
        Chunk text with specified size and overlap.
        
        Args:
            text: Full text to chunk
            chunk_size: Target chunk size in words
            chunk_overlap: Overlap between chunks in words
            metadata: Document metadata
            well_names: List of well names in document
            strategy: Chunking strategy name
            
        Returns:
            List of chunk dictionaries
        """
        # Split into words (simple word-based chunking)
        words = text.split()
        
        if len(words) == 0:
            return []
        
        chunks = []
        start_idx = 0
        chunk_id = 0
        
        while start_idx < len(words):
            # Get chunk
            end_idx = min(start_idx + chunk_size, len(words))
            chunk_words = words[start_idx:end_idx]
            chunk_text = ' '.join(chunk_words)
            
            # Detect which page(s) this chunk is from
            page_num = self._detect_page_number(chunk_text)
            
            # Create chunk metadata
            chunk_data = {
                'content': chunk_text,
                'metadata': {
                    'source': metadata.get('source', ''),
                    'filename': metadata.get('filename', ''),
                    'page': page_num,
                    'wells': well_names,
                    'strategy': strategy,
                    'chunk_id': chunk_id,
                    'word_count': len(chunk_words)
                }
            }
            
            chunks.append(chunk_data)
            chunk_id += 1
            
            # Move start position (with overlap)
            if end_idx >= len(words):
                break
            start_idx += (chunk_size - chunk_overlap)
        
        return chunks
    
    def _detect_page_number(self, text: str) -> int:
        """
        Detect page number from chunk text.
        
        Args:
            text: Chunk text
            
        Returns:
            Page number (1-indexed) or 0 if not found
        """
        # Look for "--- Page N ---" markers
        match = re.search(r'--- Page (\d+) ---', text)
        if match:
            return int(match.group(1))
        
        return 0
    
    def get_chunks_by_strategy(self, all_chunks: Dict[str, List[Dict[str, Any]]], 
                               strategy: str) -> List[Dict[str, Any]]:
        """
        Get chunks for a specific strategy.
        
        Args:
            all_chunks: Dictionary of all chunks by strategy
            strategy: Strategy name to retrieve
            
        Returns:
            List of chunks for that strategy
        """
        return all_chunks.get(strategy, [])
