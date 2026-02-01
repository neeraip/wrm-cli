#!/usr/bin/env python3
"""
Stress Test Script for NEER WRM API
Runs multiple EPANET simulations in parallel and tracks timing.
"""

import os
import sys
import time
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from wrapi import WRAPIClient

# Configuration
API_URL = "https://wrm-dev.neer.ai"  # Use dev server
EPANET_DIR = Path(__file__).parent / "EPANET Example Files" / "collect-epanet-inp"
NUM_SIMULATIONS = 50
MAX_WORKERS = 20  # Parallel threads for submission
POLL_INTERVAL = 5  # Seconds between status checks


def get_input_files(directory: Path, limit: int) -> List[Path]:
    """Get the first N .inp files from directory."""
    files = sorted(directory.glob("*.inp"))
    return files[:limit]


def submit_simulation(client: WRAPIClient, input_file: Path) -> Dict:
    """Submit a single simulation and return result with timing."""
    result = {
        "file": input_file.name,
        "simulation_id": None,
        "submit_time": None,
        "submit_duration": None,
        "status": "pending",
        "error": None
    }
    
    start_time = time.time()
    try:
        label = f"Stress Test - {input_file.stem}"
        response = client.run_simulation_from_file(str(input_file), "epanet", label)
        
        if response:
            result["simulation_id"] = response.get("id")
            result["status"] = "submitted"
            result["submit_time"] = datetime.now().isoformat()
        else:
            result["status"] = "submit_failed"
            result["error"] = "No response from API"
    except Exception as e:
        result["status"] = "submit_failed"
        result["error"] = str(e)
    
    result["submit_duration"] = time.time() - start_time
    return result


def poll_simulation_status(client: WRAPIClient, sim_id: str) -> Tuple[str, float]:
    """Poll until simulation completes. Returns (final_status, execution_time)."""
    start_time = time.time()
    
    while True:
        try:
            sim = client.get_simulation(sim_id)
            if not sim:
                return ("error", time.time() - start_time)
            
            status = sim.get("status", "unknown")
            
            if status in ["completed", "failed"]:
                # Calculate actual execution time from timestamps if available
                if sim.get("started_at") and sim.get("completed_at"):
                    try:
                        started = datetime.fromisoformat(sim["started_at"].replace("Z", "+00:00"))
                        completed = datetime.fromisoformat(sim["completed_at"].replace("Z", "+00:00"))
                        exec_time = (completed - started).total_seconds()
                        return (status, exec_time)
                    except:
                        pass
                return (status, time.time() - start_time)
            
            time.sleep(POLL_INTERVAL)
            
            # Timeout after 10 minutes
            if time.time() - start_time > 600:
                return ("timeout", time.time() - start_time)
                
        except Exception as e:
            return ("error", time.time() - start_time)


def run_stress_test():
    """Run the stress test."""
    print("=" * 70)
    print("🚀 NEER WRM API Stress Test")
    print("=" * 70)
    
    # Initialize client with dev URL
    client = WRAPIClient(api_url=API_URL)
    
    # Check API health
    print("\n📡 Checking API health...")
    if client.health_check():
        print("   ✅ API is healthy")
    else:
        print("   ⚠️  API may be unavailable, proceeding anyway...")
    
    # Get input files
    print(f"\n📁 Finding EPANET input files...")
    input_files = get_input_files(EPANET_DIR, NUM_SIMULATIONS)
    print(f"   Found {len(input_files)} files to process")
    
    if not input_files:
        print("❌ No input files found!")
        sys.exit(1)
    
    # Phase 1: Submit all simulations in parallel
    print(f"\n🚀 Phase 1: Submitting {len(input_files)} simulations (max {MAX_WORKERS} parallel)...")
    print("-" * 70)
    
    submissions = []
    overall_start = time.time()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(submit_simulation, client, f): f 
            for f in input_files
        }
        
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            submissions.append(result)
            
            status_icon = "✅" if result["status"] == "submitted" else "❌"
            print(f"   [{i:3}/{len(input_files)}] {status_icon} {result['file'][:40]:<40} "
                  f"({result['submit_duration']:.2f}s)")
    
    submit_time = time.time() - overall_start
    successful_submissions = [s for s in submissions if s["status"] == "submitted"]
    
    print(f"\n   📊 Submission Summary:")
    print(f"      Total files: {len(input_files)}")
    print(f"      Successful:  {len(successful_submissions)}")
    print(f"      Failed:      {len(input_files) - len(successful_submissions)}")
    print(f"      Total time:  {submit_time:.2f}s")
    print(f"      Avg per sim: {submit_time/len(input_files):.2f}s")
    
    # Phase 2: Wait for all simulations to complete
    if successful_submissions:
        print(f"\n⏳ Phase 2: Waiting for {len(successful_submissions)} simulations to complete...")
        print("-" * 70)
        
        poll_start = time.time()
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(poll_simulation_status, client, s["simulation_id"]): s 
                for s in successful_submissions
            }
            
            completed_count = 0
            for future in as_completed(futures):
                submission = futures[future]
                status, exec_time = future.result()
                
                submission["final_status"] = status
                submission["execution_time"] = exec_time
                
                completed_count += 1
                status_icon = "✅" if status == "completed" else "❌"
                print(f"   [{completed_count:3}/{len(successful_submissions)}] {status_icon} "
                      f"{submission['file'][:40]:<40} {status:<12} ({exec_time:.2f}s)")
        
        poll_time = time.time() - poll_start
    
    # Final Summary
    total_time = time.time() - overall_start
    
    print("\n" + "=" * 70)
    print("📊 STRESS TEST RESULTS")
    print("=" * 70)
    
    completed = [s for s in submissions if s.get("final_status") == "completed"]
    failed = [s for s in submissions if s.get("final_status") == "failed"]
    errors = [s for s in submissions if s.get("final_status") in ["error", "timeout", None]]
    
    print(f"\n📈 Overall Statistics:")
    print(f"   Total Simulations:    {len(input_files)}")
    print(f"   Completed:            {len(completed)}")
    print(f"   Failed:               {len(failed)}")
    print(f"   Errors/Timeouts:      {len(errors)}")
    print(f"   Success Rate:         {len(completed)/len(input_files)*100:.1f}%")
    
    print(f"\n⏱️  Timing:")
    print(f"   Total Wall Time:      {total_time:.2f}s ({total_time/60:.1f} min)")
    print(f"   Submission Phase:     {submit_time:.2f}s")
    if successful_submissions:
        print(f"   Execution Phase:      {poll_time:.2f}s")
    
    if completed:
        exec_times = [s["execution_time"] for s in completed if s.get("execution_time")]
        if exec_times:
            print(f"\n📊 Execution Times (completed simulations):")
            print(f"   Min:                  {min(exec_times):.2f}s")
            print(f"   Max:                  {max(exec_times):.2f}s")
            print(f"   Average:              {sum(exec_times)/len(exec_times):.2f}s")
            print(f"   Total (sequential):   {sum(exec_times):.2f}s")
            print(f"   Speedup (parallel):   {sum(exec_times)/total_time:.1f}x")
    
    # Detailed results table
    print(f"\n📋 Detailed Results:")
    print("-" * 90)
    print(f"{'File':<45} {'Status':<12} {'Submit(s)':<10} {'Exec(s)':<10}")
    print("-" * 90)
    
    for s in sorted(submissions, key=lambda x: x["file"]):
        file_name = s["file"][:44]
        status = s.get("final_status", s["status"])
        submit_dur = f"{s['submit_duration']:.2f}" if s.get("submit_duration") else "-"
        exec_dur = f"{s['execution_time']:.2f}" if s.get("execution_time") else "-"
        print(f"{file_name:<45} {status:<12} {submit_dur:<10} {exec_dur:<10}")
    
    # Save results to JSON
    results_file = Path(__file__).parent / "stress_test_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_simulations": len(input_files),
            "completed": len(completed),
            "failed": len(failed),
            "errors": len(errors),
            "total_time_seconds": total_time,
            "submissions": submissions
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    print("=" * 70)
    
    return submissions


if __name__ == "__main__":
    run_stress_test()
