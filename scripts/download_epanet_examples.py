#!/usr/bin/env python3
"""
Download and validate EPANET input files from KIOS-Research/EPANET-Benchmarks repository.

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
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from urllib.parse import urljoin, urlparse

# Repository info
REPO_OWNER = "KIOS-Research"
REPO_NAME = "EPANET-Benchmarks"
BASE_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/master"
API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

# Output directory
OUTPUT_DIR = Path("EPANET Example Files")


def get_repo_contents(path: str = "") -> List[Dict]:
    """Get contents of a repository path."""
    url = f"{API_BASE}/contents/{path}" if path else f"{API_BASE}/contents"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"⚠️  Error fetching {path}: {e}")
        return []


def find_inp_files(folder_path: str = "") -> List[Tuple[str, str]]:
    """Recursively find all .inp files in repository."""
    inp_files = []
    
    def search_directory(path: str):
        contents = get_repo_contents(path)
        for item in contents:
            if item['type'] == 'file' and item['name'].endswith('.inp'):
                inp_files.append((path, item['name']))
            elif item['type'] == 'dir':
                # Recursively search subdirectories
                search_directory(f"{path}/{item['name']}" if path else item['name'])
    
    search_directory(folder_path)
    return inp_files


def parse_inp_for_external_files(content: str) -> Set[str]:
    """Extract external file references from .inp file content, excluding BACKDROP section."""
    external_files = set()
    
    # Find BACKDROP section boundaries
    backdrop_start = None
    backdrop_end = None
    
    if '[BACKDROP]' in content.upper():
        # Find the start of BACKDROP section
        backdrop_match = re.search(r'^\[BACKDROP\]', content, re.IGNORECASE | re.MULTILINE)
        if backdrop_match:
            backdrop_start = backdrop_match.start()
            # Find the next section after BACKDROP
            next_section = re.search(r'^\[', content[backdrop_match.end():], re.MULTILINE)
            if next_section:
                backdrop_end = backdrop_match.end() + next_section.start()
            else:
                backdrop_end = len(content)
    
    # Pattern for FILE references
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


def validate_inp_file(content: str) -> Tuple[bool, List[str]]:
    """Validate .inp file using knowledge base rules."""
    issues = []
    
    # Check for required sections
    required_sections = ['[JUNCTIONS]', '[PIPES]']
    for section in required_sections:
        if section not in content:
            issues.append(f"Missing required section: {section}")
    
    # Check for at least one tank or reservoir
    if '[TANKS]' not in content and '[RESERVOIRS]' not in content:
        issues.append("No tanks or reservoirs found (EPANET requires at least one fixed-grade node)")
    
    # Check for undefined references
    # Extract node names
    junctions = re.findall(r'^(\S+)\s+', content.split('[JUNCTIONS]')[1].split('[')[0] if '[JUNCTIONS]' in content else '', re.MULTILINE)
    pipes = re.findall(r'^(\S+)\s+(\S+)\s+(\S+)', content.split('[PIPES]')[1].split('[')[0] if '[PIPES]' in content else '', re.MULTILINE)
    
    # Check pipe node references
    if pipes:
        all_nodes = set(junctions)
        if '[TANKS]' in content:
            tanks = re.findall(r'^(\S+)\s+', content.split('[TANKS]')[1].split('[')[0], re.MULTILINE)
            all_nodes.update(tanks)
        if '[RESERVOIRS]' in content:
            reservoirs = re.findall(r'^(\S+)\s+', content.split('[RESERVOIRS]')[1].split('[')[0], re.MULTILINE)
            all_nodes.update(reservoirs)
        
        for pipe in pipes[:10]:  # Check first 10 pipes
            if len(pipe) >= 2:
                node1, node2 = pipe[0], pipe[1]
                if node1 not in all_nodes:
                    issues.append(f"Pipe references undefined node: {node1}")
                if node2 not in all_nodes:
                    issues.append(f"Pipe references undefined node: {node2}")
    
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
    external_files = parse_inp_for_external_files(content)
    
    if external_files:
        print(f"   📎 Found {len(external_files)} external file reference(s): {', '.join(external_files)}")
        
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
            print(f"   ⚠️  Skipping - missing external files: {', '.join(missing_files)}")
            return False, {'reason': 'missing_external_files', 'missing': missing_files}
    else:
        found_files = {}
    
    # Validate the input file
    is_valid, issues = validate_inp_file(content)
    
    if not is_valid:
        print(f"   ⚠️  Validation issues: {', '.join(issues)}")
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
    """Main function to process all EPANET files."""
    import sys
    
    # Check if we should re-process invalid files
    reprocess_invalid = '--reprocess-invalid' in sys.argv
    
    print("=" * 70)
    print("EPANET Example Files Downloader & Validator")
    print("=" * 70)
    print(f"\nRepository: {REPO_OWNER}/{REPO_NAME}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Load existing summary if re-processing
    files_to_process = []
    if reprocess_invalid:
        summary_path = OUTPUT_DIR / "summary.json"
        if summary_path.exists():
            print("\n🔄 Re-processing invalid files from previous run...")
            with open(summary_path, 'r') as f:
                summary = json.load(f)
            # Get files that were skipped due to missing external files
            for invalid in summary.get('invalid_files', []):
                if invalid.get('reason') == 'missing_external_files':
                    folder = invalid.get('folder', '')
                    filename = invalid.get('filename', '')
                    if folder and filename:
                        files_to_process.append((folder, filename))
            print(f"   Found {len(files_to_process)} files to re-process")
        else:
            print("⚠️  No previous summary found, processing all files...")
            reprocess_invalid = False
    
    if not reprocess_invalid:
        # Find all .inp files
        print("\n🔍 Searching for .inp files...")
        files_to_process = find_inp_files()
        print(f"   Found {len(files_to_process)} .inp file(s)")
    
    if not files_to_process:
        print("❌ No files to process!")
        return
    
    # Load existing valid files if re-processing
    existing_valid = []
    if reprocess_invalid:
        summary_path = OUTPUT_DIR / "summary.json"
        if summary_path.exists():
            with open(summary_path, 'r') as f:
                summary = json.load(f)
            existing_valid = summary.get('valid_files', [])
            print(f"   Keeping {len(existing_valid)} previously valid files")
    
    # Process each file
    valid_files = existing_valid.copy() if reprocess_invalid else []
    invalid_files = []
    
    for folder_path, filename in files_to_process:
        # Skip if already in valid files (when re-processing)
        if reprocess_invalid:
            already_valid = any(
                vf.get('folder') == folder_path and vf.get('filename') == filename
                for vf in existing_valid
            )
            if already_valid:
                continue
        
        is_valid, info = process_inp_file(folder_path, filename)
        if is_valid:
            valid_files.append(info)
        else:
            invalid_files.append({'folder': folder_path, 'filename': filename, **info})
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n✅ Valid files: {len(valid_files)}")
    print(f"❌ Invalid/Skipped files: {len(invalid_files)}")
    print(f"📊 Total files processed: {len(files_to_process)}")
    
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
            for f in files:
                print(f"      - {f}")
    
    if invalid_files:
        print(f"\n⚠️  Invalid/Skipped files:")
        for file_info in invalid_files[:10]:  # Show first 10
            reason = file_info.get('reason', 'unknown')
            folder = file_info.get('folder', 'root')
            filename = file_info.get('filename', 'unknown')
            print(f"   {folder}/{filename}: {reason}")
        if len(invalid_files) > 10:
            print(f"   ... and {len(invalid_files) - 10} more")
    
    # Save summary to JSON
    summary_path = OUTPUT_DIR / "summary.json"
    
    # Load existing summary to preserve total_found if re-processing
    total_found = len(files_to_process)
    if reprocess_invalid and summary_path.exists():
        with open(summary_path, 'r') as f:
            old_summary = json.load(f)
            total_found = old_summary.get('total_found', len(files_to_process))
    
    with open(summary_path, 'w') as f:
        json.dump({
            'total_found': total_found,
            'valid': len(valid_files),
            'invalid': len(invalid_files),
            'valid_files': valid_files,
            'invalid_files': invalid_files
        }, f, indent=2)
    
    print(f"\n📄 Summary saved to: {summary_path}")
    print(f"\n✅ Total valid EPANET input files: {len(valid_files)}")


if __name__ == '__main__':
    main()
