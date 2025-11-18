"""Regex patterns for extracting geothermal well data."""

import re
from typing import List, Dict, Optional, Tuple
from .unit_conversion import parse_fractional_inches, inches_to_meters

# Well name patterns
WELL_NAME_PATTERNS = [
    r'[A-Z]{2,10}-GT-\d{2}(?:-S\d+)?',  # Dutch format: ADK-GT-01, ADK-GT-01-S1
    r'[A-Z]{3,}-\d{2,}',                # Generic: ABC-01, WXYZ-123
]

# Trajectory patterns (MD, TVD, Inclination)
TRAJECTORY_PATTERNS = [
    # Space-separated: "1000.5  995.2  1.5"
    r'(\d{1,5}\.?\d*)\s+(\d{1,5}\.?\d*)\s+(\d{1,2}\.?\d*)',
    # Tab-separated: "1000.5\t995.2\t1.5"
    r'(\d{1,5}\.?\d*)\t+(\d{1,5}\.?\d*)\t+(\d{1,2}\.?\d*)',
    # Pipe-separated: "| 1000.5 | 995.2 | 1.5 |"
    r'\|\s*(\d{1,5}\.?\d*)\s*\|\s*(\d{1,5}\.?\d*)\s*\|\s*(\d{1,2}\.?\d*)',
]

# Casing patterns
CASING_FRACTIONAL_PATTERNS = [
    # "13 3/8" casing from 0 to 1331m"
    r'(\d+)\s+(\d+)/(\d+)"\s+(?:casing|liner).*?(\d{3,4})\s*(?:m|meters?)',
    # "9 5/8" liner: 1298 - 2500m"
    r'(\d+)\s+(\d+)/(\d+)"\s+(?:casing|liner).*?(\d{3,4})\s*-\s*(\d{3,4})\s*(?:m|meters?)',
]

CASING_DECIMAL_PATTERNS = [
    # "13.375" casing to 1331m"
    r'(\d+\.\d+)"\s+(?:casing|liner).*?(\d{3,4})\s*(?:m|meters?)',
    # "9.625 inch casing from 1298m to 2500m"
    r'(\d+\.\d+)\s*(?:inch|")\s+(?:casing|liner).*?(\d{3,4})\s*-\s*(\d{3,4})\s*(?:m|meters?)',
    # "7" liner from 2450m to 3000m" (whole number)
    r'(\d+)"\s+(?:casing|liner).*?(?:from\s+)?(\d{3,4})m',
]

# Table detection patterns
TABLE_KEYWORDS = [
    'md', 'tvd', 'inclination', 'inc', 'survey', 'directional',
    'measured depth', 'true vertical depth', 'along hole', 'ah'
]

CASING_KEYWORDS = [
    'casing', 'liner', 'pipe id', 'drift', 'tubular', 'schematic',
    'inner diameter', 'od', 'outer diameter'
]

def extract_well_names(text: str) -> List[str]:
    """
    Extract well names from text.
    
    Args:
        text: Text to search
        
    Returns:
        List of unique well names found
    """
    well_names = set()
    
    for pattern in WELL_NAME_PATTERNS:
        matches = re.findall(pattern, text)
        well_names.update(matches)
    
    return sorted(list(well_names))

def extract_trajectory_data(text: str) -> List[Dict[str, float]]:
    """
    Extract trajectory survey data (MD, TVD, Inclination) from text.
    
    Args:
        text: Text containing trajectory data
        
    Returns:
        List of trajectory points: [{'md': 100, 'tvd': 100, 'inc': 0.5}, ...]
    """
    trajectory_points = []
    
    # Try each pattern
    for pattern in TRAJECTORY_PATTERNS:
        matches = re.findall(pattern, text, re.MULTILINE)
        
        for match in matches:
            try:
                md = float(match[0])
                tvd = float(match[1])
                inc = float(match[2])
                
                # Basic validation: skip invalid points
                if md >= tvd and 0 <= inc <= 90:
                    trajectory_points.append({
                        'md': md,
                        'tvd': tvd,
                        'inc': inc
                    })
            except (ValueError, IndexError):
                continue
    
    # Remove duplicates (same MD)
    seen_md = set()
    unique_points = []
    for point in trajectory_points:
        if point['md'] not in seen_md:
            seen_md.add(point['md'])
            unique_points.append(point)
    
    # Sort by MD
    unique_points.sort(key=lambda x: x['md'])
    
    return unique_points

def extract_casing_data(text: str) -> List[Dict[str, float]]:
    """
    Extract casing design data (depth, pipe ID) from text.
    
    Args:
        text: Text containing casing design
        
    Returns:
        List of casing intervals: [{'md': 1331, 'pipe_id': 0.311}, ...]
    """
    casing_intervals = []
    
    # Try fractional patterns first
    for pattern in CASING_FRACTIONAL_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        for match in matches:
            try:
                # Parse fractional inches: "13 3/8" → 13.375
                whole = int(match[0])
                numerator = int(match[1])
                denominator = int(match[2])
                size_inches = whole + (numerator / denominator)
                
                # Convert to meters (pipe ID, assume 95% of OD for ID)
                pipe_id_meters = inches_to_meters(size_inches * 0.95)
                
                # Extract depth
                if len(match) == 4:
                    md = float(match[3])
                    casing_intervals.append({
                        'md': md,
                        'pipe_id': pipe_id_meters
                    })
                elif len(match) == 5:
                    # Range provided, use top of interval
                    md = float(match[3])
                    casing_intervals.append({
                        'md': md,
                        'pipe_id': pipe_id_meters
                    })
            except (ValueError, IndexError):
                continue
    
    # Try decimal patterns
    for pattern in CASING_DECIMAL_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        for match in matches:
            try:
                size_inches = float(match[0])
                pipe_id_meters = inches_to_meters(size_inches * 0.95)
                
                if len(match) == 2:
                    md = float(match[1])
                    casing_intervals.append({
                        'md': md,
                        'pipe_id': pipe_id_meters
                    })
                elif len(match) == 3:
                    md = float(match[1])
                    casing_intervals.append({
                        'md': md,
                        'pipe_id': pipe_id_meters
                    })
            except (ValueError, IndexError):
                continue
    
    # Remove duplicates and sort
    seen_md = set()
    unique_intervals = []
    for interval in casing_intervals:
        if interval['md'] not in seen_md:
            seen_md.add(interval['md'])
            unique_intervals.append(interval)
    
    unique_intervals.sort(key=lambda x: x['md'])
    
    return unique_intervals

def is_trajectory_content(text: str) -> bool:
    """
    Detect if text contains trajectory survey data.
    
    Args:
        text: Text to analyze
        
    Returns:
        True if trajectory content detected
    """
    text_lower = text.lower()
    
    # Count keywords
    keyword_count = sum(1 for kw in TABLE_KEYWORDS if kw in text_lower)
    
    # Check for numeric patterns
    has_pattern = any(re.search(pattern, text) for pattern in TRAJECTORY_PATTERNS)
    
    return keyword_count >= 2 or has_pattern

def is_casing_content(text: str) -> bool:
    """
    Detect if text contains casing design data.
    
    Args:
        text: Text to analyze
        
    Returns:
        True if casing content detected
    """
    text_lower = text.lower()
    
    # Count keywords
    keyword_count = sum(1 for kw in CASING_KEYWORDS if kw in text_lower)
    
    # Check for fractional inch patterns
    has_fractional = bool(re.search(r'\d+\s+\d+/\d+"\s+(?:casing|liner)', text_lower))
    
    return keyword_count >= 2 or has_fractional
