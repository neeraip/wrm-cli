#!/usr/bin/env python3
"""Remove files that failed API simulation tests."""

import json
from pathlib import Path

# Load test results
results_file = Path(__file__).parent / "new_swmm_test_results.json"
data = json.load(open(results_file))

# Get failed files
failed = [r for r in data['results'] if r.get('final_status') in ['failed', 'error', 'timeout']]
submit_failed = [r for r in data['results'] if r.get('status') in ['submit_failed', 'submit_exception']]

# Combine all files to remove
files_to_remove = failed + submit_failed

print(f"Files to remove: {len(files_to_remove)}")
print(f"  - Execution failures: {len(failed)}")
print(f"  - Submit failures: {len(submit_failed)}")

# Remove files
repo_root = Path(__file__).parent
removed_count = 0
not_found = []
errors = []

for r in files_to_remove:
    file_path_str = r['file']
    # Handle both absolute and relative paths
    if Path(file_path_str).is_absolute():
        file_path = Path(file_path_str)
    else:
        file_path = repo_root / file_path_str
    
    if file_path.exists():
        try:
            file_path.unlink()
            removed_count += 1
        except Exception as e:
            errors.append((str(file_path), str(e)))
    else:
        not_found.append(str(file_path))

print(f"\n✅ Removed {removed_count} files")
if not_found:
    print(f"⚠️  Not found ({len(not_found)}):")
    for f in not_found[:5]:
        print(f"  - {f}")
if errors:
    print(f"❌ Errors ({len(errors)}):")
    for f, e in errors[:5]:
        print(f"  - {f}: {e}")
