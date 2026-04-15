"""
G-code Generator Module

Generates CNC lathe G-code programs for FANUC, Siemens, and Mitsubishi systems.
"""

from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class GCodeBlock:
    """Represents a single G-code block."""
    line_number: int
    g_code: str
    comment: str = ""
    
    def __str__(self) -> str:
        if self.comment:
            return f"N{self.line_number:04d} {self.g_code} ; {self.comment}"
        return f"N{self.line_number:04d} {self.g_code}"


class GCodeGenerator:
    """
    G-code program generator for CNC lathes.
    
    Supports FANUC, Siemens, and Mitsubishi control systems.
    """
    
    def __init__(self, machine_system: str = "FANUC"):
        """
        Initialize G-code generator.
        
        Args:
            machine_system: Control system (FANUC, Siemens, Mitsubishi)
        """
        self.machine_system = machine_system
        self.blocks: List[GCodeBlock] = []
        self.line_counter = 1
        self.current_tool = None
        self.current_spindle_speed = 0
        self.current_feed_rate = 0
    
    def _add_block(self, g_code: str, comment: str = "") -> int:
        """Add a G-code block to the program."""
        block = GCodeBlock(
            line_number=self.line_counter,
            g_code=g_code,
            comment=comment
        )
        self.blocks.append(block)
        self.line_counter += 1
        return block.line_number
    
    def _get_comment_prefix(self) -> str:
        """Get comment prefix for the machine system."""
        if self.machine_system == "Siemens":
            return ";"
        return ";"  # FANUC and Mitsubishi also use semicolon
    
    def generate_header(self, program_name: str = "O0001", part_name: str = "") -> None:
        """
        Generate program header.
        
        Args:
            program_name: Program number/name
            part_name: Part description
        """
        self._add_block(f"{program_name}", f"Program: {part_name or program_name}")
        self._add_block("(DATE=" + datetime.now().strftime("%Y-%m-%d") + ")", "Date")
        self._add_block("(TIME=" + datetime.now().strftime("%H:%M:%S") + ")", "Time")
        self._add_block("(MACHINE=" + self.machine_system + ")", "Control system")
        self._add_block("", "")
        
        # Safety startup
        self._add_block("G21", "Metric units")
        self._add_block("G40 G97 G99", "Cancel compensation, constant RPM, feed per rev")
        self._add_block("G54", "Work coordinate system 1")
        self._add_block("T0100", "Cancel tool offset")
        self._add_block("M05", "Spindle stop")
        self._add_block("M09", "Coolant off")
    
    def generate_footer(self) -> None:
        """Generate program footer."""
        self._add_block("M05", "Spindle stop")
        self._add_block("M09", "Coolant off")
        self._add_block("G28 U0 W0", "Return to reference point")
        self._add_block("M30", "Program end")
    
    def get_gcode(self) -> str:
        """Get generated G-code as string."""
        return self.to_string()
    
    def to_string(self) -> str:
        """Convert all blocks to G-code string."""
        lines = []
        for block in self.blocks:
            line = str(block)
            if line.strip():
                lines.append(line)
        return '\n'.join(lines)
    
    def setup_tool(self, tool_number: int, spindle_speed: int, direction: str = "CW") -> None:
        """
        Setup tool and start spindle.
        
        Args:
            tool_number: Tool number (e.g., 1 for T0101)
            spindle_speed: Spindle speed in RPM
            direction: Rotation direction (CW or CCW)
        """
        m_code = "M03" if direction == "CW" else "M04"
        
        self._add_block(f"T{tool_number:02d}{tool_number:02d}", f"Select tool T{tool_number}")
        self._add_block(f"S{spindle_speed} {m_code}", f"Spindle {direction} {spindle_speed} RPM")
        self._add_block("M08", "Coolant on")
        self._add_block("G04 X2.0", "Dwell 2 seconds")
        
        self.current_tool = tool_number
        self.current_spindle_speed = spindle_speed
    
    def rapid_position(self, x: float, z: float, comment: str = "") -> None:
        """
        Rapid positioning.
        
        Args:
            x: X position (diameter value)
            z: Z position
            comment: Optional comment
        """
        self._add_block(f"G00 X{x:.3f} Z{z:.3f}", comment or f"Rapid to X{x} Z{z}")
    
    def linear_cut(self, x: float, z: float, feed_rate: float, comment: str = "") -> None:
        """
        Linear cutting move.
        
        Args:
            x: X position (diameter value)
            z: Z position
            feed_rate: Feed rate in mm/rev
            comment: Optional comment
        """
        if feed_rate != self.current_feed_rate:
            self._add_block(f"G01 X{x:.3f} Z{z:.3f} F{feed_rate:.3f}", 
                          comment or f"Cut to X{x} Z{z}")
            self.current_feed_rate = feed_rate
        else:
            self._add_block(f"G01 X{x:.3f} Z{z:.3f}", 
                          comment or f"Cut to X{x} Z{z}")
    
    def generate_rough_turning_cycle_fanuc(
        self,
        start_x: float,
        start_z: float,
        end_x: float,
        end_z: float,
        depth_per_pass: float,
        finish_allowance: float = 0.5,
        feed_rate: float = 0.3
    ) -> None:
        """
        Generate FANUC G71 rough turning cycle.
        
        Args:
            start_x: Starting X diameter
            start_z: Starting Z position
            end_x: Ending X diameter
            end_z: Ending Z position
            depth_per_pass: Depth of cut per pass (radius value)
            finish_allowance: Finish allowance (radius value)
            feed_rate: Feed rate
        """
        if self.machine_system != "FANUC":
            # Fall back to manual roughing for non-FANUC
            self._generate_manual_roughing(start_x, start_z, end_x, end_z, 
                                          depth_per_pass, feed_rate)
            return
        
        self._add_block("G71 U{} R{}".format(depth_per_pass, 1.0), 
                       f"Rough cycle - depth {depth_per_pass}mm, retract 1mm")
        self._add_block(f"G71 P{self.line_counter+2:04d} Q{self.line_counter+3:04d} "
                       f"U{finish_allowance*2:.3f} W{finish_allowance:.3f} F{feed_rate:.3f}",
                       "Rough cycle parameters")
        self._add_block(f"G00 X{start_x:.3f}", "Start position X")
        self._add_block(f"G01 Z{start_z:.3f}", "Start position Z")
        self._add_block(f"X{end_x:.3f} Z{end_z:.3f}", "Profile end")
    
    def _generate_manual_roughing(
        self,
        start_x: float,
        start_z: float,
        end_x: float,
        end_z: float,
        depth_per_pass: float,
        feed_rate: float
    ) -> None:
        """Generate manual roughing passes for non-FANUC systems."""
        current_x = start_x
        total_depth = abs(start_x - end_x) / 2  # Radius value
        
        pass_num = 0
        while current_x > end_x + 0.1:
            pass_num += 1
            current_x -= depth_per_pass * 2
            if current_x < end_x:
                current_x = end_x
            
            z_cut = start_z + (end_z - start_z) * (start_x - current_x) / (start_x - end_x)
            
            self.rapid_position(current_x + 2.0, start_z, f"Approach pass {pass_num}")
            self.linear_cut(current_x, z_cut, feed_rate, f"Rough pass {pass_num}")
        
        self._add_block("", f"Completed {pass_num} roughing passes")
    
    def generate_finish_pass(
        self,
        start_x: float,
        start_z: float,
        end_x: float,
        end_z: float,
        feed_rate: float = 0.08
    ) -> None:
        """
        Generate finish turning pass.
        
        Args:
            start_x: Starting X diameter
            start_z: Starting Z position
            end_x: Ending X diameter
            end_z: Ending Z position
            feed_rate: Feed rate for finishing
        """
        self.rapid_position(start_x - 2.0, start_z + 2.0, "Approach finish")
        self.linear_cut(start_x, start_z, feed_rate, "Start finish")
        self.linear_cut(end_x, end_z, feed_rate, "Finish profile")
    
    def generate_groove(
        self,
        groove_x: float,
        groove_z: float,
        groove_width: float,
        groove_depth: float,
        feed_rate: float = 0.1
    ) -> None:
        """
        Generate grooving operation.
        
        Args:
            groove_x: Groove bottom diameter
            groove_z: Groove Z position
            groove_width: Groove width
            groove_depth: Groove depth (radius value)
            feed_rate: Feed rate
        """
        start_x = groove_x + groove_depth * 2
        
        self.rapid_position(groove_z, start_x + 2.0, "Approach groove")
        
        # Plunge cuts for wide grooves
        num_plunges = max(1, int(groove_width / 3.0))
        plunge_width = groove_width / num_plunges
        
        for i in range(num_plunges):
            z_pos = groove_z + (i * plunge_width)
            self._add_block(f"G01 X{groove_x:.3f} Z{z_pos:.3f} F{feed_rate:.3f}", 
                          f"Plunge {i+1}/{num_plunges}")
            if i < num_plunges - 1:
                self._add_block(f"G01 X{start_x:.3f}", "Retract")
        
        self._add_block(f"G01 X{start_x:.3f}", "Final retract")
    
    def generate_thread(
        self,
        major_diameter: float,
        minor_diameter: float,
        pitch: float,
        thread_length: float,
        start_z: float = 0
    ) -> None:
        """
        Generate external threading.
        
        Args:
            major_diameter: Thread major diameter
            minor_diameter: Thread minor diameter
            pitch: Thread pitch
            thread_length: Thread length
            start_z: Starting Z position
        """
        if self.machine_system == "FANUC":
            # Use G76 threading cycle
            self._add_block(f"G76 P020060 Q100 R0.05", "Threading cycle params")
            self._add_block(f"G76 X{minor_diameter:.3f} Z{start_z - thread_length:.3f} "
                          f"P{int((major_diameter - minor_diameter)/2*1000):04d} "
                          f"Q100 F{pitch:.3f}",
                          f"Thread M{int(major_diameter)}x{pitch}")
        else:
            # Use G92 simple threading cycle
            depth = (major_diameter - minor_diameter) / 2
            num_passes = 8
            for i in range(num_passes):
                pass_depth = depth * (i + 1) / num_passes
                current_dia = major_diameter - pass_depth * 2
                self._add_block(f"G92 X{current_dia:.3f} Z{start_z - thread_length:.3f} "
                              f"F{pitch:.3f}", f"Thread pass {i+1}/{num_passes}")
    
    def change_coolant(self, on: bool = True) -> None:
        """Turn coolant on or off."""
        self._add_block("M08" if on else "M09", "Coolant " + ("on" if on else "off"))
    
    def stop_spindle(self) -> None:
        """Stop spindle rotation."""
        self._add_block("M05", "Spindle stop")
    
    def generate(self) -> str:
        """
        Generate complete G-code program string.
        
        Returns:
            Complete G-code program as string
        """
        lines = []
        for block in self.blocks:
            lines.append(str(block))
        return "\n".join(lines)
    
    def save_to_file(self, filepath: str) -> None:
        """
        Save G-code program to file.
        
        Args:
            filepath: Output file path
        """
        gcode = self.generate()
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(gcode, encoding='utf-8')
        print(f"✅ G-code saved to: {filepath}")
    
    def generate_test_program(self) -> str:
        """Generate a sample test program demonstrating all features."""
        self.generate_header("O0001", "Test Part - Shaft")
        
        # Operation 1: Rough turning
        self.setup_tool(tool_number=1, spindle_speed=800, direction="CW")
        self.rapid_position(52.0, 2.0, "Approach stock")
        self.generate_rough_turning_cycle_fanuc(
            start_x=50.0, start_z=0.0,
            end_x=30.0, end_z=-50.0,
            depth_per_pass=2.0,
            finish_allowance=0.5,
            feed_rate=0.3
        )
        
        # Operation 2: Finish turning
        self.setup_tool(tool_number=1, spindle_speed=1500, direction="CW")
        self.generate_finish_pass(
            start_x=50.0, start_z=0.0,
            end_x=30.0, end_z=-50.0,
            feed_rate=0.08
        )
        
        # Operation 3: Grooving
        self.setup_tool(tool_number=2, spindle_speed=500, direction="CW")
        self.generate_groove(
            groove_x=28.0, groove_z=-30.0,
            groove_width=3.0, groove_depth=1.0,
            feed_rate=0.1
        )
        
        # Operation 4: Threading
        self.setup_tool(tool_number=3, spindle_speed=400, direction="CW")
        self.generate_thread(
            major_diameter=30.0, minor_diameter=26.5,
            pitch=1.5, thread_length=20.0,
            start_z=-50.0
        )
        
        self.generate_footer()
        return self.generate()


# Convenience function
def generate_simple_shaft(
    start_diameter: float,
    end_diameter: float,
    length: float,
    material: str = "45#钢",
    machine_system: str = "FANUC"
) -> str:
    """
    Generate a simple shaft turning program.
    
    Args:
        start_diameter: Starting diameter
        end_diameter: Ending diameter
        length: Part length
        material: Material type
        machine_system: Control system
    
    Returns:
        G-code program string
    """
    from src.core.process_planning import CuttingRulesEngine
    
    engine = CuttingRulesEngine()
    
    # Get cutting parameters
    rough_params = engine.get_params(material, "粗车")
    finish_params = engine.get_params(material, "精车")
    
    generator = GCodeGenerator(machine_system)
    
    # Header
    generator.generate_header("O0001", f"Shaft {start_diameter}x{length}")
    
    # Rough turning
    generator.setup_tool(1, rough_params.spindle_speed)
    generator.rapid_position(start_diameter + 2.0, 2.0)
    generator.generate_rough_turning_cycle_fanuc(
        start_x=start_diameter, start_z=0.0,
        end_x=end_diameter, end_z=-length,
        depth_per_pass=rough_params.depth_of_cut,
        feed_rate=rough_params.feed_rate
    )
    
    # Finish turning
    generator.setup_tool(1, finish_params.spindle_speed)
    generator.generate_finish_pass(
        start_x=start_diameter, start_z=0.0,
        end_x=end_diameter, end_z=-length,
        feed_rate=finish_params.feed_rate
    )
    
    # Footer
    generator.generate_footer()
    
    return generator.generate()


if __name__ == "__main__":
    # Test G-code generation
    print("=" * 60)
    print("G-code Generator Test")
    print("=" * 60)
    
    generator = GCodeGenerator("FANUC")
    gcode = generator.generate_test_program()
    
    print("\nGenerated G-code:\n")
    print(gcode)
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
