"""
Test DXF File Generator for CAD to G-code Platform

Generates simple shaft part DXF files for testing the parsing and feature recognition pipeline.
"""

from pathlib import Path
import ezdxf
from ezdxf import units


def create_simple_shaft_dxf(output_path: str, 
                            diameters: list = None,
                            lengths: list = None,
                            include_arc: bool = True,
                            include_taper: bool = True) -> str:
    """
    Create a simple shaft part DXF file for testing.
    
    The shaft is drawn in the XZ plane (X = radius, Z = length).
    Only the upper half profile is drawn (Y = 0).
    
    Args:
        output_path: Output file path
        diameters: List of diameters at each step (mm). Default: [50, 40, 30, 20]
        lengths: List of cumulative Z positions (mm). Default: [0, 30, 60, 100]
        include_arc: Include a fillet arc between steps
        include_taper: Include a tapered section
        
    Returns:
        Path to created DXF file
    """
    # Default dimensions for a simple stepped shaft
    if diameters is None:
        diameters = [50, 40, 30, 20]  # mm
    if lengths is None:
        lengths = [0, 30, 60, 100]  # mm (cumulative from right end)
    
    output_path = Path(output_path)
    
    # Create new DXF document
    doc = ezdxf.new(dxfversion='R2010')
    doc.units = units.MM
    
    # Set header variables
    doc.header['$INSUNITS'] = 4  # Millimeters
    doc.header['$MEASUREMENT'] = 1  # Metric
    
    # Get modelspace
    msp = doc.modelspace()
    
    # Add layers
    doc.layers.add('轮廓线', color=7)  # White
    doc.layers.add('中心线', color=1)  # Red
    doc.layers.add('标注', color=3)    # Green
    
    # Draw the shaft profile (upper half only, in XZ plane)
    # Starting from right end (Z=0) to left end (Z=-total_length)
    
    points = []
    current_z = 0
    
    for i, (dia, next_z) in enumerate(zip(diameters, lengths[1:])):
        radius = dia / 2
        z_position = -next_z  # Negative Z for lathe convention
        
        # Add point at current diameter
        points.append((radius, 0, current_z))  # Start of this section
        points.append((radius, 0, z_position))  # End of this section
        
        current_z = z_position
    
    # Draw lines connecting the points
    for i in range(len(points) - 1):
        start = points[i]
        end = points[i + 1]
        
        # Check if this should be a taper or straight
        if include_taper and i % 2 == 0 and abs(start[0] - end[0]) > 0.5:
            # This is a tapered section - draw inclined line
            msp.add_line(start, end, dxfattribs={'layer': '轮廓线'})
        else:
            # Straight cylindrical section - draw vertical line
            msp.add_line(start, end, dxfattribs={'layer': '轮廓线'})
        
        # Add arc/fillet between sections if requested
        if include_arc and i < len(points) - 2:
            # Add a small fillet at the corner
            corner = end
            next_point = points[i + 2]
            
            # Calculate fillet (simple quarter circle)
            fillet_radius = 2.0  # mm
            
            if abs(corner[0] - next_point[0]) > fillet_radius:
                # Create arc at the corner
                arc_center = (corner[0] - fillet_radius, 0, corner[2])
                
                # Add arc (90 degrees)
                arc = msp.add_arc(
                    center=arc_center,
                    radius=fillet_radius,
                    start_angle=0,
                    end_angle=90,
                    dxfattribs={'layer': '轮廓线'}
                )
    
    # Add centerline (along Z axis)
    total_length = lengths[-1]
    msp.add_line(
        (0, 0, 5),  # Slightly beyond right end
        (0, 0, -total_length - 5),  # Slightly beyond left end
        dxfattribs={'layer': '中心线', 'linetype': 'DASHDOT'}
    )
    
    # Add some dimension-like circles (to simulate dimension markers)
    for dia in diameters[:3]:  # Add circles for first few diameters
        radius = dia / 2 + 5  # Offset from part
        msp.add_circle((0, 0, 0), radius, dxfattribs={'layer': '标注'})
    
    # Save DXF file
    doc.saveas(str(output_path))
    
    print(f"✓ Created test DXF: {output_path}")
    print(f"  Diameters: {diameters} mm")
    print(f"  Lengths: {lengths[1:]} mm")
    print(f"  Total length: {lengths[-1]} mm")
    print(f"  Entities: {len(msp)}")
    
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
    create_simple_shaft_dxf(
        str(shaft_file),
        diameters=[50, 40, 30, 20],
        lengths=[0, 30, 60, 100],
        include_arc=True,
        include_taper=False
    )
    
    # Test 2: Shaft with taper
    taper_file = output_dir / "tapered_shaft.dxf"
    create_simple_shaft_dxf(
        str(taper_file),
        diameters=[50, 35, 25, 20],
        lengths=[0, 40, 70, 100],
        include_arc=False,
        include_taper=True
    )
    
    # Test 3: Shaft with groove
    groove_file = output_dir / "shaft_with_groove.dxf"
    create_shaft_with_groove(str(groove_file))
    
    print(f"\n✓ All test DXF files created in: {output_dir}")
    print(f"  - simple_shaft.dxf")
    print(f"  - tapered_shaft.dxf")
    print(f"  - shaft_with_groove.dxf")
