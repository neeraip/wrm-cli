#!/usr/bin/env python3
"""
Example: Validate SWMM/EPANET input files before submission.

This script checks for common issues that cause simulation failures:
- Missing external file references
- Invalid infiltration parameters
- Undefined object references
- Section order issues

Usage:
    python validate_input.py model.inp
"""

import sys
import re
from pathlib import Path


def validate_swmm_file(filepath: str) -> list:
    """Validate a SWMM input file and return list of issues."""
    issues = []
    
    with open(filepath, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Track defined objects
    defined_timeseries = set()
    defined_patterns = set()
    defined_curves = set()
    
    current_section = None
    section_order = []
    
    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()
        
        # Track sections
        if line_stripped.startswith('[') and line_stripped.endswith(']'):
            current_section = line_stripped[1:-1].upper()
            section_order.append(current_section)
        
        # Skip comments and empty lines
        if not line_stripped or line_stripped.startswith(';'):
            continue
        
        # Check for external file references
        if 'FILE' in line.upper() and ('"' in line or "'" in line):
            # Extract file path
            match = re.search(r'["\']([^"\']+)["\']', line)
            if match:
                file_ref = match.group(1)
                # Check if it's an absolute Windows path
                if ':\\' in file_ref or file_ref.startswith('/'):
                    issues.append({
                        'type': 'external_file',
                        'line': i,
                        'message': f"External file reference: {file_ref}",
                        'severity': 'warning',
                        'suggestion': "Include this file as auxiliary or use relative path"
                    })
        
        # Track TIMESERIES definitions
        if current_section == 'TIMESERIES':
            parts = line_stripped.split()
            if parts and not parts[0].startswith(';'):
                defined_timeseries.add(parts[0])
        
        # Track PATTERNS definitions
        if current_section == 'PATTERNS':
            parts = line_stripped.split()
            if parts and not parts[0].startswith(';'):
                defined_patterns.add(parts[0])
        
        # Track CURVES definitions
        if current_section == 'CURVES':
            parts = line_stripped.split()
            if parts and not parts[0].startswith(';'):
                defined_curves.add(parts[0])
        
        # Check INFILTRATION parameters (GREEN_AMPT)
        if current_section == 'INFILTRATION':
            parts = line_stripped.split()
            if len(parts) >= 4 and not parts[0].startswith(';'):
                try:
                    # For GREEN_AMPT: Suction, Ksat, IMD
                    # IMD should be between 0 and 1
                    imd = float(parts[3])
                    if imd > 1.0:
                        issues.append({
                            'type': 'invalid_parameter',
                            'line': i,
                            'message': f"IMD value {imd} > 1.0 (should be 0-1 for GREEN_AMPT)",
                            'severity': 'error',
                            'suggestion': "Set IMD to a value between 0 and 1 (e.g., 0.25)"
                        })
                except (ValueError, IndexError):
                    pass
        
        # Check RAINGAGES TIMESERIES references
        if current_section == 'RAINGAGES':
            if 'TIMESERIES' in line.upper():
                parts = line_stripped.split()
                ts_idx = None
                for j, p in enumerate(parts):
                    if p.upper() == 'TIMESERIES':
                        ts_idx = j + 1
                        break
                if ts_idx and ts_idx < len(parts):
                    ts_name = parts[ts_idx]
                    if ts_name not in defined_timeseries:
                        issues.append({
                            'type': 'undefined_reference',
                            'line': i,
                            'message': f"Undefined TIMESERIES: {ts_name}",
                            'severity': 'error',
                            'suggestion': f"Define '{ts_name}' in [TIMESERIES] section before [RAINGAGES]"
                        })
    
    # Check section order
    if 'RAINGAGES' in section_order and 'TIMESERIES' in section_order:
        if section_order.index('RAINGAGES') < section_order.index('TIMESERIES'):
            issues.append({
                'type': 'section_order',
                'line': 0,
                'message': "[RAINGAGES] appears before [TIMESERIES]",
                'severity': 'warning',
                'suggestion': "Move [TIMESERIES] section before [RAINGAGES]"
            })
    
    return issues


def validate_epanet_file(filepath: str) -> list:
    """Validate an EPANET input file and return list of issues."""
    issues = []
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check for external file references
    for match in re.finditer(r'FILE\s+["\']?([^"\'\s]+)["\']?', content, re.IGNORECASE):
        file_ref = match.group(1)
        if ':\\' in file_ref or file_ref.startswith('/'):
            issues.append({
                'type': 'external_file',
                'line': content[:match.start()].count('\n') + 1,
                'message': f"External file reference: {file_ref}",
                'severity': 'warning',
                'suggestion': "Include this file as auxiliary or use relative path"
            })
    
    return issues


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_input.py <input_file.inp>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not Path(filepath).exists():
        print(f"❌ File not found: {filepath}")
        sys.exit(1)
    
    print(f"🔍 Validating: {filepath}")
    print("=" * 60)
    
    # Determine file type by extension or content
    with open(filepath, 'r') as f:
        content = f.read(1000).upper()
    
    if '[JUNCTIONS]' in content or '[SUBCATCHMENTS]' in content:
        sim_type = 'SWMM'
        issues = validate_swmm_file(filepath)
    elif '[PIPES]' in content or '[TANKS]' in content:
        sim_type = 'EPANET'
        issues = validate_epanet_file(filepath)
    else:
        print("⚠️  Could not determine file type, trying SWMM validation")
        sim_type = 'SWMM'
        issues = validate_swmm_file(filepath)
    
    print(f"   File type: {sim_type}")
    print()
    
    if not issues:
        print("✅ No issues found!")
    else:
        errors = [i for i in issues if i['severity'] == 'error']
        warnings = [i for i in issues if i['severity'] == 'warning']
        
        if errors:
            print(f"❌ ERRORS ({len(errors)}):")
            for issue in errors:
                print(f"   Line {issue['line']}: {issue['message']}")
                print(f"      💡 {issue['suggestion']}")
            print()
        
        if warnings:
            print(f"⚠️  WARNINGS ({len(warnings)}):")
            for issue in warnings:
                print(f"   Line {issue['line']}: {issue['message']}")
                print(f"      💡 {issue['suggestion']}")
            print()
        
        print(f"Summary: {len(errors)} errors, {len(warnings)} warnings")
        
        if errors:
            sys.exit(1)


if __name__ == '__main__':
    main()
