#!/usr/bin/env python3
"""
Test newly added SWMM files via API simulations.
Runs simulations in parallel to verify they work correctly.
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
DEFAULT_API_URL = "https://wrm-dev.neer.ai"
MAX_WORKERS = 10  # Lower concurrency to avoid AWS rate limits
POLL_INTERVAL = 5  # Seconds between status checks
TIMEOUT = 600  # 10 minutes per simulation


def get_new_files() -> List[Path]:
    """Get list of newly added SWMM files from git diff."""
    repo_root = Path(__file__).parent
    result = []
    
    # Get list from git
    import subprocess
    try:
        output = subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD~1", "EPASWMM Example Files"],
            cwd=repo_root,
            text=True
        )
        for line in output.strip().split('\n'):
            if line.endswith('.inp'):
                file_path = repo_root / line
                if file_path.exists():
                    result.append(file_path)
    except Exception as e:
        print(f"⚠️  Error getting git diff: {e}")
        print("   Falling back to checking all files...")
        # Fallback: check all files (less efficient)
        for inp_file in (repo_root / "EPASWMM Example Files").rglob("*.inp"):
            result.append(inp_file)
    
    return sorted(result)


def submit_simulation(client: WRAPIClient, input_file: Path) -> Dict:
    """Submit a single simulation and return result with timing."""
    result = {
        "file": str(input_file.relative_to(Path(__file__).parent)),
        "simulation_id": None,
        "submit_time": None,
        "submit_duration": None,
        "status": "pending",
        "error": None
    }
    
    start_time = time.time()
    try:
        label = f"New File Test - {input_file.stem}"
        response = client.run_simulation_from_file(str(input_file), "swmm", label)
        
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
            
            # Timeout after specified duration
            if time.time() - start_time > TIMEOUT:
                return ("timeout", time.time() - start_time)
                
        except Exception as e:
            return ("error", time.time() - start_time)


def test_new_files():
    """Test all newly added SWMM files."""
    print("=" * 70)
    print("Testing Newly Added SWMM Files")
    print("=" * 70)
    
    # Get API client
    api_url = os.getenv("WRAPI_URL", DEFAULT_API_URL)
    client = WRAPIClient(api_url=api_url)
    
    # Check API health
    print(f"\n🔍 Checking API health: {api_url}")
    if not client.health_check():
        print("❌ API health check failed!")
        return
    print("✅ API is healthy")
    
    # Get new files
    print("\n📂 Finding newly added files...")
    new_files = get_new_files()
    total_files = len(new_files)
    print(f"   Found {total_files} newly added file(s)")
    
    if total_files == 0:
        print("✅ No new files to test!")
        return
    
    # Submit all simulations
    print(f"\n🚀 Submitting {total_files} simulations (max {MAX_WORKERS} parallel)...")
    results = []
    submission_start = time.time()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all files
        future_to_file = {
            executor.submit(submit_simulation, client, inp_file): inp_file
            for inp_file in new_files
        }
        
        # Collect submission results
        for future in as_completed(future_to_file):
            inp_file = future_to_file[future]
            try:
                result = future.result()
                results.append(result)
                
                if result["status"] == "submitted":
                    print(f"   ✅ Submitted: {Path(result['file']).name}")
                else:
                    print(f"   ❌ Failed to submit: {Path(result['file']).name} - {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"   ❌ Exception submitting {inp_file.name}: {e}")
                results.append({
                    "file": str(inp_file.relative_to(Path(__file__).parent)),
                    "status": "submit_exception",
                    "error": str(e)
                })
    
    submission_time = time.time() - submission_start
    print(f"\n⏱️  Submission completed in {submission_time:.1f} seconds")
    
    # Poll for completion
    submitted = [r for r in results if r.get("simulation_id")]
    if not submitted:
        print("\n❌ No simulations were successfully submitted!")
        return
    
    print(f"\n⏳ Polling {len(submitted)} simulations for completion...")
    print(f"   (Checking every {POLL_INTERVAL} seconds)")
    
    polling_start = time.time()
    completed_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Poll all submitted simulations
        future_to_result = {
            executor.submit(poll_simulation_status, client, r["simulation_id"]): r
            for r in submitted
        }
        
        # Collect polling results
        for future in as_completed(future_to_result):
            result = future_to_result[future]
            try:
                final_status, exec_time = future.result()
                result["final_status"] = final_status
                result["execution_time"] = exec_time
                completed_count += 1
                
                status_icon = "✅" if final_status == "completed" else "❌"
                print(f"   {status_icon} {Path(result['file']).name}: {final_status} ({exec_time:.1f}s)")
                
                if completed_count % 10 == 0:
                    print(f"   Progress: {completed_count}/{len(submitted)} completed...")
                    
            except Exception as e:
                result["final_status"] = "poll_error"
                result["error"] = str(e)
                print(f"   ❌ Error polling {Path(result['file']).name}: {e}")
    
    polling_time = time.time() - polling_start
    total_time = time.time() - submission_start
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    completed = [r for r in results if r.get("final_status") == "completed"]
    failed = [r for r in results if r.get("final_status") in ["failed", "error", "timeout", "poll_error"]]
    submit_failed = [r for r in results if r.get("status") in ["submit_failed", "submit_exception"]]
    
    print(f"\n✅ Successfully completed: {len(completed)}")
    print(f"❌ Failed/Error: {len(failed)}")
    print(f"⚠️  Submit failed: {len(submit_failed)}")
    print(f"📊 Total files tested: {total_files}")
    print(f"\n⏱️  Total time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    print(f"   Submission: {submission_time:.1f}s")
    print(f"   Execution: {polling_time:.1f}s")
    
    if completed:
        avg_exec_time = sum(r.get("execution_time", 0) for r in completed) / len(completed)
        print(f"   Average execution time: {avg_exec_time:.1f}s per simulation")
    
    # Save detailed results
    results_file = Path(__file__).parent / "new_swmm_test_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_files": total_files,
            "completed": len(completed),
            "failed": len(failed),
            "submit_failed": len(submit_failed),
            "total_time": total_time,
            "results": results
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    # Show failed files
    if failed or submit_failed:
        print(f"\n⚠️  Failed files ({len(failed) + len(submit_failed)}):")
        for result in (failed + submit_failed)[:20]:
            error = result.get("error", result.get("final_status", "unknown"))
            print(f"   - {Path(result['file']).name}: {error}")
        if len(failed) + len(submit_failed) > 20:
            print(f"   ... and {len(failed) + len(submit_failed) - 20} more")
    
    # Success rate
    success_rate = (len(completed) / total_files * 100) if total_files > 0 else 0
    print(f"\n📈 Success rate: {success_rate:.1f}% ({len(completed)}/{total_files})")
    
    if success_rate >= 95:
        print("✅ Excellent! Most files are working correctly.")
    elif success_rate >= 80:
        print("⚠️  Good, but some files need attention.")
    else:
        print("❌ Many files failed. Review errors above.")


if __name__ == "__main__":
    test_new_files()
