"""Validation Agent: Data Quality + User Interaction."""

import logging
from typing import List, Dict, Any, Tuple
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.validation import (
    validate_trajectory_list,
    validate_fluid_properties
)

logger = logging.getLogger(__name__)

class ValidationAgent:
    """
    Validates extracted parameters and handles user interaction.
    
    Responsibilities:
    - Physics-based validation (MD≥TVD, realistic diameters)
    - Statistical outlier detection
    - Missing data identification
    - Confidence scoring
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ValidationAgent.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.validation_config = config.get('validation', {})
        logger.info("ValidationAgent initialized")
    
    def validate_extraction(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extraction results.
        
        Args:
            extraction_result: Result from ParameterExtractionAgent
            
        Returns:
            Validation report:
            {
                'is_valid': True/False,
                'errors': ['error1', ...],
                'warnings': ['warning1', ...],
                'confidence': 0.85,
                'recommendations': ['rec1', ...]
            }
        """
        report = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'confidence': extraction_result.get('confidence', 0.0),
            'recommendations': []
        }
        
        # Validate trajectory data
        trajectory = extraction_result.get('trajectory', [])
        if trajectory:
            is_valid, errors = validate_trajectory_list(trajectory, self.config)
            if not is_valid:
                report['is_valid'] = False
                report['errors'].extend([f"Trajectory: {e}" for e in errors])
            logger.info(f"✓ Trajectory validation: {len(trajectory)} points, valid={is_valid}")
        else:
            report['warnings'].append("No trajectory data extracted")
        
        # Validate casing data
        casing = extraction_result.get('casing', [])
        if casing:
            for i, interval in enumerate(casing):
                if 'pipe_id' not in interval:
                    report['warnings'].append(f"Casing interval {i}: missing pipe_id")
                else:
                    # Basic pipe diameter check
                    pipe_id_mm = interval['pipe_id'] * 1000
                    min_mm = self.validation_config.get('pipe_id_min_mm', 50)
                    max_mm = self.validation_config.get('pipe_id_max_mm', 1000)
                    
                    if pipe_id_mm < min_mm or pipe_id_mm > max_mm:
                        report['warnings'].append(
                            f"Casing interval {i}: pipe_id {pipe_id_mm:.1f}mm outside range ({min_mm}-{max_mm}mm)"
                        )
            logger.info(f"✓ Casing validation: {len(casing)} intervals")
        else:
            report['warnings'].append("No casing data extracted")
        
        # Validate merged data
        merged = extraction_result.get('merged', [])
        if merged:
            is_valid, errors = validate_trajectory_list(merged, self.config)
            if not is_valid:
                report['is_valid'] = False
                report['errors'].extend([f"Merged: {e}" for e in errors])
            logger.info(f"✓ Merged data validation: {len(merged)} points, valid={is_valid}")
        else:
            if trajectory and casing:
                report['warnings'].append("Trajectory and casing data exist but not merged")
        
        # Check confidence threshold
        threshold = self.config.get('extraction', {}).get('confidence_threshold', 0.7)
        if report['confidence'] < threshold:
            report['warnings'].append(
                f"Confidence ({report['confidence']:.2f}) below threshold ({threshold})"
            )
            report['recommendations'].append(
                "Consider manually reviewing extracted data or providing additional context"
            )
        
        # Generate recommendations
        if not trajectory and not casing:
            report['recommendations'].append(
                "No well data extracted. Check if PDF contains trajectory and casing information."
            )
        elif not trajectory:
            report['recommendations'].append(
                "Missing trajectory data. Look for pages with 'MD', 'TVD', 'Inclination' tables."
            )
        elif not casing:
            report['recommendations'].append(
                "Missing casing data. Look for pages with 'casing design' or 'tubular schematic'."
            )
        
        return report
    
    def validate_fluid_properties(self, properties: Dict[str, float]) -> Dict[str, Any]:
        """
        Validate fluid properties.
        
        Args:
            properties: Dictionary with 'density', 'viscosity', etc.
            
        Returns:
            Validation report
        """
        report = {
            'is_valid': True,
            'warnings': []
        }
        
        density = properties.get('density')
        viscosity = properties.get('viscosity')
        
        is_valid, warnings = validate_fluid_properties(density, viscosity, self.config)
        
        if not is_valid:
            report['is_valid'] = False
        
        report['warnings'].extend(warnings)
        
        return report
    
    def get_missing_data_prompt(self, extraction_result: Dict[str, Any]) -> str:
        """
        Generate user prompt for missing data.
        
        Args:
            extraction_result: Extraction result
            
        Returns:
            User-friendly prompt string
        """
        prompts = []
        
        trajectory = extraction_result.get('trajectory', [])
        casing = extraction_result.get('casing', [])
        
        if not trajectory:
            prompts.append(
                "⚠️ Trajectory data not found. Please provide:\n"
                "   - Measured Depth (MD)\n"
                "   - True Vertical Depth (TVD)\n"
                "   - Inclination (degrees)"
            )
        
        if not casing:
            prompts.append(
                "⚠️ Casing design not found. Please provide:\n"
                "   - Casing depths (MD)\n"
                "   - Pipe internal diameters (inches or mm)"
            )
        
        if not prompts:
            return "✓ All required data extracted successfully"
        
        return "\n\n".join(prompts)
    
    def suggest_defaults(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest default values for missing data.
        
        Args:
            extraction_result: Extraction result
            
        Returns:
            Dictionary with suggested defaults
        """
        defaults = {}
        
        # If no fluid density, suggest default
        if 'fluid_properties' not in extraction_result:
            defaults['fluid_density'] = self.validation_config.get('default_fluid_density', 1000)
            defaults['fluid_density_source'] = 'default (water)'
        
        # If partial trajectory, suggest interpolation
        trajectory = extraction_result.get('trajectory', [])
        if trajectory and len(trajectory) < 5:
            defaults['interpolation_needed'] = True
            defaults['interpolation_reason'] = f"Only {len(trajectory)} trajectory points found"
        
        return defaults
