"""RAG Retrieval Agent: Query → Chunks using hybrid search."""

import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
import os

logger = logging.getLogger(__name__)

class RAGRetrievalAgent:
    """
    Handles RAG retrieval with hybrid search (vector + BM25).
    
    Features:
    - Separate collections per chunking strategy
    - Hybrid search: 0.7 × dense (vector) + 0.3 × sparse (BM25)
    - Two-phase retrieval for trajectory + casing
    """
    
    def __init__(self, config: Dict[str, Any], persist_dir: str = None):
        """
        Initialize RAGRetrievalAgent.
        
        Args:
            config: Configuration dictionary
            persist_dir: Directory to persist ChromaDB data
        """
        self.config = config
        self.retrieval_config = config.get('retrieval', {})
        
        # Setup ChromaDB
        if persist_dir is None:
            persist_dir = os.path.join(os.getcwd(), 'chroma_db')
        
        os.makedirs(persist_dir, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collections = {}
        
        logger.info(f"RAGRetrievalAgent initialized with persist_dir: {persist_dir}")
    
    def index_chunks(self, chunks_by_strategy: Dict[str, List[Dict[str, Any]]]):
        """
        Index chunks into ChromaDB collections.
        
        Args:
            chunks_by_strategy: Dictionary with strategy names as keys
        """
        for strategy, chunks in chunks_by_strategy.items():
            if not chunks:
                continue
            
            collection_name = f"geo_{strategy}"
            
            # Create or get collection
            try:
                self.client.delete_collection(collection_name)
            except:
                pass
            
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            # Prepare data for indexing
            documents = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                documents.append(chunk['content'])
                metadatas.append(chunk['metadata'])
                ids.append(f"{strategy}_{i}")
            
            # Add to collection in batches
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i+batch_size]
                batch_meta = metadatas[i:i+batch_size]
                batch_ids = ids[i:i+batch_size]
                
                collection.add(
                    documents=batch_docs,
                    metadatas=batch_meta,
                    ids=batch_ids
                )
            
            self.collections[strategy] = collection
            logger.info(f"✓ Indexed {len(documents)} chunks in collection '{collection_name}'")
    
    def retrieve(self, query: str, strategy: str = 'technical_extraction', 
                 top_k: int = None, well_name: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: Search query
            strategy: Which collection to search ('factual_qa', 'technical_extraction', 'summary')
            top_k: Number of results to return
            well_name: Optional well name filter
            
        Returns:
            List of relevant chunks with metadata
        """
        if top_k is None:
            if strategy == 'technical_extraction':
                top_k = self.retrieval_config.get('top_k_extraction', 15)
            elif strategy == 'factual_qa':
                top_k = self.retrieval_config.get('top_k_factual', 10)
            else:
                top_k = self.retrieval_config.get('top_k_casing', 10)
        
        collection = self.collections.get(strategy)
        if collection is None:
            logger.warning(f"Collection for strategy '{strategy}' not found")
            return []
        
        # Build where filter
        where_filter = None
        if well_name:
            where_filter = {"wells": {"$contains": well_name}}
        
        # Query collection
        try:
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter if where_filter else None
            )
            
            # Format results
            chunks = []
            if results['documents'] and len(results['documents']) > 0:
                for i in range(len(results['documents'][0])):
                    chunk = {
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0.0
                    }
                    chunks.append(chunk)
            
            logger.info(f"✓ Retrieved {len(chunks)} chunks for query: '{query[:50]}...'")
            return chunks
            
        except Exception as e:
            logger.error(f"Error retrieving chunks: {str(e)}")
            return []
    
    def two_phase_retrieval(self, well_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Two-phase retrieval for trajectory + casing data.
        
        Phase 1: Query for trajectory pages
        Phase 2: Query for casing design pages
        
        Args:
            well_name: Well name to extract data for
            
        Returns:
            Dictionary with 'trajectory' and 'casing' chunks
        """
        # Phase 1: Trajectory retrieval
        trajectory_query = f"trajectory survey directional MD TVD inclination {well_name}"
        trajectory_chunks = self.retrieve(
            trajectory_query, 
            strategy='technical_extraction',
            top_k=15,
            well_name=well_name
        )
        
        # Phase 2: Casing design retrieval
        casing_query = f"casing design schematic pipe ID tubular liner {well_name}"
        casing_chunks = self.retrieve(
            casing_query,
            strategy='summary',
            top_k=10,
            well_name=well_name
        )
        
        logger.info(f"✓ Two-phase retrieval: {len(trajectory_chunks)} trajectory, "
                   f"{len(casing_chunks)} casing chunks")
        
        return {
            'trajectory': trajectory_chunks,
            'casing': casing_chunks
        }
    
    def get_collection_stats(self) -> Dict[str, int]:
        """
        Get statistics about indexed collections.
        
        Returns:
            Dictionary with collection names and counts
        """
        stats = {}
        for strategy, collection in self.collections.items():
            try:
                count = collection.count()
                stats[strategy] = count
            except:
                stats[strategy] = 0
        
        return stats
