"""
Unit tests for process planning module.
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.process_planning import (
    CuttingRulesEngine,
    CuttingParams,
    MaterialType,
    OperationType,
    MachineSystem,
)


class TestCuttingParams:
    """Test CuttingParams dataclass."""
    
    def test_create_params(self):
        """Test creating cutting parameters."""
        params = CuttingParams(
            spindle_speed=800,
            feed_rate=0.3,
            depth_of_cut=3.0,
            cutting_speed=200,
        )
        
        assert params.spindle_speed == 800
        assert params.feed_rate == 0.3
        assert params.depth_of_cut == 3.0
        assert params.cutting_speed == 200
    
    def test_to_fanuc(self):
        """Test FANUC code generation."""
        params = CuttingParams(
            spindle_speed=1500,
            feed_rate=0.08,
            depth_of_cut=0.1,
        )
        
        fanuc_code = params.to_fanuc()
        assert "S1500" in fanuc_code
        assert "F0.08" in fanuc_code
        assert "M03" in fanuc_code
    
    def test_validate_valid_params(self):
        """Test validation with valid parameters."""
        params = CuttingParams(
            spindle_speed=800,
            feed_rate=0.3,
            depth_of_cut=3.0,
        )
        
        valid, warnings = params.validate()
        assert valid is True
        assert len(warnings) == 0
    
    def test_validate_invalid_params(self):
        """Test validation with invalid parameters."""
        params = CuttingParams(
            spindle_speed=50,  # Too low
            feed_rate=3.0,     # Too high
            depth_of_cut=0.005, # Too low
        )
        
        valid, warnings = params.validate()
        assert valid is False
        assert len(warnings) > 0


class TestCuttingRulesEngine:
    """Test CuttingRulesEngine class."""
    
    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return CuttingRulesEngine()
    
    def test_init(self, engine):
        """Test engine initialization."""
        assert engine.rules is not None
        assert len(engine.rules) > 0
    
    def test_get_params_45_steel_rough(self, engine):
        """Test getting parameters for 45# steel roughing."""
        params = engine.get_params("45#钢", "粗车")
        
        assert params.spindle_speed == 800
        assert params.feed_rate == 0.3
        assert params.depth_of_cut == 3.0
        assert params.cutting_speed == 200
    
    def test_get_params_aluminum_finish(self, engine):
        """Test getting parameters for aluminum finishing."""
        params = engine.get_params("铝合金", "精车")
        
        assert params.spindle_speed == 2500
        assert params.feed_rate == 0.1
        assert params.depth_of_cut == 0.05
    
    def test_get_params_unknown_material(self, engine):
        """Test handling of unknown material."""
        params = engine.get_params("Unknown Material", "粗车")
        
        # Should fall back to 45# steel
        assert params.material == "45#钢"
        assert params.spindle_speed == 800
    
    def test_calculate_spindle_speed(self, engine):
        """Test spindle speed calculation."""
        # n = (1000 × v_c) / (π × D)
        # For v_c = 200 m/min, D = 50 mm
        # n = (1000 × 200) / (π × 50) ≈ 1273 rpm
        
        n = engine.calculate_spindle_speed(200, 50)
        assert 1270 <= n <= 1276  # Allow small rounding difference
    
    def test_calculate_spindle_speed_invalid_diameter(self, engine):
        """Test spindle speed calculation with invalid diameter."""
        with pytest.raises(ValueError):
            engine.calculate_spindle_speed(200, 0)
        
        with pytest.raises(ValueError):
            engine.calculate_spindle_speed(200, -10)
    
    def test_get_machine_codes_fanuc(self, engine):
        """Test getting FANUC machine codes."""
        codes = engine.get_machine_codes(MachineSystem.FANUC)
        
        assert "m_codes" in codes or codes.get("FANUC", {}).get("m_codes")
    
    def test_list_materials(self, engine):
        """Test listing available materials."""
        materials = engine.list_materials()
        
        assert len(materials) > 0
        assert "45#钢" in materials
        assert "铝合金" in materials
    
    def test_list_operations(self, engine):
        """Test listing operations for a material."""
        ops = engine.list_operations("45#钢")
        
        assert len(ops) > 0
        assert "rough_turning" in ops or "粗车" in ops


class TestMaterialTypes:
    """Test MaterialType enum."""
    
    def test_material_type_values(self):
        """Test material type string values."""
        assert MaterialType.STEEL_45.value == "45#钢"
        assert MaterialType.ALUMINUM.value == "铝合金"
        assert MaterialType.STAINLESS.value == "不锈钢"


class TestOperationTypes:
    """Test OperationType enum."""
    
    def test_operation_type_values(self):
        """Test operation type string values."""
        assert OperationType.ROUGH_TURNING.value == "粗车"
        assert OperationType.FINISH_TURNING.value == "精车"
        assert OperationType.GROOVING.value == "切槽"
        assert OperationType.THREADING.value == "螺纹"


class TestMachineSystems:
    """Test MachineSystem enum."""
    
    def test_machine_system_values(self):
        """Test machine system string values."""
        assert MachineSystem.FANUC.value == "FANUC"
        assert MachineSystem.SIEMENS.value == "Siemens"
        assert MachineSystem.MITSUBISHI.value == "Mitsubishi"


class TestIntegration:
    """Integration tests."""
    
    def test_full_workflow(self):
        """Test complete workflow from material to G-code."""
        engine = CuttingRulesEngine()
        
        # Get cutting parameters
        params = engine.get_params("45#钢", "粗车")
        
        # Validate
        valid, warnings = params.validate()
        assert valid is True
        
        # Generate FANUC code
        fanuc_code = params.to_fanuc()
        assert "S800" in fanuc_code
        assert "F0.3" in fanuc_code
        
        # Get machine codes
        codes = engine.get_machine_codes(MachineSystem.FANUC)
        assert codes is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
