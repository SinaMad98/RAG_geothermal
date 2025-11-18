"""Validation utilities for geothermal well data."""

from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)

def validate_trajectory_point(point: Dict[str, float], config: Dict[str, Any] = None) -> Tuple[bool, List[str]]:
    """
    Validate a single trajectory point using physics-based rules.
    
    Args:
        point: Dictionary with keys 'md', 'tvd', 'inc' (and optionally 'pipe_id')
        config: Configuration dictionary with validation parameters
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Default config values if not provided
    if config is None:
        config = {
            'validation': {
                'md_tvd_tolerance': 1.0,
                'inclination_max_deg': 90,
                'inclination_warning_deg': 80
            }
        }
    
    val_config = config.get('validation', {})
    tolerance = val_config.get('md_tvd_tolerance', 1.0)
    max_inc = val_config.get('inclination_max_deg', 90)
    warn_inc = val_config.get('inclination_warning_deg', 80)
    
    # Check required fields
    if 'md' not in point:
        errors.append("Missing 'md' (measured depth)")
    if 'tvd' not in point:
        errors.append("Missing 'tvd' (true vertical depth)")
    
    if errors:
        return False, errors
    
    md = point['md']
    tvd = point['tvd']
    
    # Critical: MD must be >= TVD (allowing small tolerance for rounding)
    if md < tvd - tolerance:
        errors.append(f"MD ({md:.2f}m) < TVD ({tvd:.2f}m) - physically impossible")
        return False, errors
    
    # Check inclination if present
    if 'inc' in point:
        inc = point['inc']
        
        if inc < 0:
            errors.append(f"Inclination ({inc:.2f}°) is negative")
            return False, errors
        
        if inc > max_inc:
            errors.append(f"Inclination ({inc:.2f}°) exceeds maximum ({max_inc}°)")
            return False, errors
        
        if inc > warn_inc:
            logger.warning(f"High inclination: {inc:.2f}° at MD={md:.2f}m (warning threshold: {warn_inc}°)")
    
    # Check pipe ID if present
    if 'pipe_id' in point:
        is_valid, pipe_errors = validate_pipe_diameter(point['pipe_id'], config)
        if not is_valid:
            errors.extend(pipe_errors)
            return False, errors
    
    return True, errors

def validate_pipe_diameter(diameter: float, config: Dict[str, Any] = None) -> Tuple[bool, List[str]]:
    """
    Validate pipe internal diameter.
    
    Args:
        diameter: Pipe ID in meters
        config: Configuration dictionary
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if config is None:
        config = {
            'validation': {
                'pipe_id_min_mm': 50,
                'pipe_id_max_mm': 1000
            }
        }
    
    val_config = config.get('validation', {})
    min_mm = val_config.get('pipe_id_min_mm', 50)
    max_mm = val_config.get('pipe_id_max_mm', 1000)
    
    # Convert to mm for comparison
    diameter_mm = diameter * 1000
    
    if diameter_mm < min_mm:
        errors.append(f"Pipe ID ({diameter_mm:.1f}mm) below minimum ({min_mm}mm)")
        return False, errors
    
    if diameter_mm > max_mm:
        errors.append(f"Pipe ID ({diameter_mm:.1f}mm) exceeds maximum ({max_mm}mm) - likely wrong unit")
        return False, errors
    
    return True, errors

def validate_fluid_properties(density: float = None, viscosity: float = None, 
                              config: Dict[str, Any] = None) -> Tuple[bool, List[str]]:
    """
    Validate fluid properties.
    
    Args:
        density: Fluid density in kg/m³
        viscosity: Fluid viscosity in Pa·s (optional)
        config: Configuration dictionary
        
    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    warnings = []
    
    if config is None:
        config = {
            'validation': {
                'fluid_density_min': 800,
                'fluid_density_max': 1200
            }
        }
    
    val_config = config.get('validation', {})
    
    if density is not None:
        min_density = val_config.get('fluid_density_min', 800)
        max_density = val_config.get('fluid_density_max', 1200)
        
        if density < min_density:
            warnings.append(f"Fluid density ({density:.1f} kg/m³) below typical range ({min_density}-{max_density})")
        elif density > max_density:
            warnings.append(f"Fluid density ({density:.1f} kg/m³) above typical range ({min_density}-{max_density})")
    
    if viscosity is not None:
        # Typical water viscosity at 20°C: ~0.001 Pa·s
        # Typical range for geothermal: 0.0001 to 0.01 Pa·s
        if viscosity < 0.0001 or viscosity > 0.01:
            warnings.append(f"Fluid viscosity ({viscosity:.6f} Pa·s) outside typical range (0.0001-0.01)")
    
    # Warnings don't invalidate, just inform
    return True, warnings

def validate_trajectory_list(trajectory: List[Dict[str, float]], 
                            config: Dict[str, Any] = None) -> Tuple[bool, List[str]]:
    """
    Validate entire trajectory list.
    
    Args:
        trajectory: List of trajectory points
        config: Configuration dictionary
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    all_errors = []
    
    if not trajectory:
        return False, ["Trajectory is empty"]
    
    if len(trajectory) < 2:
        all_errors.append("Trajectory has fewer than 2 points")
    
    # Validate each point
    for i, point in enumerate(trajectory):
        is_valid, errors = validate_trajectory_point(point, config)
        if not is_valid:
            all_errors.append(f"Point {i} (MD={point.get('md', 'N/A')}): {', '.join(errors)}")
    
    # Check that MD values are monotonically increasing
    md_values = [p['md'] for p in trajectory if 'md' in p]
    if len(md_values) >= 2:
        for i in range(1, len(md_values)):
            if md_values[i] <= md_values[i-1]:
                all_errors.append(f"MD values not monotonically increasing at index {i}: "
                                f"{md_values[i-1]:.2f} → {md_values[i]:.2f}")
    
    return len(all_errors) == 0, all_errors
