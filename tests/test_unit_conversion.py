"""Unit tests for unit conversion utilities."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.unit_conversion import (
    parse_fractional_inches,
    inches_to_meters,
    meters_to_inches,
    bar_to_psi,
    psi_to_bar
)

class TestFractionalInches:
    """Test fractional inch parsing."""
    
    def test_whole_and_fraction(self):
        """Test parsing 'whole fraction' format."""
        assert parse_fractional_inches("13 3/8") == 13.375
        assert parse_fractional_inches("9 5/8") == 9.625
        assert parse_fractional_inches("7 1/2") == 7.5
    
    def test_whole_number_only(self):
        """Test parsing whole numbers."""
        assert parse_fractional_inches("7") == 7.0
        assert parse_fractional_inches("13") == 13.0
    
    def test_decimal_format(self):
        """Test parsing decimal format."""
        assert parse_fractional_inches("13.375") == 13.375
        assert parse_fractional_inches("9.625") == 9.625
    
    def test_with_quotes(self):
        """Test parsing with inch marks."""
        assert parse_fractional_inches('13 3/8"') == 13.375
        assert parse_fractional_inches('9.625"') == 9.625
    
    def test_fraction_only(self):
        """Test parsing fraction without whole number."""
        assert parse_fractional_inches("3/8") == 0.375
        assert parse_fractional_inches("1/2") == 0.5

class TestInchesMeters:
    """Test inch-meter conversions."""
    
    def test_inches_to_meters(self):
        """Test conversion from inches to meters."""
        assert abs(inches_to_meters(1) - 0.0254) < 1e-6
        assert abs(inches_to_meters(10) - 0.254) < 1e-6
        assert abs(inches_to_meters(13.375) - 0.339725) < 1e-6
    
    def test_meters_to_inches(self):
        """Test conversion from meters to inches."""
        assert abs(meters_to_inches(0.0254) - 1.0) < 1e-6
        assert abs(meters_to_inches(0.254) - 10.0) < 1e-6
    
    def test_round_trip(self):
        """Test round-trip conversion."""
        original = 13.375
        converted = inches_to_meters(original)
        back = meters_to_inches(converted)
        assert abs(original - back) < 1e-10

class TestPressureConversion:
    """Test pressure conversions."""
    
    def test_bar_to_psi(self):
        """Test conversion from bar to psi."""
        assert abs(bar_to_psi(1) - 14.5038) < 0.001
        assert abs(bar_to_psi(10) - 145.038) < 0.001
    
    def test_psi_to_bar(self):
        """Test conversion from psi to bar."""
        assert abs(psi_to_bar(14.5038) - 1.0) < 0.001
        assert abs(psi_to_bar(145.038) - 10.0) < 0.001
    
    def test_round_trip(self):
        """Test round-trip conversion."""
        original = 50.0
        converted = bar_to_psi(original)
        back = psi_to_bar(converted)
        assert abs(original - back) < 1e-10
