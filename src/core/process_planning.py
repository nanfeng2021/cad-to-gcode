"""
CAD to G-code Platform - Core Module

Core process planning and cutting parameter calculation.
Follows Hermes Agent engineering patterns.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)


class MaterialType(str, Enum):
    """Common machining material types."""
    STEEL_45 = "45#钢"
    STEEL_40CR = "40Cr"
    STAINLESS = "不锈钢"
    ALUMINUM = "铝合金"
    BRASS = "黄铜"
    CAST_STEEL = "铸钢"
    CAST_IRON = "铸铁"


class OperationType(str, Enum):
    """Machining operation types."""
    ROUGH_TURNING = "粗车"
    FINISH_TURNING = "精车"
    GROOVING = "切槽"
    THREADING = "螺纹"
    FACING = "端面"
    BORING = "镗孔"
    PARTING = "切断"


class MachineSystem(str, Enum):
    """Supported CNC machine control systems."""
    FANUC = "FANUC"
    SIEMENS = "Siemens"
    MITSUBISHI = "Mitsubishi"
    GSK = "GSK"
    HNC = "HNC"


@dataclass
class CuttingParams:
    """Cutting parameters for a machining operation."""
    spindle_speed: int  # n (rpm)
    feed_rate: float    # f (mm/rev or mm/min)
    depth_of_cut: float  # ap (mm)
    cutting_speed: Optional[int] = None  # v_c (m/min)
    radial_engagement: Optional[float] = None  # ae
    operation_type: str = ""
    material: str = ""
    
    def to_fanuc(self, rapid: bool = False) -> str:
        """Generate FANUC-style G-code parameters."""
        g_code = "G00" if rapid else "G01"
        return f"{g_code} S{self.spindle_speed} M03\n{g_code} F{self.feed_rate}"
    
    def to_siemens(self) -> str:
        """Generate Siemens-style G-code parameters."""
        return f"S{self.spindle_speed} M03\nF{self.feed_rate}"
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate cutting parameters against safe ranges."""
        warnings = []
        
        if self.spindle_speed < 100:
            warnings.append(f"Spindle speed too low: {self.spindle_speed} rpm")
        elif self.spindle_speed > 10000:
            warnings.append(f"Spindle speed too high: {self.spindle_speed} rpm")
        
        if self.feed_rate < 0.01:
            warnings.append(f"Feed rate too low: {self.feed_rate} mm/rev")
        elif self.feed_rate > 2.0:
            warnings.append(f"Feed rate too high: {self.feed_rate} mm/rev")
        
        if self.depth_of_cut < 0.01:
            warnings.append(f"Depth of cut too low: {self.depth_of_cut} mm")
        elif self.depth_of_cut > 10.0:
            warnings.append(f"Depth of cut too high: {self.depth_of_cut} mm")
        
        return len(warnings) == 0, warnings


@dataclass
class ToolDefinition:
    """Tool definition from database."""
    tool_id: str
    name: str
    tool_type: str
    model: str
    insert_material: str
    compatible_materials: List[str]
    applications: List[str]
    cutting_params: Dict[str, Dict]
    machine_compatibility: List[str]
    notes: str = ""


class CuttingRulesEngine:
    """
    Cutting parameter rules engine.
    
    Loads rules from YAML configuration file (like Hermes config).
    Provides parameter lookup and calculation methods.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the cutting rules engine.
        
        Args:
            config_path: Path to cutting_rules.yaml. 
                        Defaults to config/cutting_rules.yaml
        """
        self.rules: Dict = {}
        self.tools: Dict = {}
        self.machine_systems: Dict = {}
        
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "cutting_rules.yaml"
        
        self.config_path = config_path
        self._load_config()
    
    def _load_config(self):
        """Load cutting rules from YAML configuration."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            self._load_default_rules()
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.rules = config.get('materials', {})
            self.tools = config.get('tools', {})
            self.machine_systems = config.get('machine_systems', {})
            
            logger.info(f"Loaded cutting rules from {self.config_path}")
            logger.info(f"  Materials: {len(self.rules)}")
            logger.info(f"  Machine systems: {len(self.machine_systems)}")
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._load_default_rules()
    
    def _load_default_rules(self):
        """Load built-in default cutting rules."""
        self.rules = {
            "45#钢": {
                "code": "STEEL_45",
                "operations": {
                    "rough_turning": {"v_c": 200, "n": 800, "f": 0.3, "ap": 3.0},
                    "finish_turning": {"v_c": 200, "n": 1500, "f": 0.08, "ap": 0.1},
                }
            },
            "40Cr": {
                "code": "STEEL_40CR",
                "operations": {
                    "rough_turning": {"v_c": 180, "n": 700, "f": 0.25, "ap": 2.5},
                    "finish_turning": {"v_c": 180, "n": 1400, "f": 0.08, "ap": 0.1},
                }
            },
            "不锈钢": {
                "code": "STAINLESS",
                "operations": {
                    "rough_turning": {"v_c": 150, "n": 600, "f": 0.2, "ap": 2.0},
                    "finish_turning": {"v_c": 150, "n": 1200, "f": 0.06, "ap": 0.1},
                }
            },
            "铝合金": {
                "code": "ALUMINUM",
                "operations": {
                    "rough_turning": {"v_c": 300, "n": 1500, "f": 0.4, "ap": 3.0},
                    "finish_turning": {"v_c": 300, "n": 2500, "f": 0.1, "ap": 0.05},
                }
            },
        }
    
    def get_params(
        self, 
        material: str, 
        operation: str,
        tool_diameter: Optional[float] = None
    ) -> CuttingParams:
        """
        Get cutting parameters based on material and operation.
        
        Args:
            material: Material type (e.g., "45#钢", "铝合金")
            operation: Operation type (e.g., "粗车", "精车")
            tool_diameter: Tool diameter in mm (optional, for speed calculation)
        
        Returns:
            CuttingParams object with calculated parameters
        """
        # Normalize operation name
        op_map = {
            "粗车": "rough_turning",
            "精车": "finish_turning",
            "切槽": "grooving",
            "螺纹": "threading",
            "端面": "facing",
            "镗孔": "boring",
        }
        op_key = op_map.get(operation, operation)
        
        # Look up material rules
        if material not in self.rules:
            logger.warning(f"Material '{material}' not found, using default (45#钢)")
            material = "45#钢"
        
        material_rules = self.rules[material]
        operations = material_rules.get('operations', {})
        
        if op_key not in operations:
            logger.warning(f"Operation '{operation}' not found for {material}, using rough_turning")
            op_key = "rough_turning"
        
        params = operations[op_key]
        
        # Calculate spindle speed from cutting speed if diameter provided
        spindle_speed = params.get('n')
        if tool_diameter and params.get('v_c'):
            spindle_speed = self.calculate_spindle_speed(params['v_c'], tool_diameter)
        
        return CuttingParams(
            spindle_speed=spindle_speed,
            feed_rate=params.get('f', 0.3),
            depth_of_cut=params.get('ap', 3.0),
            cutting_speed=params.get('v_c'),
            radial_engagement=params.get('ae'),
            operation_type=operation,
            material=material
        )
    
    def calculate_spindle_speed(self, cutting_speed: int, diameter: float) -> int:
        """
        Calculate spindle speed from cutting speed and diameter.
        
        Formula: n = (1000 × v_c) / (π × D)
        
        Args:
            cutting_speed: Cutting speed in m/min
            diameter: Workpiece/tool diameter in mm
        
        Returns:
            Spindle speed in rpm (rounded to integer)
        """
        import math
        if diameter <= 0:
            raise ValueError("Diameter must be positive")
        
        n = (1000 * cutting_speed) / (math.pi * diameter)
        return int(round(n))
    
    def get_machine_codes(self, system: MachineSystem) -> Dict:
        """
        Get M-code and G-code definitions for a machine system.
        
        Args:
            system: Machine control system (FANUC, Siemens, etc.)
        
        Returns:
            Dictionary of machine codes
        """
        if system.value not in self.machine_systems:
            logger.warning(f"Machine system '{system.value}' not found, using FANUC defaults")
            return self.machine_systems.get('FANUC', {})
        
        return self.machine_systems[system.value]
    
    def get_tool_recommendation(
        self, 
        operation: str, 
        material: str
    ) -> Optional[ToolDefinition]:
        """
        Get recommended tool for an operation and material.
        
        Args:
            operation: Operation type
            material: Material to machine
        
        Returns:
            ToolDefinition or None if no match found
        """
        # Map operations to tool types
        op_to_tool = {
            "rough_turning": "external_turning",
            "finish_turning": "external_turning",
            "boring": "internal_boring",
            "grooving": "grooving",
            "threading": "threading",
        }
        
        tool_type = op_to_tool.get(operation)
        if not tool_type or tool_type not in self.tools:
            return None
        
        # Return first matching tool (could be enhanced with scoring)
        tools_list = self.tools[tool_type].get('types', [])
        if tools_list:
            tool_data = tools_list[0]
            return ToolDefinition(
                tool_id=f"TOOL_{tool_type.upper()}_001",
                name=tool_data.get('name', ''),
                tool_type=tool_type,
                model=tool_data.get('insert_shape', ''),
                insert_material="Carbide",
                compatible_materials=tool_data.get('materials', []),
                applications=tool_data.get('applications', []),
                cutting_params={},
                machine_compatibility=["FANUC", "Siemens"],
                notes=tool_data.get('notes', '')
            )
        
        return None
    
    def list_materials(self) -> List[str]:
        """List all available materials in the database."""
        return list(self.rules.keys())
    
    def list_operations(self, material: str) -> List[str]:
        """List available operations for a material."""
        if material not in self.rules:
            return []
        
        ops = self.rules[material].get('operations', {})
        return list(ops.keys())


# Convenience function (Hermes-style module API)
def get_cutting_params(material: str, operation: str) -> CuttingParams:
    """
    Quick access to cutting parameters.
    
    Args:
        material: Material type
        operation: Operation type
    
    Returns:
        CuttingParams object
    """
    engine = CuttingRulesEngine()
    return engine.get_params(material, operation)


# Example usage (like Hermes module tests)
if __name__ == "__main__":
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )
    
    print("=" * 60)
    print("CAD to G-code - Cutting Rules Engine Test")
    print("=" * 60)
    
    engine = CuttingRulesEngine()
    
    # Test parameter lookup
    print("\n1. Testing parameter lookup:")
    test_cases = [
        ("45#钢", "粗车"),
        ("45#钢", "精车"),
        ("铝合金", "粗车"),
        ("不锈钢", "精车"),
    ]
    
    for material, operation in test_cases:
        params = engine.get_params(material, operation)
        print(f"\n  {material} - {operation}:")
        print(f"    转速：{params.spindle_speed} rpm")
        print(f"    进给：{params.feed_rate} mm/rev")
        print(f"    切深：{params.depth_of_cut} mm")
        print(f"    FANUC: {params.to_fanuc()}")
        
        # Validate
        valid, warnings = params.validate()
        if warnings:
            print(f"    ⚠️  Warnings: {warnings}")
    
    # Test machine codes
    print("\n2. Testing machine codes:")
    fanuc_codes = engine.get_machine_codes(MachineSystem.FANUC)
    print(f"  FANUC M-codes:")
    for code, value in fanuc_codes.get('m_codes', {}).items():
        print(f"    {code}: {value}")
    
    # Test material listing
    print("\n3. Available materials:")
    for mat in engine.list_materials():
        print(f"  - {mat}")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
