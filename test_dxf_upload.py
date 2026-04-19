#!/usr/bin/env python3
"""
Test script for DXF upload and feature recognition
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print(f"✓ Health check passed: {json.dumps(response.json(), indent=2)}")
        return True
    else:
        print(f"✗ Health check failed: {response.status_code}")
        return False

def test_dxf_upload():
    """Test DXF upload endpoint"""
    print("\nTesting /gcode/upload-dxf endpoint...")
    
    # Test with simple_shaft.dxf
    dxf_path = "tests/test_dxf_files/simple_shaft.dxf"
    
    try:
        with open(dxf_path, 'rb') as f:
            files = {'file': ('simple_shaft.dxf', f, 'application/dxf')}
            data = {
                'material': '45#钢',
                'machine_system': 'FANUC'
            }
            
            print(f"Uploading {dxf_path}...")
            response = requests.post(f"{BASE_URL}/gcode/upload-dxf", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ DXF upload successful!")
                print(f"  Features count: {result.get('features_count', 0)}")
                print(f"  G-code lines: {result.get('gcode_lines', 0)}")
                print(f"  Program name: {result.get('program_name', 'N/A')}")
                
                # Print recognized features
                if 'features' in result:
                    print(f"\nRecognized features:")
                    for i, feat in enumerate(result['features'][:5]):
                        print(f"  {i+1}. {feat.get('type', 'N/A')} - {feat.get('parameters', {})}")
                
                return True
            else:
                print(f"✗ DXF upload failed: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("DXF Upload and Feature Recognition Test")
    print("=" * 60)
    
    # Test health first
    if not test_health():
        print("\nServer is not healthy. Exiting...")
        exit(1)
    
    # Test DXF upload
    test_dxf_upload()
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
