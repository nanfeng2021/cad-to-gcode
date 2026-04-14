"""
Test DXF File Generator for CAD to G-code Platform

Generates simple shaft part DXF files for testing the parsing and feature recognition pipeline.
"""

from pathlib import Path
import math
import ezdxf
from ezdxf import units


def create_shaft_with_taper(output_path: str) -> str:
    """
    Create a shaft with a tapered section for testing taper recognition.
    
    Args:
        output_path: Output file path
        
    Returns:
        Path to created DXF file
    """
    doc = ezdxf.new(dxfversion='R2010')
    doc.units = units.MM
    doc.header['$INSUNITS'] = 4
    doc.header['$MEASUREMENT'] = 1
    
    msp = doc.modelspace()
    doc.layers.add('轮廓线', color=7)
    doc.layers.add('中心线', color=1)
    
    # Shaft with taper:
    # Section 1: Ø50mm cylinder, 30mm long (Z=0 to Z=-30)
    msp.add_line((25, 0, 0), (25, 0, -30), dxfattribs={'layer': '轮廓线'})
    
    # Section 2: Taper from Ø50mm to Ø30mm over 40mm (Z=-30 to Z=-70)
    # This is an INCLINED line!
    msp.add_line((25, 0, -30), (15, 0, -70), dxfattribs={'layer': '轮廓线'})
    
    # Section 3: Ø30mm cylinder, 30mm long (Z=-70 to Z=-100)
    msp.add_line((15, 0, -70), (15, 0, -100), dxfattribs={'layer': '轮廓线'})
    
    # Centerline
    msp.add_line((0, 0, 5), (0, 0, -105), dxfattribs={'layer': '中心线', 'linetype': 'DASHDOT'})
    
    # Save
    doc.saveas(str(output_path))
    
    print(f"✓ Created shaft with taper DXF: {output_path}")
    print(f"  Entities: {len(msp)}")
    print(f"  Sections:")
    print(f"    - Ø50mm cylinder (30mm)")
    print(f"    - Taper Ø50→Ø30mm (40mm, angle={math.degrees(math.atan2(10, 40)):.1f}°)")
    print(f"    - Ø30mm cylinder (30mm)")
    
    return str(output_path)


def create_simple_shaft_dxf(output_path: str) -> str:
    """Create a simple stepped shaft for testing."""
    doc = ezdxf.new(dxfversion='R2010')
    doc.units = units.MM
    doc.header['$INSUNITS'] = 4
    doc.header['$MEASUREMENT'] = 1
    
    msp = doc.modelspace()
    doc.layers.add('轮廓线', color=7)
    doc.layers.add('中心线', color=1)
    
    # Stepped shaft: Ø50 → Ø40 → Ø30 → Ø20
    msp.add_line((25, 0, 0), (25, 0, -30), dxfattribs={'layer': '轮廓线'})
    msp.add_line((25, 0, -30), (20, 0, -30), dxfattribs={'layer': '轮廓线'})  # Shoulder
    msp.add_line((20, 0, -30), (20, 0, -60), dxfattribs={'layer': '轮廓线'})
    msp.add_line((20, 0, -60), (15, 0, -60), dxfattribs={'layer': '轮廓线'})  # Shoulder
    msp.add_line((15, 0, -60), (15, 0, -100), dxfattribs={'layer': '轮廓线'})
    
    # Centerline
    msp.add_line((0, 0, 5), (0, 0, -105), dxfattribs={'layer': '中心线', 'linetype': 'DASHDOT'})
    
    doc.saveas(str(output_path))
    print(f"✓ Created simple shaft DXF: {output_path}")
    return str(output_path)


def create_shaft_with_groove(output_path: str) -> str:
    """
    Create a shaft with a groove for testing groove recognition.
    
    Args:
        output_path: Output file path
        
    Returns:
        Path to created DXF file
    """
    doc = ezdxf.new(dxfversion='R2010')
    doc.units = units.MM
    doc.header['$INSUNITS'] = 4
    doc.header['$MEASUREMENT'] = 1
    
    msp = doc.modelspace()
    doc.layers.add('轮廓线', color=7)
    doc.layers.add('中心线', color=1)
    
    # Shaft profile with a groove
    # Main shaft: 50mm diameter
    msp.add_line((25, 0, 0), (25, 0, -40), dxfattribs={'layer': '轮廓线'})
    
    # Groove: 3mm wide, 2mm deep at Z=-40 to -43
    msp.add_line((25, 0, -40), (23, 0, -40), dxfattribs={'layer': '轮廓线'})  # Left side of groove
    msp.add_line((23, 0, -40), (23, 0, -43), dxfattribs={'layer': '轮廓线'})  # Bottom of groove
    msp.add_line((23, 0, -43), (25, 0, -43), dxfattribs={'layer': '轮廓线'})  # Right side of groove
    
    # Continue shaft: 25mm diameter
    msp.add_line((25, 0, -43), (25, 0, -80), dxfattribs={'layer': '轮廓线'})
    
    # Smaller diameter section: 20mm
    msp.add_line((25, 0, -80), (20, 0, -80), dxfattribs={'layer': '轮廓线'})  # Shoulder
    msp.add_line((20, 0, -80), (20, 0, -100), dxfattribs={'layer': '轮廓线'})
    
    # Centerline
    msp.add_line((0, 0, 5), (0, 0, -105), dxfattribs={'layer': '中心线', 'linetype': 'DASHDOT'})
    
    # Save
    doc.saveas(str(output_path))
    
    print(f"✓ Created shaft with groove DXF: {output_path}")
    print(f"  Entities: {len(msp)}")
    
    return str(output_path)


if __name__ == "__main__":
    import sys
    
    output_dir = Path("/mnt/g/projects/cad-to-gcode/tests/test_dxf_files")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Test 1: Simple stepped shaft
    shaft_file = output_dir / "simple_shaft.dxf"
    create_simple_shaft_dxf(str(shaft_file))
    
    # Test 2: Shaft with taper (NEW!)
    taper_file = output_dir / "tapered_shaft.dxf"
    create_shaft_with_taper(str(taper_file))
    
    # Test 3: Shaft with groove
    groove_file = output_dir / "shaft_with_groove.dxf"
    create_shaft_with_groove(str(groove_file))
    
    print(f"\n✓ All test DXF files created in: {output_dir}")
    print(f"  - simple_shaft.dxf (stepped shaft)")
    print(f"  - tapered_shaft.dxf (with taper section)")
    print(f"  - shaft_with_groove.dxf (with groove)")
