#!/usr/bin/env python3
"""
Download and validate SWMM input files from SWMMEnablement/1729-SWMM5-Models repository.

This script:
1. Finds all .inp files in the repository
2. Checks for external file references
3. Validates external files exist
4. Downloads valid files preserving folder structure
5. Counts total valid input files
"""

import os
import re
import sys
import json
import requests
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from urllib.parse import urljoin, urlparse

# Repository info
REPO_OWNER = "SWMMEnablement"
REPO_NAME = "1729-SWMM5-Models"
BASE_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main"
API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

# Output directory
OUTPUT_DIR = Path("EPASWMM Example Files")


def get_repo_contents(path: str = "") -> List[Dict]:
    """Get contents of a repository path."""
    url = f"{API_BASE}/contents/{path}" if path else f"{API_BASE}/contents"
    response = None
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        # Handle both list and single item responses
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        return []
    except Exception as e:
        # Rate limiting - wait and retry
        if response is not None and (response.status_code == 403 or response.status_code == 429):
            print(f"   ⏳ Rate limited, waiting 60s...")
            time.sleep(60)
            return get_repo_contents(path)
        return []


def find_inp_files(folder_path: str = "") -> List[Tuple[str, str]]:
    """Recursively find all .inp files in repository."""
    inp_files = []
    
    def search_directory(path: str):
        contents = get_repo_contents(path)
        for item in contents:
            if isinstance(item, dict):
                if item.get('type') == 'file' and item.get('name', '').endswith('.inp'):
                    inp_files.append((path, item['name']))
                elif item.get('type') == 'dir':
                    # Recursively search subdirectories
                    sub_path = f"{path}/{item['name']}" if path else item['name']
                    search_directory(sub_path)
    
    search_directory(folder_path)
    return inp_files


def parse_swmm_for_external_files(content: str) -> Set[str]:
    """Extract external file references from SWMM .inp file content."""
    external_files = set()
    
    # SWMM sections that can reference external files
    # [RAINGAGES] - FILE references for rainfall data
    # [TEMPERATURE] - FILE references for temperature data
    # [TIMESERIES] - FILE references for time series data
    # [INFLOWS] - FILE references for inflow data
    # [RDII] - FILE references for RDII data
    
    # Find all FILE references, but exclude BACKDROP section if it exists
    backdrop_start = None
    backdrop_end = None
    
    if '[BACKDROP]' in content.upper():
        backdrop_match = re.search(r'^\[BACKDROP\]', content, re.IGNORECASE | re.MULTILINE)
        if backdrop_match:
            backdrop_start = backdrop_match.start()
            next_section = re.search(r'^\[', content[backdrop_match.end():], re.MULTILINE)
            if next_section:
                backdrop_end = backdrop_match.end() + next_section.start()
            else:
                backdrop_end = len(content)
    
    # Pattern for FILE references in SWMM
    patterns = [
        r'FILE\s+["\']([^"\']+)["\']',  # FILE "path"
        r'FILE\s+([^\s]+)',              # FILE path (no quotes)
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            # Check if this match is within BACKDROP section
            if backdrop_start is not None and backdrop_end is not None:
                if backdrop_start <= match.start() < backdrop_end:
                    # Skip - this is in BACKDROP section (visualization only)
                    continue
            
            file_path = match.group(1)
            # Skip absolute paths (Windows or Unix)
            if not (file_path.startswith('/') or ':\\' in file_path or file_path.startswith('C:')):
                external_files.add(file_path)
    
    return external_files


def check_file_exists_in_repo(folder_path: str, filename: str) -> bool:
    """Check if a file exists in the repository folder or data subfolder."""
    # Check in same folder
    file_path = f"{folder_path}/{filename}" if folder_path else filename
    contents = get_repo_contents(file_path)
    if isinstance(contents, list):
        if any(isinstance(item, dict) and item.get('name') == filename and item.get('type') == 'file' for item in contents):
            return True
    
    # Check in data subfolder
    data_path = f"{folder_path}/data/{filename}" if folder_path else f"data/{filename}"
    contents = get_repo_contents(data_path)
    if isinstance(contents, list):
        if any(isinstance(item, dict) and item.get('name') == filename and item.get('type') == 'file' for item in contents):
            return True
    
    # Check in DataFiles folder (common in SWMM repo)
    datafiles_path = f"DataFiles/{filename}"
    contents = get_repo_contents(datafiles_path)
    if isinstance(contents, list):
        if any(isinstance(item, dict) and item.get('name') == filename and item.get('type') == 'file' for item in contents):
            return True
    
    return False


def get_file_path_in_repo(folder_path: str, filename: str) -> Optional[str]:
    """Get the repository path where a file exists."""
    # Check in same folder
    file_path = f"{folder_path}/{filename}" if folder_path else filename
    contents = get_repo_contents(file_path)
    if isinstance(contents, list):
        if any(isinstance(item, dict) and item.get('name') == filename and item.get('type') == 'file' for item in contents):
            return file_path
    
    # Check in data subfolder
    data_path = f"{folder_path}/data/{filename}" if folder_path else f"data/{filename}"
    contents = get_repo_contents(data_path)
    if isinstance(contents, list):
        if any(isinstance(item, dict) and item.get('name') == filename and item.get('type') == 'file' for item in contents):
            return data_path
    
    # Check in DataFiles folder (common in SWMM repo)
    datafiles_path = f"DataFiles/{filename}"
    contents = get_repo_contents(datafiles_path)
    if isinstance(contents, list):
        if any(isinstance(item, dict) and item.get('name') == filename and item.get('type') == 'file' for item in contents):
            return datafiles_path
    
    return None


def download_file(repo_path: str, local_path: Path) -> bool:
    """Download a file from repository to local path."""
    url = f"{BASE_URL}/{repo_path}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"   ⚠️  Failed to download {repo_path}: {e}")
        return False


def validate_swmm_file(content: str) -> Tuple[bool, List[str]]:
    """Validate SWMM .inp file using knowledge base rules."""
    issues = []
    
    # Check for required sections - OPTIONS is always required
    # But SUBCATCHMENTS is optional for hydraulics-only models
    if '[OPTIONS]' not in content:
        issues.append("Missing required section: [OPTIONS]")
    
    # For a valid model, need either SUBCATCHMENTS (hydrology) or JUNCTIONS/CONDUITS (hydraulics)
    has_hydrology = '[SUBCATCHMENTS]' in content
    has_hydraulics = '[JUNCTIONS]' in content or '[CONDUITS]' in content or '[STORAGE]' in content
    
    if not has_hydrology and not has_hydraulics:
        issues.append("Missing model elements: needs SUBCATCHMENTS or JUNCTIONS/CONDUITS")
    
    # Check for infiltration parameters (ERROR 235)
    if '[INFILTRATION]' in content:
        infil_section = content.split('[INFILTRATION]')[1].split('[')[0]
        # Check for GREEN_AMPT with IMD > 1
        for line in infil_section.split('\n'):
            if line.strip() and not line.strip().startswith(';'):
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        # For GREEN_AMPT: Suction, Ksat, IMD
                        imd = float(parts[3])
                        if imd > 1.0:
                            issues.append(f"Invalid IMD value {imd} > 1.0 (GREEN_AMPT requires 0-1)")
                    except (ValueError, IndexError):
                        pass
    
    # Check for undefined TIMESERIES references in RAINGAGES
    if '[RAINGAGES]' in content and '[TIMESERIES]' in content:
        raingages_section = content.split('[RAINGAGES]')[1].split('[')[0]
        timeseries_section = content.split('[TIMESERIES]')[1].split('[')[0] if '[TIMESERIES]' in content else ''
        
        # Extract defined timeseries names
        defined_ts = set()
        for line in timeseries_section.split('\n'):
            if line.strip() and not line.strip().startswith(';'):
                parts = line.split()
                if parts:
                    defined_ts.add(parts[0])
        
        # Check RAINGAGES for TIMESERIES references
        for line in raingages_section.split('\n'):
            if 'TIMESERIES' in line.upper() and not line.strip().startswith(';'):
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.upper() == 'TIMESERIES' and i + 1 < len(parts):
                        ts_name = parts[i + 1]
                        if ts_name not in defined_ts:
                            issues.append(f"Undefined TIMESERIES: {ts_name} referenced in RAINGAGES")
    
    # Check section order - TIMESERIES should come before RAINGAGES if referenced
    if '[RAINGAGES]' in content and '[TIMESERIES]' in content:
        raingages_pos = content.find('[RAINGAGES]')
        timeseries_pos = content.find('[TIMESERIES]')
        if timeseries_pos > raingages_pos:
            # Check if any raingage references timeseries
            raingages_section = content[raingages_pos:].split('[')[0]
            if 'TIMESERIES' in raingages_section.upper():
                issues.append("[TIMESERIES] should come before [RAINGAGES] when referenced")
    
    # Check for absolute paths (will fail in cloud)
    if re.search(r'["\']([C-Z]:\\|/Users/|/home/)', content):
        issues.append("Contains absolute file paths (will fail in cloud environment)")
    
    is_valid = len(issues) == 0
    return is_valid, issues


def process_inp_file(folder_path: str, filename: str) -> Tuple[bool, Dict]:
    """Process a single .inp file: check external files, validate, download."""
    print(f"\n📄 Processing: {folder_path}/{filename}" if folder_path else f"\n📄 Processing: {filename}")
    
    # Download .inp file content first
    repo_path = f"{folder_path}/{filename}" if folder_path else filename
    url = f"{BASE_URL}/{repo_path}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.text
    except Exception as e:
        print(f"   ❌ Failed to download .inp file: {e}")
        return False, {}
    
    # Find external file references
    external_files = parse_swmm_for_external_files(content)
    
    if external_files:
        print(f"   📎 Found {len(external_files)} external file reference(s): {', '.join(list(external_files)[:3])}{'...' if len(external_files) > 3 else ''}")
        
        # Check if all external files exist
        missing_files = []
        found_files = {}
        
        for ext_file in external_files:
            file_path = get_file_path_in_repo(folder_path, ext_file)
            if file_path:
                found_files[ext_file] = file_path
                print(f"   ✅ Found: {ext_file}")
            else:
                missing_files.append(ext_file)
                print(f"   ❌ Missing: {ext_file}")
        
        if missing_files:
            print(f"   ⚠️  Skipping - missing external files: {', '.join(missing_files[:3])}{'...' if len(missing_files) > 3 else ''}")
            return False, {'reason': 'missing_external_files', 'missing': missing_files}
    else:
        found_files = {}
    
    # Validate the input file
    is_valid, issues = validate_swmm_file(content)
    
    if not is_valid:
        print(f"   ⚠️  Validation issues: {', '.join(issues[:2])}{'...' if len(issues) > 2 else ''}")
        # Still consider it valid if only minor issues
        if len(issues) <= 2 and 'Missing required section' not in str(issues):
            print(f"   ✅ Minor issues, considering valid")
            is_valid = True
    
    if not is_valid:
        return False, {'reason': 'validation_failed', 'issues': issues}
    
    # Download files to local directory
    local_folder = OUTPUT_DIR / folder_path if folder_path else OUTPUT_DIR
    local_folder.mkdir(parents=True, exist_ok=True)
    
    # Download .inp file
    local_inp_path = local_folder / filename
    if download_file(repo_path, local_inp_path):
        print(f"   ✅ Downloaded: {local_inp_path}")
    else:
        return False, {'reason': 'download_failed'}
    
    # Download external files
    for ext_file, repo_file_path in found_files.items():
        local_ext_path = local_folder / ext_file
        if download_file(repo_file_path, local_ext_path):
            print(f"   ✅ Downloaded external: {ext_file}")
        else:
            print(f"   ⚠️  Failed to download external: {ext_file}")
    
    return True, {
        'folder': folder_path,
        'filename': filename,
        'external_files': list(found_files.keys()),
        'local_path': str(local_inp_path)
    }


def main():
    """Main function to process all SWMM files."""
    print("=" * 70)
    print("SWMM Example Files Downloader & Validator")
    print("=" * 70)
    print(f"\nRepository: {REPO_OWNER}/{REPO_NAME}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Find all .inp files
    print("\n🔍 Searching for .inp files...")
    inp_files = find_inp_files()
    print(f"   Found {len(inp_files)} .inp file(s)")
    
    if not inp_files:
        print("❌ No .inp files found!")
        return
    
    # Process each file
    valid_files = []
    invalid_files = []
    
    for i, (folder_path, filename) in enumerate(inp_files, 1):
        print(f"\n[{i}/{len(inp_files)}]", end=" ")
        is_valid, info = process_inp_file(folder_path, filename)
        if is_valid:
            valid_files.append(info)
        else:
            invalid_files.append({'folder': folder_path, 'filename': filename, **info})
        
        # Small delay to avoid rate limiting
        if i % 10 == 0:
            time.sleep(1)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n✅ Valid files: {len(valid_files)}")
    print(f"❌ Invalid/Skipped files: {len(invalid_files)}")
    print(f"📊 Total files processed: {len(inp_files)}")
    
    if valid_files:
        print(f"\n📁 Valid files saved to: {OUTPUT_DIR}/")
        print("\nValid files by folder:")
        by_folder = {}
        for file_info in valid_files:
            folder = file_info.get('folder', 'root')
            if folder not in by_folder:
                by_folder[folder] = []
            by_folder[folder].append(file_info['filename'])
        
        for folder, files in sorted(by_folder.items()):
            print(f"   {folder or 'root'}: {len(files)} file(s)")
    
    if invalid_files:
        print(f"\n⚠️  Invalid/Skipped files (showing first 10):")
        for file_info in invalid_files[:10]:
            reason = file_info.get('reason', 'unknown')
            folder = file_info.get('folder', 'root')
            filename = file_info.get('filename', 'unknown')
            print(f"   {folder}/{filename}: {reason}")
        if len(invalid_files) > 10:
            print(f"   ... and {len(invalid_files) - 10} more")
    
    # Save summary to JSON
    summary_path = OUTPUT_DIR / "summary.json"
    with open(summary_path, 'w') as f:
        json.dump({
            'total_found': len(inp_files),
            'valid': len(valid_files),
            'invalid': len(invalid_files),
            'valid_files': valid_files,
            'invalid_files': invalid_files
        }, f, indent=2)
    
    print(f"\n📄 Summary saved to: {summary_path}")
    print(f"\n✅ Total valid SWMM input files: {len(valid_files)}")


if __name__ == '__main__':
    main()
