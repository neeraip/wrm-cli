#!/usr/bin/env python3
"""
Analyze runtimes for ALL 813 SWMM files by running simulations.
This will take significant time but provides complete statistics.
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent))
from wrapi import WRAPIClient

DEFAULT_API_URL = "https://wrm.neer.ai"
MAX_WORKERS = 10  # Lower to avoid rate limits
POLL_INTERVAL = 5
TIMEOUT = 600


def find_all_swmm_files() -> List[Path]:
    """Find all SWMM input files in the repository."""
    repo_root = Path(__file__).parent
    swmm_dir = repo_root / "EPASWMM Example Files"
    
    inp_files = list(swmm_dir.rglob("*.inp"))
    return sorted(inp_files)


def submit_simulation(client: WRAPIClient, input_file: Path) -> Dict:
    """Submit a single simulation."""
    result = {
        "file": str(input_file.relative_to(Path(__file__).parent)),
        "simulation_id": None,
        "status": "pending",
        "error": None
    }
    
    try:
        label = f"Runtime Analysis - {input_file.stem}"
        response = client.run_simulation_from_file(str(input_file), "swmm", label)
        
        if response:
            result["simulation_id"] = response.get("id")
            result["status"] = "submitted"
        else:
            result["status"] = "submit_failed"
            result["error"] = "No response from API"
    except Exception as e:
        result["status"] = "submit_failed"
        result["error"] = str(e)
    
    return result


def poll_simulation(client: WRAPIClient, sim_id: str) -> tuple:
    """Poll until simulation completes. Returns (status, execution_time)."""
    start_time = time.time()
    
    while time.time() - start_time < TIMEOUT:
        try:
            sim = client.get_simulation(sim_id)
            if not sim:
                return ("error", None)
            
            status = sim.get("status", "unknown")
            
            if status in ["completed", "failed"]:
                # Calculate execution time
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
            
        except Exception as e:
            return ("error", None)
    
    return ("timeout", None)


def analyze_all_files():
    """Run simulations for all SWMM files and analyze runtimes."""
    print("=" * 70)
    print("Complete SWMM Runtime Analysis")
    print("=" * 70)
    
    api_url = os.getenv("WRAPI_URL", DEFAULT_API_URL)
    client = WRAPIClient(api_url=api_url)
    
    if not client.health_check():
        print("❌ API health check failed!")
        return
    
    # Find all SWMM files
    print("\n📂 Finding all SWMM input files...")
    inp_files = find_all_swmm_files()
    total_files = len(inp_files)
    print(f"   Found {total_files} SWMM input files")
    
    if total_files == 0:
        print("❌ No SWMM files found!")
        return
    
    # Check for existing results
    results_file = Path(__file__).parent / "all_swmm_runtime_results.json"
    existing_results = {}
    if results_file.exists():
        existing_data = json.load(open(results_file))
        existing_results = {r['file']: r for r in existing_data.get('results', []) 
                           if r.get('final_status') == 'completed' and r.get('execution_time')}
        print(f"   Found {len(existing_results)} existing completed results")
    
    # Filter out already completed
    files_to_test = [f for f in inp_files 
                     if str(f.relative_to(Path(__file__).parent)) not in existing_results]
    
    if not files_to_test:
        print("\n✅ All files already analyzed!")
        all_results = list(existing_results.values())
    else:
        print(f"\n🚀 Submitting {len(files_to_test)} simulations (max {MAX_WORKERS} parallel)...")
        
        results = []
        submission_start = time.time()
        
        # Submit all simulations
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_file = {
                executor.submit(submit_simulation, client, inp_file): inp_file
                for inp_file in files_to_test
            }
            
            for future in as_completed(future_to_file):
                inp_file = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                    if result["status"] == "submitted":
                        print(f"   ✅ Submitted: {inp_file.name}")
                except Exception as e:
                    print(f"   ❌ Exception: {inp_file.name} - {e}")
        
        submission_time = time.time() - submission_start
        print(f"\n⏱️  Submission completed in {submission_time:.1f} seconds")
        
        # Poll for completion
        submitted = [r for r in results if r.get("simulation_id")]
        print(f"\n⏳ Polling {len(submitted)} simulations for completion...")
        
        polling_start = time.time()
        completed_count = 0
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_result = {
                executor.submit(poll_simulation, client, r["simulation_id"]): r
                for r in submitted
            }
            
            for future in as_completed(future_to_result):
                result = future_to_result[future]
                try:
                    final_status, exec_time = future.result()
                    result["final_status"] = final_status
                    result["execution_time"] = exec_time
                    completed_count += 1
                    
                    if completed_count % 10 == 0:
                        print(f"   Progress: {completed_count}/{len(submitted)} completed...")
                except Exception as e:
                    result["final_status"] = "poll_error"
                    result["error"] = str(e)
        
        polling_time = time.time() - polling_start
        total_time = time.time() - submission_start
        
        # Combine with existing results
        all_results = list(existing_results.values()) + [
            r for r in results if r.get("final_status") == "completed" and r.get("execution_time")
        ]
        
        # Save results
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_files': total_files,
                'completed': len(all_results),
                'results': results + list(existing_results.values())
            }, f, indent=2)
        
        print(f"\n⏱️  Total time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    
    # Analyze results
    if not all_results:
        print("\n❌ No completed simulations found!")
        return
    
    times = [r['execution_time'] for r in all_results]
    min_time = min(times)
    max_time = max(times)
    avg_time = sum(times) / len(times)
    median_time = sorted(times)[len(times) // 2]
    
    print("\n" + "=" * 70)
    print("COMPLETE RUNTIME STATISTICS")
    print("=" * 70)
    print(f"\nTotal simulations analyzed: {len(all_results)}")
    print(f"Total files in repository: {total_files}")
    print(f"Coverage: {len(all_results)/total_files*100:.1f}%")
    
    print(f"\n⏱️  Execution Times:")
    print(f"   Minimum:  {min_time:.3f} seconds ({min_time:.2f} minutes)")
    print(f"   Maximum:  {max_time:.3f} seconds ({max_time/60:.2f} minutes)")
    print(f"   Average:  {avg_time:.3f} seconds ({avg_time/60:.2f} minutes)")
    print(f"   Median:   {median_time:.3f} seconds ({median_time/60:.2f} minutes)")
    
    # Save summary
    summary_file = Path(__file__).parent / "all_swmm_runtime_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_files': total_files,
            'analyzed': len(all_results),
            'coverage_percent': len(all_results)/total_files*100,
            'statistics': {
                'min_seconds': min_time,
                'max_seconds': max_time,
                'avg_seconds': avg_time,
                'median_seconds': median_time,
                'min_minutes': min_time / 60,
                'max_minutes': max_time / 60,
                'avg_minutes': avg_time / 60,
                'median_minutes': median_time / 60
            }
        }, f, indent=2)
    
    print(f"\n📄 Summary saved to: {summary_file}")


if __name__ == "__main__":
    print("⚠️  WARNING: This will run simulations for ALL 813 SWMM files!")
    print("   This may take several hours and use API resources.")
    print("   Press Ctrl+C to cancel, or wait 5 seconds to continue...")
    
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        sys.exit(0)
    
    analyze_all_files()
