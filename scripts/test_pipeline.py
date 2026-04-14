#!/usr/bin/env python3
"""
End-to-End Test: DXF → Parse → Feature Recognition → G-code

Tests the complete pipeline from CAD file to machinable G-code.
"""

import sys
import json
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from ai.dxf_parser import parse_dxf, DXFParser
from ai.feature_recognition import recognize_features
from cam.gcode_generator import GCodeGenerator


def test_dxf_to_gcode(dxf_file: str):
    """
    Test complete pipeline: DXF → Features → G-code
    
    Args:
        dxf_file: Path to DXF file
    """
    print("=" * 70)
    print(f"Testing: {dxf_file}")
    print("=" * 70)
    
    # Step 1: Parse DXF
    print("\n[Step 1/3] Parsing DXF file...")
    try:
        geometry_dict = parse_dxf(dxf_file)
        print(f"✓ Parsed successfully")
        print(f"  Format: {geometry_dict['metadata']['format']}")
        print(f"  Version: {geometry_dict['metadata']['version']}")
        print(f"  Units: {geometry_dict['metadata']['units']}")
        print(f"  Entities:")
        print(f"    - Lines: {geometry_dict['summary']['line_count']}")
        print(f"    - Circles: {geometry_dict['summary']['circle_count']}")
        print(f"    - Arcs: {geometry_dict['summary']['arc_count']}")
        print(f"    - Polylines: {geometry_dict['summary']['polyline_count']}")
    except Exception as e:
        print(f"✗ Parse failed: {e}")
        return None
    
    # Step 2: Recognize features
    print("\n[Step 2/3] Recognizing machining features...")
    try:
        # Need to reconstruct objects from dict for feature recognition
        parser = DXFParser()
        geometry = parser.parse_file(dxf_file)
        
        feature_tree = recognize_features(geometry)
        
        print(f"✓ Recognized {feature_tree['feature_count']} features")
        
        for feat in feature_tree['features']:
            feat_type = feat['type']
            feat_id = feat['id']
            
            if feat_type == 'external_cylinder':
                dia = feat['parameters']['diameter']
                length = feat['parameters']['length']
                print(f"  [{feat_id}] 外圆: Ø{dia}mm × {length}mm")
            elif feat_type == 'taper':
                start_dia = feat['parameters']['start_diameter']
                end_dia = feat['parameters']['end_diameter']
                length = feat['parameters']['length']
                taper = feat['parameters']['taper_ratio']
                print(f"  [{feat_id}] 锥度: Ø{start_dia}→{end_dia}mm (锥度:{taper})")
            elif feat_type == 'arc_surface':
                radius = feat['parameters']['radius']
                sweep = feat['parameters']['sweep_angle']
                print(f"  [{feat_id}] 圆弧面: R{radius}mm ({sweep}°)")
            elif feat_type == 'groove':
                width = feat['parameters']['width']
                depth = feat['parameters']['depth']
                pos_z = feat['parameters']['position_z']
                print(f"  [{feat_id}] 切槽: 宽{width}mm × 深{depth}mm @ Z{pos_z}")
        
    except Exception as e:
        print(f"✗ Feature recognition failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Step 3: Generate G-code (simplified for now)
    print("\n[Step 3/3] Generating G-code program...")
    try:
        # For now, generate a simple shaft based on the largest diameter
        max_diameter = 0
        total_length = 0
        
        for feat in feature_tree['features']:
            if feat['type'] == 'external_cylinder':
                dia = feat['parameters']['diameter']
                if dia > max_diameter:
                    max_diameter = dia
                length = feat['parameters']['length']
                if length > total_length:
                    total_length = length
        
        if max_diameter == 0:
            max_diameter = 50  # Default
        if total_length == 0:
            total_length = 100  # Default
        
        # Use existing G-code generator with simple shaft turning
        generator = GCodeGenerator(machine_system="FANUC")
        
        # Generate header
        part_name = Path(dxf_file).stem
        generator.generate_header(program_name="O9999", part_name=part_name)
        
        # Safety startup (inline)
        generator._add_block("G21", "Metric units")
        generator._add_block("G40 G97 G99", "Cancel compensation, constant RPM, feed per rev")
        generator._add_block("G00 X0 Z5", "Rapid to start position")
        
        # Facing operation
        generator._add_block("T0101 M06", "Face tool")
        generator._add_block("S800 M03", "Spindle on CW")
        generator._add_block("G00 X55 Z0 M08", "Rapid to facing start")
        generator._add_block("G01 X-2 F0.2", "Face to center")
        generator._add_block("G00 X55 Z2", "Retract")
        
        # Rough turning using G71 cycle
        stock_diameter = max_diameter + 5
        generator._add_block("T0202 M06", "Rough turning tool")
        generator._add_block(f"G00 X{stock_diameter} Z2", "Rapid to cycle start")
        generator._add_block("G71 U2.0 R0.5", "Rough cycle - depth of cut 2mm")
        generator._add_block(f"G71 P10 Q20 U0.5 W0.2 F0.3", f"Rough cycle - finish allowance 0.5mm")
        generator._add_block("N10 G00 X0", "Start of profile")
        generator._add_block(f"N15 G01 X{max_diameter} Z-{total_length} F0.2", "Turn to final diameter")
        generator._add_block("N20 G01 X55", "End of profile")
        
        # Finish turning
        generator._add_block("T0303 M06", "Finish turning tool")
        generator._add_block("S1200 M03", "Higher speed for finish")
        generator._add_block(f"G00 X{max_diameter} Z2", "Rapid to finish start")
        generator._add_block(f"G70 P10 Q20 F0.1", "Finish cycle")
        generator._add_block("G00 X100 Z100", "Rapid to change position")
        
        # Program end (footer)
        generator.generate_footer()
        
        # Get G-code using the correct method name
        gcode = generator.generate()
        lines = gcode.split('\n')
        
        print(f"✓ Generated {len(lines)} lines of G-code")
        print(f"\n--- G-code Preview (first 20 lines) ---")
        for line in lines[:20]:
            print(line)
        if len(lines) > 20:
            print(f"... ({len(lines) - 20} more lines)")
        print("--- End Preview ---\n")
        
        # Save G-code
        output_file = Path(dxf_file).with_suffix('.nc')
        output_file.write_text(gcode)
        print(f"✓ Saved G-code to: {output_file}")
        
        return {
            'success': True,
            'dxf_file': str(dxf_file),
            'feature_count': feature_tree['feature_count'],
            'features': feature_tree['features'],
            'gcode_lines': len(lines),
            'output_file': str(output_file)
        }
        
    except Exception as e:
        print(f"✗ G-code generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_pipeline.py <dxf_file>")
        print("\nTest files available:")
        print("  tests/test_dxf_files/simple_shaft.dxf")
        print("  tests/test_dxf_files/tapered_shaft.dxf")
        print("  tests/test_dxf_files/shaft_with_groove.dxf")
        sys.exit(1)
    
    dxf_file = sys.argv[1]
    result = test_dxf_to_gcode(dxf_file)
    
    if result and result['success']:
        print("\n" + "=" * 70)
        print("✓ Pipeline test PASSED")
        print("=" * 70)
        print(f"\nSummary:")
        print(f"  Input: {result['dxf_file']}")
        print(f"  Features recognized: {result['feature_count']}")
        print(f"  G-code generated: {result['gcode_lines']} lines")
        print(f"  Output: {result['output_file']}")
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("✗ Pipeline test FAILED")
        print("=" * 70)
        sys.exit(1)
