#!/usr/bin/env python3
"""Re-test the 5 files that had encoding issues (now fixed)."""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from wrapi import WRAPIClient

# Files that were fixed
FIXED_FILES = [
    "EPASWMM Example Files/SWMM5_NCIMM/675_H&H_Elements.inp",
    "EPASWMM Example Files/SWMM5_NCIMM/Dummy_Polygon_for_Subcatchments.inp",
    "EPASWMM Example Files/SWMM5_NCIMM/lakes.inp",
    "EPASWMM Example Files/SWMM5_NCIMM/riverhills.inp",
    "EPASWMM Example Files/SWMM5_NCIMM/seepage.inp",
]

API_URL = os.getenv("WRAPI_URL", "https://wrm-dev.neer.ai")

def test_file(client, file_path):
    """Test a single file."""
    file = Path(file_path)
    if not file.exists():
        return {"file": file_path, "status": "not_found", "error": "File does not exist"}
    
    print(f"Testing: {file.name}...")
    
    try:
        label = f"Encoding Fix Test - {file.stem}"
        response = client.run_simulation_from_file(str(file), "swmm", label)
        
        if not response:
            return {"file": file_path, "status": "submit_failed", "error": "No response"}
        
        sim_id = response.get("id")
        print(f"  ✅ Submitted: {sim_id}")
        
        # Poll for completion
        start_time = time.time()
        while time.time() - start_time < 600:  # 10 min timeout
            sim = client.get_simulation(sim_id)
            if not sim:
                return {"file": file_path, "status": "error", "error": "Could not get status"}
            
            status = sim.get("status")
            if status == "completed":
                print(f"  ✅ Completed")
                return {"file": file_path, "status": "completed", "simulation_id": sim_id}
            elif status == "failed":
                print(f"  ❌ Failed")
                return {"file": file_path, "status": "failed", "simulation_id": sim_id}
            
            time.sleep(5)
        
        return {"file": file_path, "status": "timeout", "error": "Timeout after 10 minutes"}
        
    except Exception as e:
        return {"file": file_path, "status": "error", "error": str(e)}

def main():
    print("=" * 70)
    print("Testing Fixed Encoding Files")
    print("=" * 70)
    
    client = WRAPIClient(api_url=API_URL)
    
    if not client.health_check():
        print("❌ API health check failed!")
        return
    
    print(f"\nTesting {len(FIXED_FILES)} files with fixed encoding...\n")
    
    results = []
    for file_path in FIXED_FILES:
        result = test_file(client, file_path)
        results.append(result)
        time.sleep(2)  # Small delay between submissions
    
    # Summary
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    completed = [r for r in results if r.get("status") == "completed"]
    failed = [r for r in results if r.get("status") in ["failed", "error", "timeout", "submit_failed"]]
    
    print(f"\n✅ Completed: {len(completed)}")
    print(f"❌ Failed: {len(failed)}")
    
    if failed:
        print(f"\nFailed files:")
        for r in failed:
            print(f"  - {Path(r['file']).name}: {r.get('status')} - {r.get('error', '')}")
    
    if completed:
        print(f"\n✅ {len(completed)} files are now working after encoding fix!")

if __name__ == "__main__":
    main()
