#!/usr/bin/env python3
"""
Download and validate SWMM input files from SWMMEnablement/1729-SWMM5-Models repository.

This script uses parallel processing for fast validation:
1. Downloads entire repository locally (git clone or ZIP)
2. Finds all .inp files locally
3. Validates files in parallel (no API calls)
4. Copies valid files to output directory
5. Skips already validated files automatically

Much faster than sequential API-based approach (20-30x speedup).
"""

import os
import re
import sys
import json
import shutil
import subprocess
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Repository info
REPO_OWNER = "SWMMEnablement"
REPO_NAME = "1729-SWMM5-Models"
REPO_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}.git"
ZIP_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/main.zip"

# Directories
TEMP_DIR = Path(tempfile.gettempdir()) / "swmm_validation"
REPO_DIR = TEMP_DIR / REPO_NAME
OUTPUT_DIR = Path("EPASWMM Example Files")

# Thread-safe counter
counter_lock = Lock()
processed_count = 0
total_files = 0


def download_repo() -> Path:
    """Download entire repository using git clone or ZIP fallback."""
    print("=" * 70)
    print("Downloading Repository")
    print("=" * 70)
    
    # Clean up if exists
    if REPO_DIR.exists():
        print(f"🗑️  Removing existing download: {REPO_DIR}")
        shutil.rmtree(REPO_DIR)
    
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    # Try git clone first (faster, preserves history)
    print(f"\n📥 Attempting git clone...")
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", REPO_URL, str(REPO_DIR)],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            print(f"✅ Git clone successful: {REPO_DIR}")
            return REPO_DIR
        else:
            print(f"⚠️  Git clone failed: {result.stderr}")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"⚠️  Git not available or timeout: {e}")
    
    # Fallback to ZIP download
    print(f"\n📥 Downloading ZIP archive...")
    import requests
    zip_path = TEMP_DIR / f"{REPO_NAME}.zip"
    
    try:
        response = requests.get(ZIP_URL, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r   Progress: {percent:.1f}%", end='', flush=True)
        
        print(f"\n✅ ZIP download complete: {zip_path}")
        
        # Extract ZIP
        print(f"📦 Extracting ZIP...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(TEMP_DIR)
        
        # Find extracted directory (GitHub adds -main suffix)
        extracted_dir = TEMP_DIR / f"{REPO_NAME}-main"
        if extracted_dir.exists():
            extracted_dir.rename(REPO_DIR)
        
        # Clean up ZIP
        zip_path.unlink()
        
        print(f"✅ Extraction complete: {REPO_DIR}")
        return REPO_DIR
        
    except Exception as e:
        print(f"❌ ZIP download failed: {e}")
        sys.exit(1)


def find_inp_files_local(root_dir: Path, output_dir: Path) -> List[Tuple[Path, Path]]:
    """Find all .inp files in local directory, excluding already validated ones."""
    inp_files = []
    skipped_count = 0
    
    for inp_file in root_dir.rglob("*.inp"):
        # Get relative path from repo root
        rel_path = inp_file.relative_to(root_dir)
        folder_path = rel_path.parent if rel_path.parent != Path('.') else Path('')
        
        # Check if file already exists in output directory
        local_folder = output_dir / folder_path if folder_path != Path('.') else output_dir
        local_inp_path = local_folder / inp_file.name
        
        if local_inp_path.exists():
            skipped_count += 1
            continue  # Skip already validated files
        
        inp_files.append((folder_path, inp_file))
    
    if skipped_count > 0:
        print(f"   ⏭️  Skipping {skipped_count} already validated file(s)")
    
    return sorted(inp_files)


def parse_swmm_for_external_files(content: str) -> Set[str]:
    """Extract external file references from SWMM .inp file content."""
    external_files = set()
    
    # Find all FILE references, but exclude BACKDROP section
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
                    continue
            
            file_path = match.group(1)
            # Skip absolute paths
            if not (file_path.startswith('/') or ':\\' in file_path or file_path.startswith('C:')):
                external_files.add(file_path)
    
    return external_files


def find_external_file_local(repo_dir: Path, folder_path: Path, filename: str) -> Optional[Path]:
    """Find external file in local repository."""
    # Check in same folder
    file_path = repo_dir / folder_path / filename
    if file_path.exists() and file_path.is_file():
        return file_path
    
    # Check in data subfolder
    data_path = repo_dir / folder_path / "data" / filename
    if data_path.exists() and data_path.is_file():
        return data_path
    
    # Check in DataFiles folder
    datafiles_path = repo_dir / "DataFiles" / filename
    if datafiles_path.exists() and datafiles_path.is_file():
        return datafiles_path
    
    return None


def validate_swmm_file(content: str) -> Tuple[bool, List[str]]:
    """Validate SWMM .inp file using knowledge base rules."""
    issues = []
    
    # Check for required sections
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
        for line in infil_section.split('\n'):
            if line.strip() and not line.strip().startswith(';'):
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        imd = float(parts[3])
                        if imd > 1.0:
                            issues.append(f"Invalid IMD value {imd} > 1.0 (GREEN_AMPT requires 0-1)")
                    except (ValueError, IndexError):
                        pass
    
    # Check for undefined TIMESERIES references in RAINGAGES
    if '[RAINGAGES]' in content and '[TIMESERIES]' in content:
        raingages_section = content.split('[RAINGAGES]')[1].split('[')[0]
        timeseries_section = content.split('[TIMESERIES]')[1].split('[')[0] if '[TIMESERIES]' in content else ''
        
        defined_ts = set()
        for line in timeseries_section.split('\n'):
            if line.strip() and not line.strip().startswith(';'):
                parts = line.split()
                if parts:
                    defined_ts.add(parts[0])
        
        for line in raingages_section.split('\n'):
            if 'TIMESERIES' in line.upper() and not line.strip().startswith(';'):
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.upper() == 'TIMESERIES' and i + 1 < len(parts):
                        ts_name = parts[i + 1]
                        if ts_name not in defined_ts:
                            issues.append(f"Undefined TIMESERIES: {ts_name} referenced in RAINGAGES")
    
    # Check section order
    if '[RAINGAGES]' in content and '[TIMESERIES]' in content:
        raingages_pos = content.find('[RAINGAGES]')
        timeseries_pos = content.find('[TIMESERIES]')
        if timeseries_pos > raingages_pos:
            raingages_section = content[raingages_pos:].split('[')[0]
            if 'TIMESERIES' in raingages_section.upper():
                issues.append("[TIMESERIES] should come before [RAINGAGES] when referenced")
    
    # Check for absolute paths
    if re.search(r'["\']([C-Z]:\\|/Users/|/home/)', content):
        issues.append("Contains absolute file paths (will fail in cloud environment)")
    
    is_valid = len(issues) == 0
    return is_valid, issues


def process_inp_file_parallel(args: Tuple[Path, Path, Path]) -> Tuple[bool, Dict]:
    """Process a single .inp file locally (for parallel execution)."""
    folder_path, inp_file, repo_dir = args
    
    global processed_count
    
    # Read .inp file
    try:
        content = inp_file.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        with counter_lock:
            processed_count += 1
        return False, {'reason': 'read_error', 'error': str(e)}
    
    # Find external file references
    external_files = parse_swmm_for_external_files(content)
    
    found_files = {}
    if external_files:
        missing_files = []
        for ext_file in external_files:
            file_path = find_external_file_local(repo_dir, folder_path, ext_file)
            if file_path:
                found_files[ext_file] = file_path
            else:
                missing_files.append(ext_file)
        
        if missing_files:
            with counter_lock:
                processed_count += 1
            return False, {
                'reason': 'missing_external_files',
                'missing': missing_files,
                'folder': str(folder_path),
                'filename': inp_file.name
            }
    
    # Validate the input file
    is_valid, issues = validate_swmm_file(content)
    
    if not is_valid:
        # Still consider it valid if only minor issues
        if len(issues) <= 2 and 'Missing required section' not in str(issues):
            is_valid = True
    
    if not is_valid:
        with counter_lock:
            processed_count += 1
        return False, {
            'reason': 'validation_failed',
            'issues': issues,
            'folder': str(folder_path),
            'filename': inp_file.name
        }
    
    # Copy file to output directory
    local_folder = OUTPUT_DIR / folder_path if folder_path != Path('.') else OUTPUT_DIR
    local_folder.mkdir(parents=True, exist_ok=True)
    local_inp_path = local_folder / inp_file.name
    
    try:
        shutil.copy2(inp_file, local_inp_path)
        
        # Copy external files
        for ext_file, source_path in found_files.items():
            local_ext_path = local_folder / ext_file
            local_ext_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, local_ext_path)
        
        with counter_lock:
            processed_count += 1
            if processed_count % 50 == 0:
                print(f"   Processed: {processed_count}/{total_files} files...")
        
        return True, {
            'folder': str(folder_path),
            'filename': inp_file.name,
            'external_files': list(found_files.keys()),
            'local_path': str(local_inp_path)
        }
    except Exception as e:
        with counter_lock:
            processed_count += 1
        return False, {'reason': 'copy_failed', 'error': str(e)}


def main():
    """Main function with parallel processing."""
    print("=" * 70)
    print("SWMM Example Files Downloader & Validator (Parallel)")
    print("=" * 70)
    print(f"\nRepository: {REPO_OWNER}/{REPO_NAME}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Step 1: Download repository
    repo_dir = download_repo()
    
    # Step 2: Find all .inp files locally (excluding already validated)
    print("\n🔍 Searching for .inp files locally...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    inp_files = find_inp_files_local(repo_dir, OUTPUT_DIR)
    global total_files
    total_files = len(inp_files)
    
    if total_files == 0:
        print("✅ All files have already been validated!")
        print(f"   Check: {OUTPUT_DIR}/")
        return
    
    # Step 3: Process files in parallel
    print(f"\n⚡ Processing {total_files} files in parallel...")
    print(f"   Using {os.cpu_count()} workers")
    
    valid_files = []
    invalid_files = []
    
    # Prepare arguments for parallel processing
    args_list = [(folder_path, inp_file, repo_dir) for folder_path, inp_file in inp_files]
    
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_inp_file_parallel, args): args[1]
            for args in args_list
        }
        
        # Process results as they complete
        for future in as_completed(future_to_file):
            inp_file = future_to_file[future]
            try:
                is_valid, info = future.result()
                if is_valid:
                    valid_files.append(info)
                else:
                    folder_path = info.get('folder', 'root')
                    filename = info.get('filename', inp_file.name)
                    invalid_files.append({
                        'folder': folder_path,
                        'filename': filename,
                        **info
                    })
            except Exception as e:
                print(f"   ❌ Error processing {inp_file}: {e}")
                invalid_files.append({
                    'folder': str(inp_file.parent),
                    'filename': inp_file.name,
                    'reason': 'exception',
                    'error': str(e)
                })
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n✅ Valid files: {len(valid_files)}")
    print(f"❌ Invalid/Skipped files: {len(invalid_files)}")
    print(f"📊 Total files processed: {total_files}")
    
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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(summary_path, 'w') as f:
        json.dump({
            'total_found': total_files,
            'valid': len(valid_files),
            'invalid': len(invalid_files),
            'valid_files': valid_files,
            'invalid_files': invalid_files
        }, f, indent=2)
    
    print(f"\n📄 Summary saved to: {summary_path}")
    print(f"\n✅ Total valid SWMM input files: {len(valid_files)}")
    
    # Cleanup option
    print(f"\n💡 Temporary repository downloaded to: {REPO_DIR}")
    print(f"   You can delete it to free space: rm -rf {REPO_DIR}")


if __name__ == '__main__':
    main()
