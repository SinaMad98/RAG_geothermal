"""Unit tests for extraction patterns."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.extraction_patterns import (
    extract_well_names,
    extract_trajectory_data,
    extract_casing_data,
    is_trajectory_content,
    is_casing_content
)

class TestWellNameExtraction:
    """Test well name extraction."""
    
    def test_dutch_format(self):
        """Test extraction of Dutch geothermal well names."""
        text = "Well ADK-GT-01 report for production analysis"
        names = extract_well_names(text)
        assert 'ADK-GT-01' in names
    
    def test_sidetrack_format(self):
        """Test extraction of sidetrack well names."""
        text = "Sidetrack ADK-GT-01-S1 was drilled in 2020"
        names = extract_well_names(text)
        assert 'ADK-GT-01-S1' in names
    
    def test_multiple_wells(self):
        """Test extraction of multiple well names."""
        text = "Wells ADK-GT-01 and BVD-GT-02 in the doublet system"
        names = extract_well_names(text)
        assert 'ADK-GT-01' in names
        assert 'BVD-GT-02' in names

class TestTrajectoryExtraction:
    """Test trajectory data extraction."""
    
    def test_space_separated(self):
        """Test extraction from space-separated format."""
        text = """
        MD      TVD     Inc
        100.0   100.0   0.5
        500.0   498.5   1.0
        1000.0  995.0   1.5
        """
        points = extract_trajectory_data(text)
        assert len(points) >= 3
        assert points[0]['md'] == 100.0
        assert points[0]['tvd'] == 100.0
        assert points[0]['inc'] == 0.5
    
    def test_tab_separated(self):
        """Test extraction from tab-separated format."""
        text = "100.0\t100.0\t0.5\n500.0\t498.5\t1.0"
        points = extract_trajectory_data(text)
        assert len(points) >= 2
    
    def test_table_format(self):
        """Test extraction from table with pipes."""
        text = """
        | 100.0 | 100.0 | 0.5 |
        | 500.0 | 498.5 | 1.0 |
        """
        points = extract_trajectory_data(text)
        assert len(points) >= 2
    
    def test_invalid_data_filtered(self):
        """Test that invalid points are filtered out."""
        text = "1000 1005 1.5"  # MD < TVD (invalid)
        points = extract_trajectory_data(text)
        # Should not extract this point as it's physically impossible
        assert not any(p['md'] == 1000 and p['tvd'] == 1005 for p in points)

class TestCasingExtraction:
    """Test casing data extraction."""
    
    def test_fractional_inches(self):
        """Test extraction of fractional inch notation."""
        text = '13 3/8" casing from 0 to 1331m'
        intervals = extract_casing_data(text)
        assert len(intervals) >= 1
        # 13 3/8" * 0.95 (ID/OD ratio) * 0.0254 (inch to m) ≈ 0.323m
        assert intervals[0]['md'] == 1331
        assert 0.30 < intervals[0]['pipe_id'] < 0.35
    
    def test_decimal_inches(self):
        """Test extraction of decimal inch notation."""
        text = '9.625" casing to 2500m'
        intervals = extract_casing_data(text)
        assert len(intervals) >= 1
        assert intervals[0]['md'] == 2500
        # 9.625" * 0.95 * 0.0254 ≈ 0.232m
        assert 0.20 < intervals[0]['pipe_id'] < 0.25
    
    def test_liner_format(self):
        """Test extraction of liner notation."""
        text = '7" liner from 2450m to 3000m'
        intervals = extract_casing_data(text)
        assert len(intervals) >= 1
        assert intervals[0]['md'] == 2450

class TestContentDetection:
    """Test content type detection."""
    
    def test_trajectory_detection(self):
        """Test detection of trajectory content."""
        text = """
        Directional Survey Results
        MD      TVD     Inclination
        100.0   100.0   0.5
        """
        assert is_trajectory_content(text)
    
    def test_casing_detection(self):
        """Test detection of casing content."""
        text = """
        Tubular Design
        13 3/8" casing to 1331m
        9 5/8" liner to 2500m
        """
        assert is_casing_content(text)
    
    def test_non_relevant_content(self):
        """Test rejection of non-relevant content."""
        text = "This is general information about the drilling operation"
        assert not is_trajectory_content(text)
        assert not is_casing_content(text)
