#!/usr/bin/env python3
"""
Sample CAD file processor for testing.
Generates a simple STEP file and processes it.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cam.gcode_generator import GCodeGenerator, generate_simple_shaft
from src.core.process_planning import CuttingRulesEngine


def test_gcode_generation():
    """Test G-code generation with different materials."""
    print("=" * 70)
    print("CAD to G-code Platform - Test Suite")
    print("=" * 70)
    
    engine = CuttingRulesEngine()
    
    # Test cases
    test_cases = [
        {
            "name": "45#钢 - 轴类零件",
            "start_dia": 50.0,
            "end_dia": 30.0,
            "length": 100.0,
            "material": "45#钢",
        },
        {
            "name": "铝合金 - 轻量轴",
            "start_dia": 60.0,
            "end_dia": 40.0,
            "length": 80.0,
            "material": "铝合金",
        },
        {
            "name": "不锈钢 - 耐腐蚀轴",
            "start_dia": 45.0,
            "end_dia": 35.0,
            "length": 120.0,
            "material": "不锈钢",
        },
    ]
    
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] Testing: {case['name']}")
        print("-" * 70)
        
        # Get cutting parameters
        rough_params = engine.get_params(case["material"], "粗车")
        finish_params = engine.get_params(case["material"], "精车")
        
        print(f"  Material: {case['material']}")
        print(f"  Dimensions: Φ{case['start_dia']} × {case['length']} mm")
        print(f"  Roughing: S{rough_params.spindle_speed} F{rough_params.feed_rate} ap={rough_params.depth_of_cut}")
        print(f"  Finishing: S{finish_params.spindle_speed} F{finish_params.feed_rate} ap={finish_params.depth_of_cut}")
        
        # Generate G-code
        gcode = generate_simple_shaft(
            start_diameter=case["start_dia"],
            end_diameter=case["end_dia"],
            length=case["length"],
            material=case["material"],
            machine_system="FANUC"
        )
        
        # Save to file
        output_file = output_dir / f"test_part_{i}.nc"
        output_file.write_text(gcode, encoding='utf-8')
        
        print(f"  ✅ Generated: {output_file}")
        print(f"  📊 Lines: {len(gcode.splitlines())}")
    
    print("\n" + "=" * 70)
    print("Test complete! Check the 'output' directory for generated files.")
    print("=" * 70)


def test_api_endpoints():
    """Test API endpoints using httpx."""
    try:
        import httpx
    except ImportError:
        print("⚠️  httpx not installed. Install with: pip install httpx")
        return
    
    print("\n" + "=" * 70)
    print("API Endpoint Tests")
    print("=" * 70)
    
    base_url = "http://localhost:8000"
    
    with httpx.Client() as client:
        # Test health endpoint
        print("\n1. Testing /health endpoint...")
        response = client.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        # Test materials endpoint
        print("\n2. Testing /materials endpoint...")
        response = client.get(f"{base_url}/materials")
        print(f"   Status: {response.status_code}")
        materials = response.json()
        print(f"   Materials count: {len(materials)}")
        for mat in materials[:3]:
            print(f"     - {mat['name']}: {mat['operations']}")
        
        # Test cutting params endpoint
        print("\n3. Testing /cutting-params endpoint...")
        response = client.post(
            f"{base_url}/cutting-params",
            json={"material": "45#钢", "operation": "粗车"}
        )
        print(f"   Status: {response.status_code}")
        params = response.json()
        print(f"   Spindle: {params['spindle_speed']} rpm")
        print(f"   Feed: {params['feed_rate']} mm/rev")
        print(f"   Depth: {params['depth_of_cut']} mm")
        
        # Test G-code generation endpoint
        print("\n4. Testing /gcode/generate endpoint...")
        response = client.post(
            f"{base_url}/gcode/generate",
            json={
                "start_diameter": 50,
                "end_diameter": 30,
                "length": 100,
                "material": "45#钢",
                "machine_system": "FANUC"
            }
        )
        print(f"   Status: {response.status_code}")
        result = response.json()
        print(f"   Program: {result['program_name']}")
        print(f"   Lines: {result['lines']}")
        print(f"   Generated: {result['generated_at']}")
    
    print("\n" + "=" * 70)
    print("API tests complete!")
    print("=" * 70)


if __name__ == "__main__":
    # Run G-code generation tests
    test_gcode_generation()
    
    # Ask if user wants to run API tests
    print("\n🤔 Run API endpoint tests? (requires server running)")
    response = input("Enter 'y' to test API endpoints: ").strip().lower()
    
    if response == 'y':
        test_api_endpoints()
    else:
        print("Skipping API tests. Start server with: uvicorn src.web.api:app --reload")
