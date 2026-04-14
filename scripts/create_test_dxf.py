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
    return str(output_path)


def create_shaft_with_thread(output_path: str) -> str:
    """
    Create a shaft with external thread for testing thread recognition.
    
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
    
    # Shaft with thread:
    # Section 1: Ø50mm cylinder, 40mm long (Z=0 to Z=-40)
    msp.add_line((25, 0, 0), (25, 0, -40), dxfattribs={'layer': '轮廓线'})
    
    # Section 2: Thread relief groove (narrow depression)
    # From Ø50 to Ø46, width 3mm (Z=-40 to Z=-43)
    msp.add_line((25, 0, -40), (23, 0, -40), dxfattribs={'layer': '轮廓线'})  # Enter groove
    msp.add_line((23, 0, -40), (23, 0, -43), dxfattribs={'layer': '轮廓线'})  # Groove bottom
    msp.add_line((23, 0, -43), (25, 0, -43), dxfattribs={'layer': '轮廓线'})  # Exit groove
    
    # Section 3: Thread section - Ø30mm major diameter, 20mm long (Z=-43 to Z=-63)
    # For M30x1.5 thread: major=30mm, minor≈28.05mm (H=0.6495*P, H=0.974mm)
    # We represent the thread as a cylinder at minor diameter with annotation
    # In real CAD, threads are often shown schematically
    msp.add_line((15, 0, -43), (15, 0, -63), dxfattribs={'layer': '轮廓线'})
    
    # Add thread annotation (text) - using simple point placement
    # Note: In lathe DXF, Y coordinate represents Z position in the machining plane
    msp.add_text("M30x1.5", dxfattribs={
        'height': 2.0,
        'rotation': 0,
        'layer': '轮廓线',
        'insert': (-10, -53, 0)  # X=-10 (outside profile), Y=-53 (Z position), Z=0
    })
    
    # Centerline
    msp.add_line((0, 0, 5), (0, 0, -68), dxfattribs={'layer': '中心线', 'linetype': 'DASHDOT'})
    
    # Save
    doc.saveas(str(output_path))
    
    print(f"✓ Created shaft with thread DXF: {output_path}")
    print(f"  Entities: {len(msp)}")
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
    
    # Test 4: Shaft with thread (NEW!)
    thread_file = output_dir / "shaft_with_thread.dxf"
    create_shaft_with_thread(str(thread_file))
    
    print(f"\n✓ All test DXF files created in: {output_dir}")
    print(f"  - simple_shaft.dxf (stepped shaft)")
    print(f"  - tapered_shaft.dxf (with taper section)")
    print(f"  - shaft_with_groove.dxf (with groove)")
    print(f"  - shaft_with_thread.dxf (with M30x1.5 thread)")
