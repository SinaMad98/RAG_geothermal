"""Example usage of RAG Geothermal Wells system."""

from main import RAGGeothermalSystem
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

def example_with_sample_data():
    """
    Example using synthetic sample data.
    
    This demonstrates the system without requiring actual PDF files.
    """
    print("=" * 70)
    print("RAG Geothermal Wells System - Example Usage")
    print("=" * 70)
    
    # Sample well report text (simulating extracted PDF content)
    sample_text = """
    --- Page 1 ---
    End of Well Report
    Well: ADK-GT-01
    Location: Aardgas Delft-Koekelaar
    
    --- Page 8 ---
    Tubular Design Schematic
    
    13 3/8" casing from surface to 1331m MD
    9 5/8" production liner from 1298m to 2500m MD
    7" slotted liner from 2450m to 2750m MD (total depth)
    
    --- Page 19 ---
    Appendix II: Directional Survey
    
    Measured Depth (MD)    True Vertical Depth (TVD)    Inclination (°)
    100.0                  100.0                        0.5
    500.0                  499.5                        0.8
    1000.0                 998.5                        1.2
    1331.0                 1328.0                       1.8
    1500.0                 1495.5                       2.1
    2000.0                 1993.0                       2.8
    2500.0                 2488.5                       3.5
    2750.0                 2735.0                       4.2
    """
    
    # Example of extraction patterns in action
    from utils.extraction_patterns import (
        extract_well_names,
        extract_trajectory_data,
        extract_casing_data
    )
    
    print("\n1. Extracting Well Names:")
    well_names = extract_well_names(sample_text)
    print(f"   Found: {well_names}")
    
    print("\n2. Extracting Trajectory Data:")
    trajectory = extract_trajectory_data(sample_text)
    print(f"   Extracted {len(trajectory)} trajectory points:")
    for i, point in enumerate(trajectory[:3]):  # Show first 3
        print(f"   [{i+1}] MD: {point['md']:.1f}m, TVD: {point['tvd']:.1f}m, Inc: {point['inc']:.1f}°")
    print(f"   ... and {len(trajectory)-3} more points")
    
    print("\n3. Extracting Casing Design:")
    casing = extract_casing_data(sample_text)
    print(f"   Extracted {len(casing)} casing strings:")
    for i, interval in enumerate(casing):
        print(f"   [{i+1}] MD: {interval['md']:.1f}m, Pipe ID: {interval['pipe_id']:.4f}m "
              f"({interval['pipe_id']*1000:.1f}mm)")
    
    print("\n4. Validation:")
    from utils.validation import validate_trajectory_list
    is_valid, errors = validate_trajectory_list(trajectory)
    print(f"   Trajectory valid: {is_valid}")
    if errors:
        print(f"   Errors: {errors}")
    else:
        print("   ✓ No errors detected")
    
    print("\n5. Merging Trajectory + Casing:")
    from agents import ParameterExtractionAgent
    from utils import load_config
    
    config = load_config()
    extraction_agent = ParameterExtractionAgent(config)
    
    merged = extraction_agent._merge_trajectory_casing(trajectory, casing)
    print(f"   Merged {len(merged)} points ready for nodal analysis:")
    print(f"   {'MD (m)':>10} {'TVD (m)':>10} {'Inc (°)':>10} {'Pipe ID (m)':>12}")
    print("   " + "-" * 46)
    for point in merged:
        print(f"   {point['md']:>10.2f} {point['tvd']:>10.2f} "
              f"{point['inc']:>10.2f} {point['pipe_id']:>12.4f}")
    
    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)

def example_unit_conversions():
    """Demonstrate unit conversion utilities."""
    print("\n" + "=" * 70)
    print("Unit Conversion Examples")
    print("=" * 70)
    
    from utils.unit_conversion import (
        parse_fractional_inches,
        inches_to_meters,
        bar_to_psi
    )
    
    print("\n1. Fractional Inches Parsing:")
    examples = ["13 3/8", "9 5/8", "7", "13.375"]
    for ex in examples:
        decimal = parse_fractional_inches(ex)
        meters = inches_to_meters(decimal)
        print(f"   {ex:>10} → {decimal:>8.3f} inches → {meters:>8.4f} meters")
    
    print("\n2. Pressure Conversions:")
    pressures_bar = [1, 10, 50, 100]
    for bar in pressures_bar:
        psi = bar_to_psi(bar)
        print(f"   {bar:>6.1f} bar = {psi:>8.2f} psi")

if __name__ == "__main__":
    # Run examples
    example_with_sample_data()
    example_unit_conversions()
    
    print("\n\n" + "=" * 70)
    print("To process actual PDF files, use:")
    print("  python main.py path/to/your/well_report.pdf")
    print("=" * 70)
