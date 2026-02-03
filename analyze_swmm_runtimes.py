#!/usr/bin/env python3
"""
Analyze SWMM simulation runtimes from test results and API.
Finds min/max/average execution times for SWMM simulations.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))
from wrapi import WRAPIClient

DEFAULT_API_URL = "https://wrm.neer.ai"


def analyze_from_test_results():
    """Analyze runtimes from test result files."""
    results_file = Path(__file__).parent / "new_swmm_test_results.json"
    
    if not results_file.exists():
        print("⚠️  Test results file not found: new_swmm_test_results.json")
        return None
    
    print("📊 Analyzing runtimes from test results...")
    data = json.load(open(results_file))
    
    completed = [r for r in data.get('results', []) 
                 if r.get('final_status') == 'completed' and r.get('execution_time')]
    
    if not completed:
        print("⚠️  No completed simulations with execution times found")
        return None
    
    times = [r['execution_time'] for r in completed]
    
    return {
        'source': 'test_results',
        'count': len(completed),
        'times': times,
        'simulations': completed
    }


def calculate_execution_time(sim: Dict) -> Optional[float]:
    """Calculate execution time in seconds from simulation timestamps."""
    started_at = sim.get('started_at')
    completed_at = sim.get('completed_at') or sim.get('ended_at')
    
    if not started_at or not completed_at:
        return None
    
    try:
        started = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
        completed = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
        return (completed - started).total_seconds()
    except Exception:
        return None


def analyze_from_api(limit: int = 100):
    """Try to get more data from API."""
    print("\n📊 Attempting to fetch additional data from API...")
    
    api_url = os.getenv("WRAPI_URL", DEFAULT_API_URL)
    client = WRAPIClient(api_url=api_url)
    
    if not client.health_check():
        print("⚠️  API health check failed, skipping API analysis")
        return None
    
    try:
        # Try to get simulations
        all_sims = client.list_simulations(sim_type="swmm", limit=limit)
        completed = []
        
        for sim in all_sims:
            if sim.get('status') == 'completed':
                exec_time = calculate_execution_time(sim)
                if exec_time is not None:
                    completed.append({
                        'id': sim.get('id'),
                        'label': sim.get('label', 'N/A'),
                        'execution_time': exec_time
                    })
        
        if completed:
            times = [r['execution_time'] for r in completed]
            return {
                'source': 'api',
                'count': len(completed),
                'times': times,
                'simulations': completed
            }
        else:
            print("   No completed simulations with timestamps found in API")
            return None
            
    except Exception as e:
        print(f"   ⚠️  Error fetching from API: {e}")
        return None


def print_statistics(data: Dict):
    """Print runtime statistics."""
    times = data['times']
    source = data['source']
    count = data['count']
    
    min_time = min(times)
    max_time = max(times)
    avg_time = sum(times) / len(times)
    median_time = sorted(times)[len(times) // 2]
    
    print("\n" + "=" * 70)
    print("SWMM RUNTIME STATISTICS")
    print("=" * 70)
    print(f"\nData source: {source}")
    print(f"Total simulations analyzed: {count}")
    
    print(f"\n⏱️  Execution Times:")
    print(f"   Minimum:  {min_time:.3f} seconds ({min_time:.2f} minutes)")
    print(f"   Maximum:  {max_time:.3f} seconds ({max_time/60:.2f} minutes)")
    print(f"   Average:  {avg_time:.3f} seconds ({avg_time/60:.2f} minutes)")
    print(f"   Median:   {median_time:.3f} seconds ({median_time/60:.2f} minutes)")
    
    # Show fastest and slowest
    simulations = data['simulations']
    simulations.sort(key=lambda x: x['execution_time'])
    
    print(f"\n🚀 Fastest Simulations:")
    for sim in simulations[:5]:
        label = sim.get('file', sim.get('label', 'N/A'))
        if len(label) > 50:
            label = label[:47] + "..."
        print(f"   {sim['execution_time']:.3f}s - {label}")
    
    print(f"\n🐌 Slowest Simulations:")
    for sim in simulations[-5:]:
        label = sim.get('file', sim.get('label', 'N/A'))
        if len(label) > 50:
            label = label[:47] + "..."
        print(f"   {sim['execution_time']:.3f}s ({sim['execution_time']/60:.2f} min) - {label}")
    
    # Time distribution
    print(f"\n📊 Time Distribution:")
    buckets = {
        '< 1 second': 0,
        '1-5 seconds': 0,
        '5-10 seconds': 0,
        '10-30 seconds': 0,
        '30-60 seconds': 0,
        '1-5 minutes': 0,
        '5-10 minutes': 0,
        '> 10 minutes': 0
    }
    
    for time in times:
        if time < 1:
            buckets['< 1 second'] += 1
        elif time < 5:
            buckets['1-5 seconds'] += 1
        elif time < 10:
            buckets['5-10 seconds'] += 1
        elif time < 30:
            buckets['10-30 seconds'] += 1
        elif time < 60:
            buckets['30-60 seconds'] += 1
        elif time < 300:
            buckets['1-5 minutes'] += 1
        elif time < 600:
            buckets['5-10 minutes'] += 1
        else:
            buckets['> 10 minutes'] += 1
    
    for bucket, count in buckets.items():
        if count > 0:
            percentage = (count / len(times)) * 100
            print(f"   {bucket:15} {count:4} ({percentage:5.1f}%)")
    
    # Save results
    results_file = Path(__file__).parent / "swmm_runtime_analysis.json"
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'source': source,
            'total_simulations': count,
            'statistics': {
                'min_seconds': min_time,
                'max_seconds': max_time,
                'avg_seconds': avg_time,
                'median_seconds': median_time,
                'min_minutes': min_time / 60,
                'max_minutes': max_time / 60,
                'avg_minutes': avg_time / 60,
                'median_minutes': median_time / 60
            },
            'distribution': buckets,
            'fastest': simulations[:10],
            'slowest': simulations[-10:]
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")


def main():
    """Main analysis function."""
    print("=" * 70)
    print("SWMM Runtime Analysis")
    print("=" * 70)
    
    # Try test results first
    data = analyze_from_test_results()
    
    # Try API for additional data
    api_data = analyze_from_api(limit=100)
    
    # Combine if both available
    if data and api_data:
        print("\n📊 Combining data from test results and API...")
        combined_times = data['times'] + api_data['times']
        combined_sims = data['simulations'] + api_data['simulations']
        data = {
            'source': 'combined',
            'count': len(combined_times),
            'times': combined_times,
            'simulations': combined_sims
        }
    elif api_data and not data:
        data = api_data
    
    if data:
        print_statistics(data)
    else:
        print("\n❌ No runtime data found. Run some simulations first.")


if __name__ == "__main__":
    main()
