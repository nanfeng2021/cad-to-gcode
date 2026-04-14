"""
Unit tests for G-code generator module.
"""

import pytest
from pathlib import Path
import sys
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cam.gcode_generator import (
    GCodeGenerator,
    GCodeBlock,
    generate_simple_shaft,
)


class TestGCodeBlock:
    """Test GCodeBlock dataclass."""
    
    def test_create_block(self):
        """Test creating a G-code block."""
        block = GCodeBlock(
            line_number=10,
            g_code="G00 X50.0 Z2.0",
            comment="Rapid position"
        )
        
        assert block.line_number == 10
        assert block.g_code == "G00 X50.0 Z2.0"
        assert block.comment == "Rapid position"
    
    def test_block_with_comment(self):
        """Test string representation with comment."""
        block = GCodeBlock(
            line_number=5,
            g_code="M03",
            comment="Spindle on"
        )
        
        str_repr = str(block)
        assert "N0005" in str_repr
        assert "M03" in str_repr
        assert "Spindle on" in str_repr
    
    def test_block_without_comment(self):
        """Test string representation without comment."""
        block = GCodeBlock(
            line_number=100,
            g_code="G01 X30.0 F0.3"
        )
        
        str_repr = str(block)
        assert "N0100" in str_repr
        assert "G01" in str_repr
        assert ";" not in str_repr  # No semicolon if no comment


class TestGCodeGenerator:
    """Test GCodeGenerator class."""
    
    @pytest.fixture
    def generator(self):
        """Create generator instance."""
        return GCodeGenerator("FANUC")
    
    def test_init(self, generator):
        """Test generator initialization."""
        assert generator.machine_system == "FANUC"
        assert len(generator.blocks) == 0
        assert generator.line_counter == 1
    
    def test_generate_header(self, generator):
        """Test program header generation."""
        generator.generate_header("O0001", "Test Part")
        
        assert len(generator.blocks) > 0
        
        # Check for safety codes
        gcode = generator.generate()
        assert "G21" in gcode  # Metric units
        assert "G54" in gcode  # Work coordinate system
        assert "M05" in gcode  # Spindle stop
    
    def test_generate_footer(self, generator):
        """Test program footer generation."""
        generator.generate_footer()
        
        gcode = generator.generate()
        assert "M05" in gcode  # Spindle stop
        assert "M09" in gcode  # Coolant off
        assert "G28" in gcode  # Return to reference
        assert "M30" in gcode  # Program end
    
    def test_setup_tool(self, generator):
        """Test tool setup."""
        generator.setup_tool(tool_number=1, spindle_speed=800)
        
        gcode = generator.generate()
        assert "T0101" in gcode  # Tool selection
        assert "S800" in gcode   # Spindle speed
        assert "M03" in gcode    # Spindle CW
        assert "M08" in gcode    # Coolant on
    
    def test_rapid_position(self, generator):
        """Test rapid positioning."""
        generator.rapid_position(50.0, 2.0, "Approach")
        
        gcode = generator.generate()
        assert "G00" in gcode
        assert "X50.000" in gcode or "X50.0" in gcode
        assert "Z2.000" in gcode or "Z2.0" in gcode
    
    def test_linear_cut(self, generator):
        """Test linear cutting move."""
        generator.linear_cut(30.0, -50.0, feed_rate=0.3, comment="Cut")
        
        gcode = generator.generate()
        assert "G01" in gcode
        assert "F0.3" in gcode
    
    def test_generate_test_program(self, generator):
        """Test complete test program generation."""
        gcode = generator.generate_test_program()
        
        lines = gcode.split("\n")
        assert len(lines) > 10  # Should have multiple lines
        
        # Check structure
        assert lines[0].startswith("N0001")  # Program start
        assert "M30" in gcode  # Program end
    
    def test_save_to_file(self, generator):
        """Test saving G-code to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.nc"
            
            generator.generate_test_program()
            generator.save_to_file(str(filepath))
            
            assert filepath.exists()
            content = filepath.read_text()
            assert "M30" in content
    
    def test_groove_generation(self, generator):
        """Test grooving operation."""
        generator.setup_tool(2, 500)
        generator.generate_groove(
            groove_x=28.0,
            groove_z=-30.0,
            groove_width=3.0,
            groove_depth=1.0
        )
        
        gcode = generator.generate()
        assert "G01" in gcode
        assert "X28.0" in gcode or "X28.000" in gcode


class TestGenerateSimpleShaft:
    """Test generate_simple_shaft function."""
    
    def test_basic_generation(self):
        """Test basic shaft generation."""
        gcode = generate_simple_shaft(
            start_diameter=50.0,
            end_diameter=30.0,
            length=100.0,
            material="45#钢",
            machine_system="FANUC"
        )
        
        assert isinstance(gcode, str)
        assert len(gcode) > 100
        assert "G21" in gcode  # Metric
        assert "M30" in gcode  # End
    
    def test_different_materials(self):
        """Test generation with different materials."""
        materials = ["45#钢", "铝合金", "不锈钢"]
        
        for material in materials:
            gcode = generate_simple_shaft(
                start_diameter=50.0,
                end_diameter=30.0,
                length=50.0,
                material=material
            )
            
            assert len(gcode) > 100
    
    def test_different_systems(self):
        """Test generation for different machine systems."""
        systems = ["FANUC", "Siemens", "Mitsubishi"]
        
        for system in systems:
            gcode = generate_simple_shaft(
                start_diameter=40.0,
                end_diameter=25.0,
                length=80.0,
                machine_system=system
            )
            
            assert "M30" in gcode or "M02" in gcode  # Program end


class TestMachineSystemSpecifics:
    """Test machine system specific features."""
    
    def test_fanuc_g71_cycle(self):
        """Test FANUC G71 roughing cycle."""
        generator = GCodeGenerator("FANUC")
        generator.generate_header()
        generator.setup_tool(1, 800)
        
        generator.generate_rough_turning_cycle_fanuc(
            start_x=50.0,
            start_z=0.0,
            end_x=30.0,
            end_z=-50.0,
            depth_per_pass=2.0
        )
        
        gcode = generator.generate()
        assert "G71" in gcode
    
    def test_non_fanuc_manual_roughing(self):
        """Test manual roughing for non-FANUC systems."""
        generator = GCodeGenerator("Siemens")
        generator.generate_header()
        generator.setup_tool(1, 800)
        
        generator._generate_manual_roughing(
            start_x=50.0,
            start_z=0.0,
            end_x=30.0,
            end_z=-50.0,
            depth_per_pass=2.0,
            feed_rate=0.3
        )
        
        gcode = generator.generate()
        assert "G01" in gcode  # Linear cuts
        assert "G71" not in gcode  # No G71 for Siemens
    
    def test_threading_fanuc_g76(self):
        """Test FANUC G76 threading cycle."""
        generator = GCodeGenerator("FANUC")
        generator.generate_header()
        generator.setup_tool(3, 400)
        
        generator.generate_thread(
            major_diameter=30.0,
            minor_diameter=26.5,
            pitch=1.5,
            thread_length=20.0
        )
        
        gcode = generator.generate()
        assert "G76" in gcode


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
