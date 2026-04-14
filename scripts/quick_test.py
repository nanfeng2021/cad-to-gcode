#!/usr/bin/env python3
"""
Quick test script - no external dependencies required.
Tests core modules without FastAPI/uvicorn.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

print("=" * 70)
print("CAD to G-code Platform - Quick Test")
print("=" * 70)
print()

# Test 1: Import core modules
print("1️⃣  Testing core module imports...")
try:
    from core.process_planning import CuttingRulesEngine, CuttingParams
    print("   ✅ process_planning module loaded")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 2: Load cutting rules
print("\n2️⃣  Testing cutting rules engine...")
try:
    engine = CuttingRulesEngine()
    materials = engine.list_materials()
    print(f"   ✅ Engine initialized with {len(materials)} materials")
    print(f"   Materials: {', '.join(materials[:5])}...")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 3: Get cutting parameters
print("\n3️⃣  Testing parameter calculation...")
try:
    params = engine.get_params("45#钢", "粗车")
    print(f"   ✅ 45#钢 粗车参数:")
    print(f"      - 主轴转速：{params.spindle_speed} rpm")
    print(f"      - 进给率：{params.feed_rate} mm/rev")
    print(f"      - 切深：{params.depth_of_cut} mm")
    print(f"      - 线速度：{params.cutting_speed} m/min")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 4: Generate FANUC code
print("\n4️⃣  Testing FANUC code generation...")
try:
    fanuc = params.to_fanuc()
    print(f"   ✅ FANUC 代码：{fanuc}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 5: Import G-code generator
print("\n5️⃣  Testing G-code generator...")
try:
    from cam.gcode_generator import GCodeGenerator
    generator = GCodeGenerator("FANUC")
    print("   ✅ G-code generator initialized")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 6: Generate complete program
print("\n6️⃣  Generating complete G-code program...")
try:
    generator.generate_header("O0001", "Test Shaft")
    generator.setup_tool(tool_number=1, spindle_speed=800)
    generator.rapid_position(52.0, 2.0, "Approach")
    generator.linear_cut(50.0, 0.0, feed_rate=0.3, comment="Start cut")
    generator.linear_cut(30.0, -50.0, feed_rate=0.3, comment="Profile")
    generator.generate_footer()
    
    gcode = generator.generate()
    lines = gcode.split("\n")
    print(f"   ✅ Generated {len(lines)} lines of G-code")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 7: Save to file
print("\n7️⃣  Saving G-code to file...")
try:
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "test_part.nc"
    output_file.write_text(gcode, encoding='utf-8')
    print(f"   ✅ Saved to: {output_file.absolute()}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Display sample G-code
print("\n" + "=" * 70)
print("📄 Sample G-code (first 15 lines):")
print("=" * 70)
for i, line in enumerate(lines[:15], 1):
    print(f"  {line}")

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print()
print("📍 Next steps:")
print("   1. View full G-code: cat output/test_part.nc")
print("   2. Install dependencies: pip install -e .")
print("   3. Start API server: uvicorn src.web.api:app --reload")
print("   4. Access docs: http://localhost:8000/docs")
print()
