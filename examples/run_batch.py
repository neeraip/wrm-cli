#!/usr/bin/env python3
"""
Example: Batch run multiple SWMM simulations and collect results.

Usage:
    python run_batch.py model1.inp model2.inp model3.inp
    python run_batch.py *.inp
"""

import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wrapi import WRAPIClient

def run_batch(input_files: list, sim_type: str = 'swmm'):
    """Run multiple simulations and wait for all to complete."""
    
    client = WRAPIClient()
    
    # Check API health
    if not client.health_check():
        print("⚠️  Warning: API health check failed")
    
    # Submit all simulations
    simulations = []
    print(f"🚀 Submitting {len(input_files)} simulations...")
    
    for input_file in input_files:
        print(f"   Submitting: {input_file}")
        
        if input_file.startswith('http'):
            result = client.run_simulation_from_url(input_file, sim_type, label=input_file.split('/')[-1])
        else:
            result = client.run_simulation_from_file(input_file, sim_type)
        
        if result:
            simulations.append({
                'id': result['id'],
                'input': input_file,
                'status': result['status']
            })
            print(f"      ✓ ID: {result['id']}")
        else:
            print(f"      ✗ Failed to submit")
    
    print(f"\n⏳ Waiting for {len(simulations)} simulations to complete...")
    
    # Poll until all complete
    completed = set()
    start_time = time.time()
    timeout = 600  # 10 minutes
    
    while len(completed) < len(simulations) and (time.time() - start_time) < timeout:
        for sim in simulations:
            if sim['id'] in completed:
                continue
            
            details = client.get_simulation(sim['id'])
            if details:
                status = details.get('status')
                sim['status'] = status
                
                if status in ['completed', 'failed']:
                    completed.add(sim['id'])
                    emoji = "✅" if status == 'completed' else "❌"
                    print(f"   {emoji} {sim['input']}: {status}")
        
        if len(completed) < len(simulations):
            time.sleep(5)
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 BATCH RESULTS SUMMARY")
    print(f"{'='*60}")
    
    success = sum(1 for s in simulations if s['status'] == 'completed')
    failed = sum(1 for s in simulations if s['status'] == 'failed')
    other = len(simulations) - success - failed
    
    print(f"   ✅ Completed: {success}")
    print(f"   ❌ Failed:    {failed}")
    if other:
        print(f"   ⏳ Other:     {other}")
    
    print(f"\n📁 Result Files:")
    for sim in simulations:
        if sim['status'] == 'completed':
            files = client.get_simulation_files(sim['id'])
            report = next((f for f in files if f['type'] == 'report'), None)
            if report:
                print(f"   {sim['input']}:")
                print(f"      {report['url']}")
    
    return simulations


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python run_batch.py <input_file1> [input_file2] ...")
        print("\nExample URLs to try:")
        print("  https://raw.githubusercontent.com/SWMMEnablement/1729-SWMM5-Models/main/Hydraulics/10000FootSurchargeDepth.inp")
        print("  https://raw.githubusercontent.com/SWMMEnablement/1729-SWMM5-Models/main/Hydraulics/5_H&H_Elements.inp")
        sys.exit(1)
    
    run_batch(sys.argv[1:])
