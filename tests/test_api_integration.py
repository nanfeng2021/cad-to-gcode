#!/usr/bin/env python3
"""
CAD to G-code Platform - API Integration Test

Tests the complete workflow:
1. Generate G-code
2. List programs
3. Get program details
4. Download program
5. Delete program
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_api():
    """Run all API tests."""
    print("=" * 60)
    print("CAD to G-code Platform - API Integration Test")
    print("=" * 60)
    
    # Test 1: Health check
    print("\n[1/6] Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200, f"Health check failed: {response.text}"
    health = response.json()
    print(f"✓ API Status: {health['status']}")
    print(f"  Version: {health['version']}")
    print(f"  Materials: {health['materials_count']}")
    print(f"  Programs in DB: {health['programs_count']}")
    
    # Test 2: Generate G-code (should auto-save to DB)
    print("\n[2/6] Generating G-code for a test shaft...")
    gen_request = {
        "start_diameter": 50.0,
        "end_diameter": 30.0,
        "length": 100.0,
        "material": "45#钢",
        "machine_system": "FANUC"
    }
    response = requests.post(
        f"{BASE_URL}/gcode/generate",
        json=gen_request
    )
    assert response.status_code == 200, f"G-code generation failed: {response.text}"
    gen_result = response.json()
    print(f"✓ Generated program: {gen_result['program_name']}")
    print(f"  Lines: {gen_result['lines']}")
    print(f"  Generated at: {gen_result['generated_at']}")
    
    # Test 3: List programs
    print("\n[3/6] Listing saved programs...")
    response = requests.get(f"{BASE_URL}/programs")
    assert response.status_code == 200, f"List programs failed: {response.text}"
    programs = response.json()
    print(f"✓ Found {len(programs)} program(s) in database")
    
    if len(programs) > 0:
        # Get the first program ID for subsequent tests
        program_id = programs[0]['id']
        print(f"  Latest program ID: {program_id}")
        print(f"  Filename: {programs[0]['filename']}")
        print(f"  Material: {programs[0]['material']}")
        
        # Test 4: Get program details
        print(f"\n[4/6] Getting program details for ID {program_id}...")
        response = requests.get(f"{BASE_URL}/programs/{program_id}")
        assert response.status_code == 200, f"Get program failed: {response.text}"
        program_detail = response.json()
        print(f"✓ Program details retrieved:")
        print(f"  Content length: {len(program_detail['content'])} chars")
        print(f"  Operations: {len(program_detail['operations'])}")
        print(f"  Metadata: {json.dumps(program_detail['metadata'], indent=2)}")
        
        # Test 5: Download program
        print(f"\n[5/6] Downloading program {program_id}...")
        response = requests.get(f"{BASE_URL}/programs/{program_id}/download")
        assert response.status_code == 200, f"Download failed: {response.text}"
        content = response.text
        filename = response.headers.get('Content-Disposition', '').split('filename=')[-1].strip('"')
        print(f"✓ Downloaded: {filename}")
        print(f"  Content preview (first 200 chars):")
        print("  " + "\n  ".join(content.split("\n")[:5]))
        
        # Save downloaded file
        output_dir = Path("/mnt/g/projects/cad-to-gcode/output/test_downloads")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / filename
        output_file.write_text(content)
        print(f"  Saved to: {output_file}")
        
        # Test 6: Delete program
        print(f"\n[6/6] Deleting program {program_id}...")
        response = requests.delete(f"{BASE_URL}/programs/{program_id}")
        assert response.status_code == 200, f"Delete failed: {response.text}"
        delete_result = response.json()
        print(f"✓ {delete_result['message']}")
        
        # Verify deletion
        response = requests.get(f"{BASE_URL}/programs")
        programs_after = response.json()
        print(f"  Programs remaining: {len(programs_after)}")
    
    print("\n" + "=" * 60)
    print("✓ All tests passed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_api()
    except requests.exceptions.ConnectionError as e:
        print(f"\n✗ Connection error: {e}")
        print("  Make sure the API server is running:")
        print("  cd /mnt/g/projects/cad-to-gcode")
        print("  python -m src.web.api")
        exit(1)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        exit(1)
