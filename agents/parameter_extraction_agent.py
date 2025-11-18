"""Parameter Extraction Agent: Chunks → Structured Data."""

import logging
from typing import List, Dict, Any, Optional, Tuple
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.extraction_patterns import (
    extract_trajectory_data,
    extract_casing_data,
    is_trajectory_content,
    is_casing_content
)
from utils.validation import validate_trajectory_point

logger = logging.getLogger(__name__)

class ParameterExtractionAgent:
    """
    Extracts structured well parameters from text chunks.
    
    Responsibilities:
    - Content-type detection (trajectory vs casing vs PVT)
    - Regex-first extraction with LLM fallback
    - Unit conversion (inches→meters, fractional→decimal)
    - Merging trajectory + casing data
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ParameterExtractionAgent.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.extraction_config = config.get('extraction', {})
        self.use_regex_first = self.extraction_config.get('use_regex_first', True)
        logger.info("ParameterExtractionAgent initialized")
    
    def extract_from_chunks(self, chunks: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Extract parameters from retrieved chunks.
        
        Args:
            chunks: Dictionary with 'trajectory' and 'casing' chunks
            
        Returns:
            Extracted parameters:
            {
                'trajectory': [{'md': 100, 'tvd': 100, 'inc': 0.5}, ...],
                'casing': [{'md': 1331, 'pipe_id': 0.311}, ...],
                'merged': [{'md': 100, 'tvd': 100, 'inc': 0.5, 'pipe_id': 0.311}, ...],
                'confidence': 0.85
            }
        """
        result = {
            'trajectory': [],
            'casing': [],
            'merged': [],
            'confidence': 0.0
        }
        
        # Extract trajectory data
        trajectory_chunks = chunks.get('trajectory', [])
        if trajectory_chunks:
            trajectory_points = self._extract_trajectory(trajectory_chunks)
            result['trajectory'] = trajectory_points
            logger.info(f"✓ Extracted {len(trajectory_points)} trajectory points")
        
        # Extract casing data
        casing_chunks = chunks.get('casing', [])
        if casing_chunks:
            casing_intervals = self._extract_casing(casing_chunks)
            result['casing'] = casing_intervals
            logger.info(f"✓ Extracted {len(casing_intervals)} casing intervals")
        
        # Merge trajectory + casing
        if result['trajectory'] and result['casing']:
            merged = self._merge_trajectory_casing(
                result['trajectory'], 
                result['casing']
            )
            result['merged'] = merged
            logger.info(f"✓ Merged data: {len(merged)} points with complete information")
        
        # Calculate confidence score
        result['confidence'] = self._calculate_confidence(result)
        
        return result
    
    def _extract_trajectory(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, float]]:
        """
        Extract trajectory survey data from chunks.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            List of trajectory points
        """
        all_points = []
        
        for chunk in chunks:
            content = chunk['content']
            
            # Check if this chunk contains trajectory data
            if not is_trajectory_content(content):
                continue
            
            # Extract using regex patterns
            points = extract_trajectory_data(content)
            all_points.extend(points)
        
        # Remove duplicates based on MD
        seen_md = {}
        unique_points = []
        for point in all_points:
            md = point['md']
            if md not in seen_md:
                seen_md[md] = point
                unique_points.append(point)
        
        # Sort by MD
        unique_points.sort(key=lambda x: x['md'])
        
        return unique_points
    
    def _extract_casing(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, float]]:
        """
        Extract casing design data from chunks.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            List of casing intervals
        """
        all_intervals = []
        
        for chunk in chunks:
            content = chunk['content']
            
            # Check if this chunk contains casing data
            if not is_casing_content(content):
                continue
            
            # Extract using regex patterns
            intervals = extract_casing_data(content)
            all_intervals.extend(intervals)
        
        # Remove duplicates based on MD
        seen_md = {}
        unique_intervals = []
        for interval in all_intervals:
            md = interval['md']
            if md not in seen_md:
                seen_md[md] = interval
                unique_intervals.append(interval)
        
        # Sort by MD
        unique_intervals.sort(key=lambda x: x['md'])
        
        return unique_intervals
    
    def _merge_trajectory_casing(self, trajectory_points: List[Dict[str, float]], 
                                 casing_intervals: List[Dict[str, float]]) -> List[Dict[str, float]]:
        """
        Merge trajectory and casing data.
        
        For each casing string top, find closest trajectory point and combine.
        
        Args:
            trajectory_points: List of trajectory points with MD, TVD, Inc
            casing_intervals: List of casing intervals with MD, pipe_id
            
        Returns:
            Merged list with MD, TVD, Inc, pipe_id
        """
        if not trajectory_points or not casing_intervals:
            return []
        
        merged = []
        
        # Sort both by MD
        trajectory_points.sort(key=lambda x: x['md'])
        casing_intervals.sort(key=lambda x: x['md'])
        
        # For each casing string, find closest trajectory point
        for casing in casing_intervals:
            casing_md = casing['md']
            
            # Find trajectory point with closest MD
            closest = min(trajectory_points, key=lambda t: abs(t['md'] - casing_md))
            
            merged_point = {
                'md': casing_md,           # Use casing depth (string top)
                'tvd': closest['tvd'],      # TVD from trajectory
                'inc': closest['inc'],      # Inclination from trajectory
                'pipe_id': casing['pipe_id'] # Pipe ID from casing design
            }
            
            merged.append(merged_point)
        
        # Add total depth (TD) point with last casing ID
        if trajectory_points:
            td_point = trajectory_points[-1]
            last_casing = casing_intervals[-1]
            
            # Only add if TD is deeper than last casing
            if td_point['md'] > merged[-1]['md']:
                merged.append({
                    'md': td_point['md'],
                    'tvd': td_point['tvd'],
                    'inc': td_point['inc'],
                    'pipe_id': last_casing['pipe_id']  # Extend last casing to TD
                })
        
        return merged
    
    def _calculate_confidence(self, result: Dict[str, Any]) -> float:
        """
        Calculate confidence score for extraction.
        
        Args:
            result: Extraction result dictionary
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 0.0
        
        # Base confidence from data availability
        if result['trajectory']:
            confidence += 0.4
        if result['casing']:
            confidence += 0.3
        if result['merged']:
            confidence += 0.3
        
        # Adjust based on data quality
        if result['merged']:
            # Check if all merged points pass validation
            valid_count = 0
            for point in result['merged']:
                is_valid, _ = validate_trajectory_point(point, self.config)
                if is_valid:
                    valid_count += 1
            
            if len(result['merged']) > 0:
                validation_ratio = valid_count / len(result['merged'])
                confidence *= validation_ratio
        
        return min(confidence, 1.0)
    
    def extract_fluid_properties(self, chunks: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
        """
        Extract fluid properties from chunks.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Dictionary with fluid properties: {'density': 1000, 'viscosity': 0.001}
        """
        # Simple implementation - can be enhanced with regex patterns
        properties = {
            'density': None,
            'viscosity': None,
            'temperature': None
        }
        
        # Use default values from config if not found
        if properties['density'] is None:
            properties['density'] = self.config.get('validation', {}).get('default_fluid_density', 1000)
        
        return properties
