"""Main orchestrator for RAG Geothermal Wells system."""

import logging
import sys
from typing import List, Dict, Any
from pathlib import Path

from agents import (
    IngestionAgent,
    PreprocessingAgent,
    RAGRetrievalAgent,
    ParameterExtractionAgent,
    ValidationAgent
)
from utils import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RAGGeothermalSystem:
    """
    Main orchestrator for RAG Geothermal Wells system.
    
    Coordinates all agents to:
    1. Ingest PDF documents
    2. Preprocess and chunk text
    3. Index chunks for retrieval
    4. Extract well parameters
    5. Validate and analyze
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the RAG system.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = load_config(config_path)
        
        # Initialize agents
        logger.info("Initializing RAG Geothermal System...")
        self.ingestion_agent = IngestionAgent(self.config)
        self.preprocessing_agent = PreprocessingAgent(self.config)
        self.rag_agent = RAGRetrievalAgent(self.config)
        self.extraction_agent = ParameterExtractionAgent(self.config)
        self.validation_agent = ValidationAgent(self.config)
        
        logger.info("✓ System initialized successfully")
    
    def process_documents(self, pdf_paths: List[str]) -> Dict[str, Any]:
        """
        Process PDF documents through the full pipeline.
        
        Args:
            pdf_paths: List of paths to PDF files
            
        Returns:
            Processing results
        """
        # Step 1: Ingestion
        logger.info("=" * 60)
        logger.info("STEP 1: PDF Ingestion")
        logger.info("=" * 60)
        documents = self.ingestion_agent.process(pdf_paths)
        
        if not documents:
            logger.error("✗ No documents processed")
            return {'error': 'No documents processed'}
        
        # Step 2: Preprocessing
        logger.info("=" * 60)
        logger.info("STEP 2: Text Chunking")
        logger.info("=" * 60)
        chunks_by_strategy = self.preprocessing_agent.chunk_documents(documents)
        
        # Step 3: Indexing
        logger.info("=" * 60)
        logger.info("STEP 3: Indexing Chunks")
        logger.info("=" * 60)
        self.rag_agent.index_chunks(chunks_by_strategy)
        
        # Get collection stats
        stats = self.rag_agent.get_collection_stats()
        logger.info(f"Collection stats: {stats}")
        
        return {
            'documents': documents,
            'chunks': chunks_by_strategy,
            'stats': stats
        }
    
    def extract_well_parameters(self, well_name: str) -> Dict[str, Any]:
        """
        Extract parameters for a specific well.
        
        Args:
            well_name: Name of the well (e.g., 'ADK-GT-01')
            
        Returns:
            Extraction and validation results
        """
        logger.info("=" * 60)
        logger.info(f"EXTRACTING PARAMETERS FOR: {well_name}")
        logger.info("=" * 60)
        
        # Step 4: Two-phase retrieval
        logger.info("STEP 4: Two-Phase Retrieval")
        retrieved_chunks = self.rag_agent.two_phase_retrieval(well_name)
        
        # Step 5: Parameter extraction
        logger.info("STEP 5: Parameter Extraction")
        extraction_result = self.extraction_agent.extract_from_chunks(retrieved_chunks)
        
        # Step 6: Validation
        logger.info("STEP 6: Validation")
        validation_report = self.validation_agent.validate_extraction(extraction_result)
        
        # Log results
        logger.info("=" * 60)
        logger.info("EXTRACTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Trajectory points: {len(extraction_result.get('trajectory', []))}")
        logger.info(f"Casing intervals: {len(extraction_result.get('casing', []))}")
        logger.info(f"Merged points: {len(extraction_result.get('merged', []))}")
        logger.info(f"Confidence: {extraction_result.get('confidence', 0):.2%}")
        logger.info(f"Valid: {validation_report['is_valid']}")
        
        if validation_report['errors']:
            logger.error("Errors:")
            for error in validation_report['errors']:
                logger.error(f"  - {error}")
        
        if validation_report['warnings']:
            logger.warning("Warnings:")
            for warning in validation_report['warnings']:
                logger.warning(f"  - {warning}")
        
        return {
            'well_name': well_name,
            'extraction': extraction_result,
            'validation': validation_report
        }
    
    def query(self, query: str, strategy: str = 'factual_qa') -> List[Dict[str, Any]]:
        """
        Query the system for information.
        
        Args:
            query: Query string
            strategy: Chunking strategy to use
            
        Returns:
            List of relevant chunks
        """
        return self.rag_agent.retrieve(query, strategy=strategy)


def main():
    """Main entry point for CLI usage."""
    if len(sys.argv) < 2:
        print("Usage: python main.py <pdf_file1> [pdf_file2 ...]")
        print("\nExample:")
        print("  python main.py data/ADK-GT-01.pdf")
        sys.exit(1)
    
    # Get PDF paths from command line
    pdf_paths = sys.argv[1:]
    
    # Validate paths
    for path in pdf_paths:
        if not Path(path).exists():
            print(f"Error: File not found: {path}")
            sys.exit(1)
    
    # Initialize system
    system = RAGGeothermalSystem()
    
    # Process documents
    results = system.process_documents(pdf_paths)
    
    if 'error' in results:
        print(f"Error: {results['error']}")
        sys.exit(1)
    
    # Extract well names from documents
    well_names = []
    for doc in results['documents']:
        well_names.extend(doc.get('wells', []))
    
    if not well_names:
        print("Warning: No well names detected in documents")
        sys.exit(0)
    
    # Extract parameters for each well
    print(f"\n✓ Found {len(well_names)} well(s): {', '.join(well_names)}")
    
    for well_name in well_names:
        extraction_results = system.extract_well_parameters(well_name)
        
        # Display results
        print(f"\n{'=' * 60}")
        print(f"RESULTS FOR: {well_name}")
        print('=' * 60)
        
        merged = extraction_results['extraction'].get('merged', [])
        if merged:
            print("\nExtracted Well Trajectory + Casing:")
            print(f"{'MD (m)':>10} {'TVD (m)':>10} {'Inc (°)':>10} {'Pipe ID (m)':>12}")
            print("-" * 46)
            for point in merged:
                print(f"{point['md']:>10.2f} {point['tvd']:>10.2f} "
                      f"{point['inc']:>10.2f} {point['pipe_id']:>12.4f}")
        else:
            print("\n⚠️ Could not extract complete well data")
        
        validation = extraction_results['validation']
        if validation['recommendations']:
            print("\nRecommendations:")
            for rec in validation['recommendations']:
                print(f"  - {rec}")


if __name__ == "__main__":
    main()
