"""Unit conversion utilities for geothermal well data."""

import re
from typing import Union

def parse_fractional_inches(size_str: str) -> float:
    """
    Convert fractional inch notation to decimal.
    
    Examples:
        "13 3/8" → 13.375
        "9 5/8" → 9.625
        "7" → 7.0
        '13 3/8"' → 13.375
    
    Args:
        size_str: Pipe size string (e.g., "13 3/8", "9.625")
        
    Returns:
        Decimal inch value
    """
    # Remove quotes and extra whitespace
    size_str = size_str.strip().replace('"', '').replace("'", '')
    
    # Handle fractional format: "13 3/8"
    if '/' in size_str:
        parts = size_str.split()
        
        if len(parts) == 2:
            # Format: "13 3/8"
            whole = int(parts[0])
            frac_parts = parts[1].split('/')
            numerator = int(frac_parts[0])
            denominator = int(frac_parts[1])
            return whole + (numerator / denominator)
        elif len(parts) == 1:
            # Format: "3/8" (no whole number)
            frac_parts = parts[0].split('/')
            numerator = int(frac_parts[0])
            denominator = int(frac_parts[1])
            return numerator / denominator
    
    # Handle decimal format: "13.375" or "7"
    return float(size_str)

def inches_to_meters(inches: Union[float, int]) -> float:
    """
    Convert inches to meters.
    
    Args:
        inches: Value in inches
        
    Returns:
        Value in meters
    """
    return inches * 0.0254

def meters_to_inches(meters: Union[float, int]) -> float:
    """
    Convert meters to inches.
    
    Args:
        meters: Value in meters
        
    Returns:
        Value in inches
    """
    return meters / 0.0254

def bar_to_psi(bar: Union[float, int]) -> float:
    """
    Convert bar to psi.
    
    Args:
        bar: Pressure in bar
        
    Returns:
        Pressure in psi
    """
    return bar * 14.5038

def psi_to_bar(psi: Union[float, int]) -> float:
    """
    Convert psi to bar.
    
    Args:
        psi: Pressure in psi
        
    Returns:
        Pressure in bar
    """
    return psi / 14.5038

def celsius_to_fahrenheit(celsius: Union[float, int]) -> float:
    """
    Convert Celsius to Fahrenheit.
    
    Args:
        celsius: Temperature in Celsius
        
    Returns:
        Temperature in Fahrenheit
    """
    return (celsius * 9/5) + 32

def fahrenheit_to_celsius(fahrenheit: Union[float, int]) -> float:
    """
    Convert Fahrenheit to Celsius.
    
    Args:
        fahrenheit: Temperature in Fahrenheit
        
    Returns:
        Temperature in Celsius
    """
    return (fahrenheit - 32) * 5/9
