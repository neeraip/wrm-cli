#!/usr/bin/env python3
"""
WRAPI - Water Resources Modeling API CLI Tool
A command-line tool for running SWMM and EPANET simulations via the NEER WRM API.

Usage:
    python wrapi.py run <input_file> [options]
    python wrapi.py status <simulation_id>
    python wrapi.py logs <simulation_id>
    python wrapi.py files <simulation_id>
    python wrapi.py list [--type swmm|epanet]
    
Examples:
    # Run a SWMM simulation from local file
    python wrapi.py run model.inp --type swmm --label "My Storm Model"
    
    # Run from URL
    python wrapi.py run https://example.com/model.inp --type swmm
    
    # Run with auxiliary files (temperature, rainfall data)
    python wrapi.py run model.inp --type swmm --aux temp.dat rainfall.dat
    
    # Check status
    python wrapi.py status 550e8400-e29b-41d4-a716-446655440000
    
    # Get result files
    python wrapi.py files 550e8400-e29b-41d4-a716-446655440000
"""

import argparse
import json
import os
import sys
import time
import zipfile
import tempfile
import requests
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from .env in the same directory as this script
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()  # Try default locations
except ImportError:
    pass  # python-dotenv not installed, rely on system environment variables

# Configuration
DEFAULT_API_URL = "https://wrm.neer.ai"  # Production URL
CONFIG_FILE = os.path.expanduser("~/.wrapi_config.json")

class WRAPIClient:
    """Client for interacting with the Water Resources Modeling API."""
    
    def __init__(self, api_url: str = None, api_token: str = None):
        self.api_url = api_url or os.getenv("WRAPI_URL", DEFAULT_API_URL)
        self.api_token = api_token or os.getenv("WRAPI_TOKEN") or self._load_token()
        
        if not self.api_token:
            print("⚠️  No API token found. Set WRAPI_TOKEN environment variable or run:")
            print("   python wrapi.py config --token YOUR_TOKEN")
            sys.exit(1)
    
    def _load_token(self) -> Optional[str]:
        """Load API token from config file."""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('token')
        return None
    
    def _headers(self) -> dict:
        """Get request headers with authorization."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an API request."""
        url = f"{self.api_url}{endpoint}"
        headers = kwargs.pop('headers', self._headers())
        
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            sys.exit(1)
    
    def health_check(self) -> bool:
        """Check if API is healthy."""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def list_simulations(self, sim_type: str = None, limit: int = 20) -> List[dict]:
        """List recent simulations."""
        params = {}
        if sim_type:
            params['type'] = sim_type
        
        response = self._request("GET", "/simulations", params=params)
        
        if response.status_code == 200:
            return response.json()[:limit]
        else:
            print(f"❌ Failed to list simulations: {response.text}")
            return []
    
    def get_simulation(self, sim_id: str) -> Optional[dict]:
        """Get simulation details."""
        response = self._request("GET", f"/simulations/{sim_id}")
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"❌ Simulation not found: {sim_id}")
            return None
        else:
            print(f"❌ Failed to get simulation: {response.text}")
            return None
    
    def get_simulation_logs(self, sim_id: str, limit: int = 50) -> List[dict]:
        """Get simulation logs."""
        response = self._request("GET", f"/simulations/{sim_id}/logs", params={"limit": limit})
        
        if response.status_code == 200:
            return response.json().get('logs', [])
        else:
            print(f"❌ Failed to get logs: {response.text}")
            return []
    
    def get_simulation_files(self, sim_id: str) -> List[dict]:
        """Get simulation result files."""
        response = self._request("GET", f"/simulations/{sim_id}/files")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get files: {response.text}")
            return []
    
    def run_simulation_from_url(self, input_url: str, sim_type: str, label: str = None) -> Optional[dict]:
        """Run simulation from a remote URL."""
        data = {
            "type": sim_type,
            "input_file_uri": input_url
        }
        if label:
            data["label"] = label
        
        response = self._request("POST", "/simulations", json=data)
        
        if response.status_code == 201:
            return response.json()
        else:
            print(f"❌ Failed to create simulation: {response.text}")
            return None
    
    def run_simulation_from_file(self, input_file: str, sim_type: str, 
                                  label: str = None, aux_files: List[str] = None) -> Optional[dict]:
        """Run simulation from local file(s)."""
        input_path = Path(input_file)
        
        if not input_path.exists():
            print(f"❌ Input file not found: {input_file}")
            return None
        
        # Prepare the file(s) to upload
        if aux_files:
            # Create a zip file with input + auxiliary files
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                zip_path = tmp.name
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(input_path, input_path.name)
                for aux in aux_files:
                    aux_path = Path(aux)
                    if aux_path.exists():
                        zf.write(aux_path, aux_path.name)
                    else:
                        print(f"⚠️  Auxiliary file not found: {aux}")
            
            upload_path = zip_path
            upload_name = input_path.stem + '.zip'
        else:
            upload_path = str(input_path)
            upload_name = input_path.name
        
        # Upload via multipart form
        with open(upload_path, 'rb') as f:
            files = {'file': (upload_name, f)}
            data = {'type': sim_type}
            if label:
                data['label'] = label
            
            headers = {"Authorization": f"Bearer {self.api_token}"}
            response = requests.post(
                f"{self.api_url}/simulations",
                headers=headers,
                files=files,
                data=data
            )
        
        # Cleanup temp zip
        if aux_files and os.path.exists(zip_path):
            os.unlink(zip_path)
        
        if response.status_code == 201:
            return response.json()
        else:
            print(f"❌ Failed to create simulation: {response.text}")
            return None
    
    def wait_for_completion(self, sim_id: str, timeout: int = 600, interval: int = 15) -> Optional[dict]:
        """Wait for simulation to complete by polling logs every 15 seconds."""
        start_time = time.time()
        last_status = None
        seen_log_messages = set()
        last_progress = None
        
        print(f"   Polling logs every {interval}s...")
        
        while time.time() - start_time < timeout:
            # Get simulation status
            sim = self.get_simulation(sim_id)
            if not sim:
                return None
            
            status = sim.get('status')
            
            # Get latest logs to show progress
            logs = self.get_simulation_logs(sim_id, limit=20)
            
            # Extract and display progress
            progress = extract_progress_from_logs(logs)
            if progress is None and status == 'running':
                progress = calculate_time_progress(sim)
            
            # Show progress bar if available
            if progress is not None and progress != last_progress:
                bar_length = 30
                filled = int(bar_length * progress / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                print(f"   Progress: [{bar}] {progress:.1f}%")
                last_progress = progress
            
            # Display new log messages (newest first in response, so reverse for display)
            for log in reversed(logs):
                msg = log.get('message', '')
                ts = log.get('timestamp', '')
                log_key = f"{ts}:{msg}"
                
                if log_key not in seen_log_messages:
                    seen_log_messages.add(log_key)
                    # Format timestamp for display
                    try:
                        # Handle various timestamp formats
                        ts_clean = ts.replace('Z', '+00:00')
                        if '.' in ts_clean:
                            # Truncate microseconds if too long
                            parts = ts_clean.split('.')
                            if len(parts[1]) > 6:
                                ts_clean = parts[0] + '.' + parts[1][:6] + '+00:00'
                        dt = datetime.fromisoformat(ts_clean)
                        ts_short = dt.strftime('%H:%M:%S')
                    except:
                        # Fallback: extract time portion if available
                        if 'T' in ts and ':' in ts:
                            ts_short = ts.split('T')[1][:8]
                        else:
                            ts_short = ts[:8] if ts else ''
                    print(f"   [{ts_short}] {msg}")
            
            # Check if completed or failed
            if status in ['completed', 'failed']:
                if progress is not None:
                    print(f"   Progress: [{'█' * 30}] 100.0%")
                return sim
            
            # Update status display if changed
            if status != last_status:
                last_status = status
            
            time.sleep(interval)
        
        print(f"⚠️  Timeout waiting for simulation after {timeout}s")
        return self.get_simulation(sim_id)


def extract_progress_from_logs(logs: List[dict]) -> Optional[float]:
    """Extract progress percentage from log messages."""
    import re
    
    # Look for progress indicators in logs
    for log in reversed(logs):  # Check newest first
        msg = log.get('message', '').lower()
        
        # Look for percentage patterns
        patterns = [
            r'(\d+(?:\.\d+)?)\s*%',  # "50%" or "50.5%"
            r'progress[:\s]+(\d+(?:\.\d+)?)\s*%',  # "Progress: 50%"
            r'(\d+(?:\.\d+)?)\s*percent',  # "50 percent"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, msg)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
    
    return None


def calculate_time_progress(sim: dict) -> Optional[float]:
    """Calculate progress based on elapsed time vs estimated total."""
    started_at = sim.get('started_at')
    if not started_at:
        return None
    
    try:
        started = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
        elapsed = (datetime.now(started.tzinfo) - started).total_seconds()
        
        # For SWMM/EPANET, most simulations complete in seconds to minutes
        # We can estimate based on status and elapsed time
        status = sim.get('status', '')
        
        if status == 'running':
            # If running for more than 30 seconds, likely a longer simulation
            # Estimate based on typical ranges (most complete in 1-5 minutes)
            if elapsed < 10:
                return min(50, elapsed / 10 * 50)  # Early stage
            elif elapsed < 60:
                return min(80, 50 + (elapsed - 10) / 50 * 30)  # Mid stage
            else:
                return min(95, 80 + (elapsed - 60) / 300 * 15)  # Late stage
        
    except:
        pass
    
    return None


def format_timestamp(ts: str) -> str:
    """Format ISO timestamp for display."""
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return ts


def format_size(size: int) -> str:
    """Format file size for display."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def copy_and_update_ini_file(input_file_path: str, results_folder: Path) -> bool:
    """
    Check for a .ini file alongside the input .inp file.
    If found, copy it to results folder and update Current=1 under [Results].
    Preserves the original .ini filename.
    
    Returns True if .ini file was processed, False otherwise.
    """
    input_path = Path(input_file_path)
    
    # Look for .ini file with same base name
    ini_path = input_path.with_suffix('.ini')
    
    if not ini_path.exists():
        return False
    
    # Preserve original filename
    ini_filename = ini_path.name
    print(f"\n📋 Found .ini file: {ini_filename}")
    
    try:
        # Read the .ini file and update Current=1 under [Results]
        updated_lines = []
        inside_results = False
        found_current = False
        
        with open(ini_path, 'r', encoding='utf-8', errors='replace') as file:
            for line in file:
                if line.strip() == '[Results]':
                    inside_results = True
                    updated_lines.append(line)
                elif inside_results and line.strip().startswith('Current='):
                    updated_lines.append('Current=1\n')
                    inside_results = False
                    found_current = True
                elif line.strip().startswith('[') and inside_results:
                    # New section started without finding Current=
                    # Add Current=1 before the new section
                    if not found_current:
                        updated_lines.append('Current=1\n')
                    inside_results = False
                    updated_lines.append(line)
                else:
                    updated_lines.append(line)
        
        # If [Results] was the last section and had no Current=
        if inside_results and not found_current:
            updated_lines.append('Current=1\n')
        
        # Write updated .ini file to results folder with original filename
        dest_ini_path = results_folder / ini_filename
        with open(dest_ini_path, 'w', encoding='utf-8') as file:
            file.writelines(updated_lines)
        
        size_str = format_size(dest_ini_path.stat().st_size)
        print(f"   ✅ {ini_filename:40} ({size_str}) - Updated Current=1 under [Results]")
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to process .ini file: {e}")
        return False


def download_results_to_timestamped_folder(client: WRAPIClient, sim_id: str, files: List[dict], input_file_path: Optional[str] = None):
    """Download simulation results to a timestamped folder, preserving original filenames."""
    from urllib.parse import unquote
    
    # Create results directory
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    
    # Create timestamped folder (format: YYYYMMDD_HHMMSS)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sim_folder = results_dir / f"{timestamp}_{sim_id[:8]}"
    sim_folder.mkdir(parents=True, exist_ok=True)
    
    print(f"\n⬇️  Downloading results to: {sim_folder}/")
    
    downloaded_count = 0
    for f in files:
        file_type = f.get('type', 'unknown')
        url = f.get('url', '')
        
        if not url:
            continue
        
        # Extract original filename from URL and decode URL encoding
        # URLs like: .../Raytown%20WDS-290%20Calibration%20Model.out
        url_filename = unquote(url.split('/')[-1])
        
        # Use the original filename from URL (preserves the model name)
        if url_filename and '.' in url_filename:
            filename = url_filename
        else:
            # Fallback to generic names if URL doesn't have proper filename
            if file_type == 'input':
                filename = 'input.inp'
            elif file_type == 'output':
                filename = 'output.out'
            elif file_type == 'report':
                filename = 'report.rpt'
            else:
                filename = f"{file_type}.{file_type}"
        
        filepath = sim_folder / filename
        
        try:
            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()
            
            # Download file
            with open(filepath, 'wb') as out_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        out_file.write(chunk)
            
            size_str = format_size(filepath.stat().st_size)
            print(f"   ✅ {filename:40} ({size_str})")
            downloaded_count += 1
            
        except Exception as e:
            print(f"   ❌ Failed to download {filename}: {e}")
    
    # Check for and process .ini file if input file path is provided
    ini_processed = False
    if input_file_path and not input_file_path.startswith('http'):
        ini_processed = copy_and_update_ini_file(input_file_path, sim_folder)
    
    total_files = downloaded_count + (1 if ini_processed else 0)
    if total_files > 0:
        print(f"\n✅ Downloaded {total_files} file(s) to {sim_folder}/")
    else:
        print(f"\n⚠️  No files were downloaded")


def cmd_run(args):
    """Run a simulation."""
    client = WRAPIClient()
    
    # Check API health
    if not client.health_check():
        print("⚠️  API may be unavailable, proceeding anyway...")
    
    input_source = args.input
    sim_type = args.type
    label = args.label or f"{sim_type.upper()} - {Path(input_source).stem if not input_source.startswith('http') else 'Remote'}"
    
    print(f"🚀 Starting {sim_type.upper()} simulation...")
    print(f"   Input: {input_source}")
    print(f"   Label: {label}")
    
    # Determine if URL or local file
    if input_source.startswith('http://') or input_source.startswith('https://'):
        result = client.run_simulation_from_url(input_source, sim_type, label)
    else:
        aux_files = args.aux if args.aux else None
        if aux_files:
            print(f"   Auxiliary files: {', '.join(aux_files)}")
        result = client.run_simulation_from_file(input_source, sim_type, label, aux_files)
    
    if not result:
        sys.exit(1)
    
    sim_id = result['id']
    print(f"\n✅ Simulation created!")
    print(f"   ID: {sim_id}")
    print(f"   Status: {result['status']}")
    
    # Wait for completion if requested
    if args.wait:
        print(f"\n⏳ Waiting for completion (timeout: {args.timeout}s)...")
        result = client.wait_for_completion(sim_id, timeout=args.timeout, interval=15)
        
        if result:
            status = result.get('status')
            if status == 'completed':
                print(f"\n🎉 Simulation completed successfully!")
                
                # Always show result files immediately on completion
                print(f"\n📁 Result files:")
                # Small delay to ensure files are registered
                time.sleep(2)
                files = client.get_simulation_files(sim_id)
                if files:
                    for f in files:
                        size_str = format_size(f.get('size', 0))
                        print(f"   [{f['type']:10}] {size_str:>10}  {f['url']}")
                    
                    # Automatically download results to timestamped folder
                    # Pass input_source to check for .ini files alongside the input file
                    download_results_to_timestamped_folder(client, sim_id, files, input_source)
                else:
                    print("   (Files still uploading, use 'wrapi.py files' to check later)")
                    
            elif status == 'failed':
                print(f"\n❌ Simulation failed!")
                print("\n📋 Check the report file for error details:")
                # Get files to show report URL
                files = client.get_simulation_files(sim_id)
                report = next((f for f in files if f['type'] == 'report'), None)
                if report:
                    print(f"   {report['url']}")
    else:
        print(f"\nTo check status: python wrapi.py status {sim_id}")
        print(f"To view logs:    python wrapi.py logs {sim_id}")
        print(f"To get files:    python wrapi.py files {sim_id}")


def extract_progress_from_logs(logs: List[dict]) -> Optional[float]:
    """Extract progress percentage from log messages."""
    import re
    
    # Look for progress indicators in logs
    for log in reversed(logs):  # Check newest first
        msg = log.get('message', '').lower()
        
        # Look for percentage patterns
        patterns = [
            r'(\d+(?:\.\d+)?)\s*%',  # "50%" or "50.5%"
            r'progress[:\s]+(\d+(?:\.\d+)?)\s*%',  # "Progress: 50%"
            r'(\d+(?:\.\d+)?)\s*percent',  # "50 percent"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, msg)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
    
    return None


def calculate_time_progress(sim: dict) -> Optional[float]:
    """Calculate progress based on elapsed time vs estimated total."""
    started_at = sim.get('started_at')
    if not started_at:
        return None
    
    try:
        started = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
        elapsed = (datetime.now(started.tzinfo) - started).total_seconds()
        
        # For SWMM/EPANET, most simulations complete in seconds to minutes
        # We can estimate based on status and elapsed time
        status = sim.get('status', '')
        
        if status == 'running':
            # If running for more than 30 seconds, likely a longer simulation
            # Estimate based on typical ranges (most complete in 1-5 minutes)
            if elapsed < 10:
                return min(50, elapsed / 10 * 50)  # Early stage
            elif elapsed < 60:
                return min(80, 50 + (elapsed - 10) / 50 * 30)  # Mid stage
            else:
                return min(95, 80 + (elapsed - 60) / 300 * 15)  # Late stage
        
    except:
        pass
    
    return None


def cmd_status(args):
    """Check simulation status with progress information."""
    client = WRAPIClient()
    sim = client.get_simulation(args.id)
    
    if sim:
        print(f"\n📊 Simulation Details")
        print(f"   ID:      {sim['id']}")
        print(f"   Type:    {sim['type'].upper()} v{sim.get('version', 'N/A')}")
        print(f"   Label:   {sim.get('label', 'N/A')}")
        print(f"   Status:  {sim['status']}")
        print(f"   Created: {format_timestamp(sim['created_at'])}")
        
        if sim.get('started_at'):
            started = datetime.fromisoformat(sim['started_at'].replace('Z', '+00:00'))
            print(f"   Started: {format_timestamp(sim['started_at'])}")
            
            # Calculate elapsed time
            elapsed = (datetime.now(started.tzinfo) - started).total_seconds()
            if elapsed < 60:
                print(f"   Elapsed: {elapsed:.1f} seconds")
            else:
                print(f"   Elapsed: {elapsed/60:.1f} minutes")
        
        if sim.get('completed_at'):
            print(f"   Completed: {format_timestamp(sim['completed_at'])}")
            
            # Calculate total execution time
            if sim.get('started_at'):
                started = datetime.fromisoformat(sim['started_at'].replace('Z', '+00:00'))
                completed = datetime.fromisoformat(sim['completed_at'].replace('Z', '+00:00'))
                exec_time = (completed - started).total_seconds()
                print(f"   Duration: {exec_time:.2f} seconds ({exec_time/60:.2f} minutes)")
        
        if sim.get('ended_at'):
            print(f"   Ended: {format_timestamp(sim['ended_at'])}")
        
        # Show progress if running
        if sim.get('status') == 'running':
            print(f"\n⏳ Progress:")
            
            # Try to get progress from logs
            logs = client.get_simulation_logs(args.id, limit=50)
            log_progress = extract_progress_from_logs(logs)
            
            if log_progress is not None:
                print(f"   {log_progress:.1f}% complete (from logs)")
                # Show progress bar
                bar_length = 30
                filled = int(bar_length * log_progress / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                print(f"   [{bar}] {log_progress:.1f}%")
            else:
                # Estimate based on elapsed time
                time_progress = calculate_time_progress(sim)
                if time_progress is not None:
                    print(f"   ~{time_progress:.1f}% complete (estimated from elapsed time)")
                    bar_length = 30
                    filled = int(bar_length * time_progress / 100)
                    bar = '█' * filled + '░' * (bar_length - filled)
                    print(f"   [{bar}] {time_progress:.1f}%")
                else:
                    print(f"   Status: Running (check logs for details)")
            
            # Show recent log messages
            if logs:
                print(f"\n📋 Recent Log Messages:")
                for log in logs[-3:]:  # Show last 3 messages
                    msg = log.get('message', '')
                    ts = log.get('timestamp', '')
                    try:
                        ts_clean = ts.replace('Z', '+00:00')
                        dt = datetime.fromisoformat(ts_clean)
                        ts_short = dt.strftime('%H:%M:%S')
                    except:
                        ts_short = ts[:8] if ts else ''
                    print(f"   [{ts_short}] {msg}")
        else:
            print()


def cmd_logs(args):
    """View simulation logs."""
    client = WRAPIClient()
    logs = client.get_simulation_logs(args.id, limit=args.limit)
    
    if logs:
        print(f"\n📋 Simulation Logs (showing {len(logs)})")
        print("-" * 60)
        for log in reversed(logs):  # Show oldest first
            ts = format_timestamp(log['timestamp'])
            print(f"[{ts}] {log['message']}")
    else:
        print("No logs found.")


def cmd_files(args):
    """List simulation result files."""
    client = WRAPIClient()
    files = client.get_simulation_files(args.id)
    
    if files:
        print(f"\n📁 Simulation Files")
        print("-" * 80)
        for f in files:
            size_str = format_size(f.get('size', 0))
            print(f"[{f['type']:10}] {size_str:>10}  {f['url']}")
        
        # Offer to download
        if args.download:
            download_dir = Path(args.download)
            download_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"\n⬇️  Downloading to {download_dir}/")
            for f in files:
                filename = f['url'].split('/')[-1]
                filepath = download_dir / filename
                
                print(f"   {filename}...", end=" ")
                response = requests.get(f['url'])
                if response.status_code == 200:
                    with open(filepath, 'wb') as out:
                        out.write(response.content)
                    print("✓")
                else:
                    print("✗")
    else:
        print("No files found.")


def cmd_list(args):
    """List recent simulations."""
    client = WRAPIClient()
    sims = client.list_simulations(sim_type=args.type, limit=args.limit)
    
    if sims:
        print(f"\n📋 Recent Simulations")
        print("-" * 100)
        print(f"{'ID':<38} {'Type':<8} {'Status':<12} {'Label':<30} {'Created'}")
        print("-" * 100)
        for sim in sims:
            sim_id = sim['id']
            sim_type = sim['type'].upper()
            status = sim['status']
            label = (sim.get('label', 'N/A'))[:30]
            created = format_timestamp(sim['created_at'])
            print(f"{sim_id:<38} {sim_type:<8} {status:<12} {label:<30} {created}")
    else:
        print("No simulations found.")


def cmd_config(args):
    """Configure API settings."""
    config = {}
    
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    
    if args.token:
        config['token'] = args.token
        print(f"✅ API token saved to {CONFIG_FILE}")
    
    if args.url:
        config['url'] = args.url
        print(f"✅ API URL saved: {args.url}")
    
    if args.show:
        print(f"\n⚙️  Current Configuration")
        print(f"   Config file: {CONFIG_FILE}")
        print(f"   API URL: {config.get('url', DEFAULT_API_URL)}")
        print(f"   Token: {'*' * 20 + config.get('token', '')[-10:] if config.get('token') else 'Not set'}")
        return
    
    if config:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="WRAPI - Water Resources Modeling API CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s run model.inp --type swmm --wait
  %(prog)s run https://example.com/model.inp --type epanet
  %(prog)s run model.inp --type swmm --aux rainfall.dat temp.dat
  %(prog)s status 550e8400-e29b-41d4-a716-446655440000
  %(prog)s files 550e8400-e29b-41d4-a716-446655440000 --download ./results
  %(prog)s list --type swmm --limit 10
  %(prog)s config --token YOUR_API_TOKEN
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run a simulation')
    run_parser.add_argument('input', help='Input file path or URL')
    run_parser.add_argument('--type', '-t', required=True, choices=['swmm', 'epanet', 'hec_ras'],
                           help='Simulation type')
    run_parser.add_argument('--label', '-l', help='Simulation label')
    run_parser.add_argument('--aux', '-a', nargs='+', help='Auxiliary files (temperature, rainfall, etc.)')
    run_parser.add_argument('--wait', '-w', action='store_true', help='Wait for completion')
    run_parser.add_argument('--timeout', default=600, type=int, help='Wait timeout in seconds (default: 600)')
    run_parser.add_argument('--show-files', '-f', action='store_true', help='Show result files after completion')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check simulation status')
    status_parser.add_argument('id', help='Simulation ID')
    
    # Logs command
    logs_parser = subparsers.add_parser('logs', help='View simulation logs')
    logs_parser.add_argument('id', help='Simulation ID')
    logs_parser.add_argument('--limit', '-n', default=50, type=int, help='Number of logs to show')
    
    # Files command
    files_parser = subparsers.add_parser('files', help='List simulation files')
    files_parser.add_argument('id', help='Simulation ID')
    files_parser.add_argument('--download', '-d', help='Download files to directory')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List simulations')
    list_parser.add_argument('--type', '-t', choices=['swmm', 'epanet', 'hec_ras'],
                            help='Filter by type')
    list_parser.add_argument('--limit', '-n', default=20, type=int, help='Number to show')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configure API settings')
    config_parser.add_argument('--token', help='Set API token')
    config_parser.add_argument('--url', help='Set API URL')
    config_parser.add_argument('--show', '-s', action='store_true', help='Show current config')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    commands = {
        'run': cmd_run,
        'status': cmd_status,
        'logs': cmd_logs,
        'files': cmd_files,
        'list': cmd_list,
        'config': cmd_config,
    }
    
    commands[args.command](args)


if __name__ == '__main__':
    main()
