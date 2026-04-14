#!/usr/bin/env python3
"""
Minimal test - only Python stdlib required.
Demonstrates G-code generation without YAML/PyYAML.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

print("=" * 70)
print("CAD to G-code Platform - Minimal Test (No Dependencies)")
print("=" * 70)
print()

# Inline cutting rules (normally loaded from YAML)
CUTTING_RULES = {
    "45#钢": {
        "粗车": {"spindle_speed": 800, "feed_rate": 0.3, "depth_of_cut": 3.0, "cutting_speed": 200},
        "精车": {"spindle_speed": 1500, "feed_rate": 0.08, "depth_of_cut": 0.1, "cutting_speed": 250},
        "切槽": {"spindle_speed": 500, "feed_rate": 0.1, "depth_of_cut": 1.0, "cutting_speed": 100},
        "螺纹": {"spindle_speed": 400, "feed_rate": 1.5, "depth_of_cut": 0.2, "cutting_speed": 80},
    },
    "铝合金": {
        "粗车": {"spindle_speed": 2000, "feed_rate": 0.4, "depth_of_cut": 5.0, "cutting_speed": 400},
        "精车": {"spindle_speed": 3000, "feed_rate": 0.1, "depth_of_cut": 0.05, "cutting_speed": 500},
    },
    "不锈钢": {
        "粗车": {"spindle_speed": 600, "feed_rate": 0.2, "depth_of_cut": 2.0, "cutting_speed": 150},
        "精车": {"spindle_speed": 1200, "feed_rate": 0.06, "depth_of_cut": 0.1, "cutting_speed": 180},
    },
}


@dataclass
class CuttingParams:
    spindle_speed: int
    feed_rate: float
    depth_of_cut: float
    cutting_speed: int
    material: str = ""
    operation_type: str = ""
    
    def to_fanuc(self) -> str:
        return f"S{self.spindle_speed} M03 F{self.feed_rate}"


def get_params(material: str, operation: str) -> CuttingParams:
    """Get cutting parameters for material and operation."""
    mat_rules = CUTTING_RULES.get(material, CUTTING_RULES["45#钢"])
    op_rules = mat_rules.get(operation, mat_rules.get("粗车", {}))
    
    return CuttingParams(
        spindle_speed=op_rules.get("spindle_speed", 800),
        feed_rate=op_rules.get("feed_rate", 0.3),
        depth_of_cut=op_rules.get("depth_of_cut", 3.0),
        cutting_speed=op_rules.get("cutting_speed", 200),
        material=material,
        operation_type=operation,
    )


# Import G-code generator (only uses stdlib)
from cam.gcode_generator import GCodeGenerator, generate_simple_shaft

print("✅ G-code generator imported successfully")
print()

# Test 1: List materials
print("1️⃣  Supported materials:")
for mat in CUTTING_RULES.keys():
    ops = list(CUTTING_RULES[mat].keys())
    print(f"   • {mat}: {', '.join(ops)}")
print()

# Test 2: Get parameters
print("2️⃣  Cutting parameters for 45#钢 粗车:")
params = get_params("45#钢", "粗车")
print(f"   主轴转速：{params.spindle_speed} rpm")
print(f"   进给率：{params.feed_rate} mm/rev")
print(f"   切深：{params.depth_of_cut} mm")
print(f"   线速度：{params.cutting_speed} m/min")
print(f"   FANUC 代码：{params.to_fanuc()}")
print()

# Test 3: Generate G-code program
print("3️⃣  Generating G-code program...")
generator = GCodeGenerator("FANUC")

# Header
generator.generate_header("O0001", "Test Shaft - 45# Steel")

# Setup tool
generator.setup_tool(tool_number=1, spindle_speed=params.spindle_speed)

# Rapid to start position
generator.rapid_position(52.0, 2.0, "Approach stock")

# Rough turning cycle
generator.generate_rough_turning_cycle_fanuc(
    start_x=50.0,
    start_z=0.0,
    end_x=30.0,
    end_z=-100.0,
    depth_per_pass=params.depth_of_cut,
    finish_allowance=0.5,
    feed_rate=params.feed_rate
)

# Finish pass
finish_params = get_params("45#钢", "精车")
generator.setup_tool(tool_number=1, spindle_speed=finish_params.spindle_speed)
generator.generate_finish_pass(
    start_x=50.0,
    start_z=0.0,
    end_x=30.0,
    end_z=-100.0,
    feed_rate=finish_params.feed_rate
)

# Footer
generator.generate_footer()

gcode = generator.generate()
lines = gcode.split("\n")
print(f"   ✅ Generated {len(lines)} lines")
print()

# Test 4: Save to file
print("4️⃣  Saving to file...")
output_dir = project_root / "output"
output_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = output_dir / f"test_part_{timestamp}.nc"
output_file.write_text(gcode, encoding='utf-8')
print(f"   ✅ Saved to: {output_file}")
print()

# Display sample
print("=" * 70)
print("📄 G-code Preview (first 20 lines):")
print("=" * 70)
for line in lines[:20]:
    print(f"  {line}")

if len(lines) > 20:
    print(f"  ... ({len(lines) - 20} more lines)")

print()
print("=" * 70)
print("✅ TEST COMPLETE!")
print("=" * 70)
print()
print("📍 Full G-code file location:")
print(f"   {output_file.absolute()}")
print()
print("📍 To view full file:")
print(f"   cat {output_file}")
print()
print("📍 Next steps for full API:")
print("   1. Install dependencies:")
print("      source venv/bin/activate")
print("      pip install -e .")
print()
print("   2. Start API server:")
print("      uvicorn src.web.api:app --reload --host 0.0.0.0 --port 8000")
print()
print("   3. Access in browser:")
print("      http://localhost:8000/docs")
print()
