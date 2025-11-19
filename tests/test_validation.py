"""Unit tests for validation utilities."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.validation import (
    validate_trajectory_point,
    validate_pipe_diameter,
    validate_trajectory_list
)

class TestTrajectoryPointValidation:
    """Test single trajectory point validation."""
    
    def test_valid_point(self):
        """Test validation of valid trajectory point."""
        point = {'md': 1000, 'tvd': 995, 'inc': 1.5}
        is_valid, errors = validate_trajectory_point(point)
        assert is_valid
        assert len(errors) == 0
    
    def test_md_less_than_tvd(self):
        """Test rejection when MD < TVD."""
        point = {'md': 1000, 'tvd': 1005, 'inc': 1.5}
        is_valid, errors = validate_trajectory_point(point)
        assert not is_valid
        assert any('physically impossible' in e for e in errors)
    
    def test_negative_inclination(self):
        """Test rejection of negative inclination."""
        point = {'md': 1000, 'tvd': 995, 'inc': -1.5}
        is_valid, errors = validate_trajectory_point(point)
        assert not is_valid
        assert any('negative' in e.lower() for e in errors)
    
    def test_excessive_inclination(self):
        """Test rejection of inclination > 90°."""
        point = {'md': 1000, 'tvd': 995, 'inc': 95}
        is_valid, errors = validate_trajectory_point(point)
        assert not is_valid
        assert any('exceeds maximum' in e for e in errors)
    
    def test_missing_fields(self):
        """Test rejection when required fields missing."""
        point = {'md': 1000}  # Missing TVD
        is_valid, errors = validate_trajectory_point(point)
        assert not is_valid
        assert any('tvd' in e.lower() for e in errors)

class TestPipeDiameterValidation:
    """Test pipe diameter validation."""
    
    def test_valid_diameter(self):
        """Test validation of typical pipe diameter."""
        # 9 5/8" casing = 0.244m ID
        is_valid, errors = validate_pipe_diameter(0.244)
        assert is_valid
        assert len(errors) == 0
    
    def test_too_small_diameter(self):
        """Test rejection of unrealistically small diameter."""
        is_valid, errors = validate_pipe_diameter(0.01)  # 10mm
        assert not is_valid
        assert any('below minimum' in e for e in errors)
    
    def test_too_large_diameter(self):
        """Test rejection of unrealistically large diameter."""
        is_valid, errors = validate_pipe_diameter(2.0)  # 2000mm
        assert not is_valid
        assert any('exceeds maximum' in e for e in errors)

class TestTrajectoryListValidation:
    """Test trajectory list validation."""
    
    def test_valid_trajectory(self):
        """Test validation of valid trajectory list."""
        trajectory = [
            {'md': 100, 'tvd': 100, 'inc': 0.5},
            {'md': 500, 'tvd': 498, 'inc': 1.0},
            {'md': 1000, 'tvd': 995, 'inc': 1.5},
        ]
        is_valid, errors = validate_trajectory_list(trajectory)
        assert is_valid
        assert len(errors) == 0
    
    def test_empty_trajectory(self):
        """Test rejection of empty trajectory."""
        trajectory = []
        is_valid, errors = validate_trajectory_list(trajectory)
        assert not is_valid
        assert any('empty' in e.lower() for e in errors)
    
    def test_too_few_points(self):
        """Test warning for trajectory with only 1 point."""
        trajectory = [{'md': 100, 'tvd': 100, 'inc': 0.5}]
        is_valid, errors = validate_trajectory_list(trajectory)
        assert not is_valid
        assert any('fewer than 2' in e for e in errors)
    
    def test_non_monotonic_md(self):
        """Test rejection when MD values not increasing."""
        trajectory = [
            {'md': 500, 'tvd': 498, 'inc': 1.0},
            {'md': 100, 'tvd': 100, 'inc': 0.5},  # Out of order
            {'md': 1000, 'tvd': 995, 'inc': 1.5},
        ]
        is_valid, errors = validate_trajectory_list(trajectory)
        assert not is_valid
        assert any('not monotonically increasing' in e for e in errors)
