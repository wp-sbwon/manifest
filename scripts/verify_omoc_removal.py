#!/usr/bin/env python3
"""
Rule-based verification script for agent system refactoring.
Checks that all old agent references have been removed and replaced with new names.
"""
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Forbidden strings (case-insensitive)
FORBIDDEN_STRINGS = [
    r'\bprometheus\b',
    r'\bPrometheus\b',
    r'\bPROMETHEUS\b',
    r'\bsisyphus\b',
    r'\bSisyphus\b',
    r'\bSISYPHUS\b',
    r'\bomoc\b',
    r'\bOMOC\b',
    r'Oh My Open Code',
    r'OMOCBridge',
    r'omoc_bridge',
    r'PrometheusAgent',
    r'SisyphusAgent',
]

# Allowed strings (exceptions)
ALLOWED_STRINGS = [
    'OpenCode',  # As per user request
]

# Required new strings (should exist)
REQUIRED_NEW_STRINGS = [
    r'\borchestrator\b',
    r'\bplanner\b',
    r'\bcoder\b',
    r'AgentBridge',
    r'agent_bridge',
    r'OrchestratorAgent',
    r'PlannerAgent',
    r'CoderAgent',
]

# File patterns to check
PYTHON_FILES = ['**/*.py']
CONFIG_FILES = ['docker-compose.yml', '.manifest/agent_config.json']
DOC_FILES = ['docs/**/*.md']

# Directories to exclude
EXCLUDE_DIRS = {'.git', '__pycache__', '.pytest_cache', 'venv', 'node_modules', '.manifest'}


class VerificationError(Exception):
    """Custom exception for verification failures."""
    pass


def should_check_file(file_path: Path) -> bool:
    """Check if file should be verified."""
    # Exclude certain directories
    for part in file_path.parts:
        if part in EXCLUDE_DIRS:
            return False

    # Exclude the verification script itself
    if 'verify_omoc_removal.py' in str(file_path):
        return False

    # Exclude reference/implementation_plan.md (historical reference document)
    if 'reference/implementation_plan.md' in str(file_path):
        return False

    # Only check Python, config, and doc files
    if file_path.suffix in ['.py', '.yml', '.yaml', '.json', '.md']:
        return True

    return False


def check_file_for_forbidden_strings(file_path: Path) -> List[Tuple[int, str, str]]:
    """Check file for forbidden strings."""
    violations = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                # Check each forbidden string
                for pattern in FORBIDDEN_STRINGS:
                    # Skip if it's an allowed string
                    is_allowed = False
                    for allowed in ALLOWED_STRINGS:
                        if allowed.lower() in pattern.lower() or pattern.lower() in allowed.lower():
                            # Check if the line contains the allowed string
                            if allowed in line:
                                is_allowed = True
                                break

                    if is_allowed:
                        continue

                    # Check for matches
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append((line_num, pattern, line.strip()))

    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")

    return violations


def check_file_for_required_strings(file_path: Path) -> bool:
    """Check if file contains required new strings (for key files)."""
    # Only check key files
    key_files = [
        'src/manifest/bridge/agent_bridge.py',
        'src/manifest/runtime/agent/orchestrator_agent.py',
        'src/manifest/runtime/agent/planner_agent.py',
        'src/manifest/runtime/agent/coder_agent.py',
    ]

    if str(file_path) not in key_files:
        return True  # Not a key file, skip

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

            # Check if at least one required string exists
            for pattern in REQUIRED_NEW_STRINGS:
                if re.search(pattern, content, re.IGNORECASE):
                    return True

        return False
    except Exception:
        return True  # File doesn't exist or can't be read, skip


def check_file_names(root_dir: Path) -> List[str]:
    """Check for forbidden file names."""
    violations = []

    forbidden_names = ['prometheus', 'sisyphus', 'omoc']

    for file_path in root_dir.rglob('*'):
        if not file_path.is_file():
            continue

        # Skip excluded directories
        if any(part in EXCLUDE_DIRS for part in file_path.parts):
            continue

        file_name = file_path.name.lower()
        for forbidden in forbidden_names:
            if forbidden in file_name:
                violations.append(str(file_path))

    return violations


def check_imports(root_dir: Path) -> List[Tuple[str, str]]:
    """Check for old import paths."""
    violations = []

    old_imports = [
        r'from manifest\.omoc\.',
        r'from manifest\.bridge\.omoc_bridge',
        r'import.*omoc_bridge',
        r'from.*prometheus',
        r'from.*sisyphus',
    ]

    for file_path in root_dir.rglob('*.py'):
        if not should_check_file(file_path):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

                for line_num, line in enumerate(lines, 1):
                    for pattern in old_imports:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Check if it's an allowed exception
                            if 'OpenCode' in line:
                                continue
                            violations.append((str(file_path), f"Line {line_num}: {line.strip()}"))
        except Exception:
            pass

    return violations


def check_config_files(root_dir: Path) -> List[str]:
    """Check configuration files."""
    violations = []

    # Check docker-compose.yml
    docker_compose = root_dir / 'docker-compose.yml'
    if docker_compose.exists():
        with open(docker_compose, 'r') as f:
            content = f.read()
            if 'prometheus' in content.lower() or 'sisyphus' in content.lower():
                violations.append('docker-compose.yml contains old agent names')

    # Check agent_config.json
    agent_config = root_dir / '.manifest' / 'agent_config.json'
    if agent_config.exists():
        with open(agent_config, 'r') as f:
            content = f.read()
            if 'prometheus' in content.lower() or 'sisyphus' in content.lower():
                violations.append('.manifest/agent_config.json contains old agent names')

    return violations


def main():
    """Main verification function."""
    root_dir = Path(__file__).parent.parent
    os.chdir(root_dir)

    print("🔍 Starting OMOC removal verification...")
    print(f"📁 Root directory: {root_dir}\n")

    all_violations = []

    # 1. Check file names
    print("1. Checking file names...")
    file_name_violations = check_file_names(root_dir)
    # Filter out verification script itself (it contains "omoc" in its name for historical reasons)
    file_name_violations = [v for v in file_name_violations if 'verify_omoc_removal.py' not in v]
    if file_name_violations:
        print(f"   ❌ Found {len(file_name_violations)} files with forbidden names:")
        for violation in file_name_violations:
            print(f"      - {violation}")
        all_violations.extend(file_name_violations)
    else:
        print("   ✅ No forbidden file names found")

    # 2. Check file content
    print("\n2. Checking file content for forbidden strings...")
    content_violations = []
    for file_path in root_dir.rglob('*'):
        if not should_check_file(file_path):
            continue

        violations = check_file_for_forbidden_strings(file_path)
        if violations:
            content_violations.append((file_path, violations))

    if content_violations:
        print(f"   ❌ Found violations in {len(content_violations)} files:")
        for file_path, violations in content_violations:
            print(f"      - {file_path}:")
            for line_num, pattern, line in violations[:5]:  # Show first 5
                print(f"        Line {line_num}: {line[:80]}")
            if len(violations) > 5:
                print(f"        ... and {len(violations) - 5} more")
        all_violations.extend([str(fp) for fp, _ in content_violations])
    else:
        print("   ✅ No forbidden strings found in file content")

    # 3. Check imports
    print("\n3. Checking imports...")
    import_violations = check_imports(root_dir)
    if import_violations:
        print(f"   ❌ Found {len(import_violations)} old import statements:")
        for file_path, violation in import_violations[:10]:  # Show first 10
            print(f"      - {file_path}: {violation}")
        if len(import_violations) > 10:
            print(f"      ... and {len(import_violations) - 10} more")
        all_violations.extend([fp for fp, _ in import_violations])
    else:
        print("   ✅ No old import statements found")

    # 4. Check config files
    print("\n4. Checking configuration files...")
    config_violations = check_config_files(root_dir)
    if config_violations:
        print(f"   ❌ Found {len(config_violations)} config violations:")
        for violation in config_violations:
            print(f"      - {violation}")
        all_violations.extend(config_violations)
    else:
        print("   ✅ Configuration files are clean")

    # 5. Check for required new strings (key files)
    print("\n5. Checking for required new strings in key files...")
    key_files = [
        root_dir / 'src/manifest/bridge/agent_bridge.py',
        root_dir / 'src/manifest/runtime/agent/orchestrator_agent.py',
        root_dir / 'src/manifest/runtime/agent/planner_agent.py',
        root_dir / 'src/manifest/runtime/agent/coder_agent.py',
    ]

    missing_new_strings = []
    for key_file in key_files:
        if not key_file.exists():
            missing_new_strings.append(str(key_file))
        elif not check_file_for_required_strings(key_file):
            missing_new_strings.append(str(key_file))

    if missing_new_strings:
        print(f"   ❌ Key files missing required new strings:")
        for file_path in missing_new_strings:
            print(f"      - {file_path}")
        all_violations.extend(missing_new_strings)
    else:
        print("   ✅ All key files contain required new strings")

    # Summary
    print("\n" + "="*60)
    if all_violations:
        print(f"❌ VERIFICATION FAILED: Found {len(set(all_violations))} violations")
        print("\nPlease fix all violations before proceeding.")
        return 1
    else:
        print("✅ VERIFICATION PASSED: No violations found!")
        print("\nAll OMOC references have been successfully removed.")
        return 0


if __name__ == '__main__':
    sys.exit(main())
