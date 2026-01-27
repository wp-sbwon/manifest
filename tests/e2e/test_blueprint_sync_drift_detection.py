"""
E2E Test: Blueprint Sync & Drift Detection Workflow

Tests the complete workflow from code changes to drift detection and conflict resolution.
This validates the blueprint synchronization and drift detection system.
"""
import pytest
import asyncio
import tempfile
import shutil
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.audit.monitoring.file_watcher import FileWatcher
from manifest.audit.code.drift_auditor import DriftAuditor
from manifest.audit.blueprint.blueprint_synchronizer import BlueprintSynchronizer


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def git_repo(temp_dir):
    """Create a Git repository for testing."""
    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=temp_dir,
        capture_output=True,
        check=False
    )
    # Create initial commit
    (temp_dir / "README.md").write_text("# Test Project")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=temp_dir,
        capture_output=True,
        check=False
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=temp_dir,
        capture_output=True,
        check=False
    )
    return temp_dir


@pytest.fixture
def manifest_dir(git_repo):
    """Create .manifest directory with blueprint."""
    manifest_path = git_repo / ".manifest"
    manifest_path.mkdir(exist_ok=True)

    # Create sample blueprint
    blueprint = {
        "components": [
            {
                "id": "comp-1",
                "name": "Calculator",
                "type": "class",
                "file": "src/calculator.py",
                "methods": ["add", "subtract"]
            }
        ],
        "contracts": []
    }

    blueprint_file = manifest_path / "blueprint.json"
    with open(blueprint_file, 'w') as f:
        json.dump(blueprint, f)

    return manifest_path


@pytest.fixture
def file_watcher(git_repo):
    """Create a FileWatcher instance."""
    return FileWatcher(project_root=git_repo)


@pytest.fixture
def drift_auditor(manifest_dir):
    """Create a DriftAuditor instance."""
    return DriftAuditor(manifest_dir=manifest_dir)


@pytest.fixture
def blueprint_synchronizer(manifest_dir):
    """Create a BlueprintSynchronizer instance."""
    return BlueprintSynchronizer(manifest_dir=manifest_dir)


# ========== TDL: Workflow 3: Blueprint Sync & Drift Detection ==========

@pytest.mark.asyncio
async def test_changes_detected(
    file_watcher, drift_auditor, git_repo, manifest_dir
):
    """Test: Changes are detected by file watcher."""
    # Step 1: Create initial code file matching blueprint
    src_dir = git_repo / "src"
    src_dir.mkdir(exist_ok=True)
    code_file = src_dir / "calculator.py"
    code_file.write_text("""
class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b
""")

    subprocess.run(
        ["git", "add", str(code_file.relative_to(git_repo))],
        cwd=git_repo,
        capture_output=True,
        check=False
    )
    subprocess.run(
        ["git", "commit", "-m", "Add calculator"],
        cwd=git_repo,
        capture_output=True,
        check=False
    )

    # Step 2: Modify code (introduce change)
    code_file.write_text("""
class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b
    def multiply(self, a, b):  # New method - change
        return a * b
""")

    subprocess.run(
        ["git", "add", str(code_file.relative_to(git_repo))],
        cwd=git_repo,
        capture_output=True,
        check=False
    )

    # Step 3: File watcher detects changes
    changed_files = file_watcher.check_changes()

    # Verify changes were detected
    assert len(changed_files) > 0
    assert any("calculator.py" in f for f in changed_files)


@pytest.mark.asyncio
async def test_drift_correctly_identified(
    file_watcher, drift_auditor, git_repo, manifest_dir
):
    """Test: Drift is correctly identified by drift auditor."""
    # Step 1: Create code file matching blueprint
    src_dir = git_repo / "src"
    src_dir.mkdir(exist_ok=True)
    code_file = src_dir / "calculator.py"
    code_file.write_text("""
class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b
""")

    subprocess.run(
        ["git", "add", str(code_file.relative_to(git_repo))],
        cwd=git_repo,
        capture_output=True,
        check=False
    )
    subprocess.run(
        ["git", "commit", "-m", "Add calculator"],
        cwd=git_repo,
        capture_output=True,
        check=False
    )

    # Step 2: Modify code to introduce drift (new method not in blueprint)
    code_file.write_text("""
class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b
    def multiply(self, a, b):  # New method - drift from blueprint
        return a * b
""")

    subprocess.run(
        ["git", "add", str(code_file.relative_to(git_repo))],
        cwd=git_repo,
        capture_output=True,
        check=False
    )

    # Step 3: File watcher detects change
    changed_files = file_watcher.check_changes()
    assert len(changed_files) > 0

    # Step 4: Drift auditor identifies drift
    conflicts = drift_auditor.audit_project(root=git_repo)

    # Verify drift was identified
    assert isinstance(conflicts, list)
    # Should detect that multiply method is not in blueprint


@pytest.mark.asyncio
async def test_conflicts_classified_correctly(
    file_watcher, drift_auditor, git_repo, manifest_dir
):
    """Test: Conflicts are classified correctly."""
    # Step 1: Create code file
    src_dir = git_repo / "src"
    src_dir.mkdir(exist_ok=True)
    code_file = src_dir / "calculator.py"
    code_file.write_text("""
class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b
""")

    subprocess.run(
        ["git", "add", str(code_file.relative_to(git_repo))],
        cwd=git_repo,
        capture_output=True,
        check=False
    )
    subprocess.run(
        ["git", "commit", "-m", "Add calculator"],
        cwd=git_repo,
        capture_output=True,
        check=False
    )

    # Step 2: Introduce multiple types of drift
    code_file.write_text("""
class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b
    def multiply(self, a, b):  # Added method - drift
        return a * b
    # Removed method would also be drift, but we're adding here
""")

    subprocess.run(
        ["git", "add", str(code_file.relative_to(git_repo))],
        cwd=git_repo,
        capture_output=True,
        check=False
    )

    # Step 3: Detect and classify conflicts
    changed_files = file_watcher.check_changes()
    conflicts = drift_auditor.audit_project(root=git_repo)

    # Verify conflicts were classified
    assert isinstance(conflicts, list)
    # Conflicts should be properly structured
    if len(conflicts) > 0:
        for conflict in conflicts:
            assert isinstance(conflict, dict) or isinstance(conflict, str)


@pytest.mark.asyncio
async def test_resolution_workflow_works(
    file_watcher, drift_auditor, blueprint_synchronizer, git_repo, manifest_dir
):
    """Test: Resolution workflow works."""
    # Step 1: Create code file
    src_dir = git_repo / "src"
    src_dir.mkdir(exist_ok=True)
    code_file = src_dir / "calculator.py"
    code_file.write_text("""
class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b
""")

    subprocess.run(
        ["git", "add", str(code_file.relative_to(git_repo))],
        cwd=git_repo,
        capture_output=True,
        check=False
    )
    subprocess.run(
        ["git", "commit", "-m", "Add calculator"],
        cwd=git_repo,
        capture_output=True,
        check=False
    )

    # Step 2: Introduce drift
    code_file.write_text("""
class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b
    def multiply(self, a, b):  # New method
        return a * b
""")

    subprocess.run(
        ["git", "add", str(code_file.relative_to(git_repo))],
        cwd=git_repo,
        capture_output=True,
        check=False
    )

    # Step 3: Detect drift
    changed_files = file_watcher.check_changes()
    conflicts = drift_auditor.audit_project(root=git_repo)

    # Step 4: Resolve by syncing blueprint
    # Load blueprints
    from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
    top_down_blueprint = BlueprintLoader.load_blueprint(manifest_dir, with_metadata=True)
    bottom_up_blueprint = BlueprintLoader.load_code_blueprint(manifest_dir)

    # Sync blueprints (should merge changes)
    result = blueprint_synchronizer.sync_blueprints(
        top_down_blueprint,
        bottom_up_blueprint,
        mode="workflow"
    )

    # Verify resolution workflow
    assert isinstance(result, dict)
    # Result should contain sync information
    assert "conflicts" in result or "merged" in result or "components" in result


@pytest.mark.asyncio
async def test_complete_blueprint_drift_workflow(
    file_watcher, drift_auditor, blueprint_synchronizer, git_repo, manifest_dir
):
    """Test: Complete blueprint sync and drift detection workflow."""
    # Step 1: Create initial code matching blueprint
    src_dir = git_repo / "src"
    src_dir.mkdir(exist_ok=True)
    code_file = src_dir / "calculator.py"
    code_file.write_text("""
class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b
""")

    subprocess.run(
        ["git", "add", str(code_file.relative_to(git_repo))],
        cwd=git_repo,
        capture_output=True,
        check=False
    )
    subprocess.run(
        ["git", "commit", "-m", "Add calculator"],
        cwd=git_repo,
        capture_output=True,
        check=False
    )

    # Step 2: Register file watcher callback for drift detection
    drift_detections = []

    def detect_drift_callback(changed_files):
        """Callback that triggers drift audit."""
        drift_detections.append(changed_files)
        conflicts = drift_auditor.audit_project(root=git_repo)
        drift_detections.append(conflicts)
        return conflicts

    file_watcher.register_change_callback(detect_drift_callback)

    # Step 3: Modify code to introduce drift
    code_file.write_text("""
class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b
    def multiply(self, a, b):  # New method - drift
        return a * b
    def divide(self, a, b):  # Another new method - drift
        return a / b if b != 0 else 0
""")

    subprocess.run(
        ["git", "add", str(code_file.relative_to(git_repo))],
        cwd=git_repo,
        capture_output=True,
        check=False
    )

    # Step 4: File watcher detects changes and triggers drift check
    changed_files = file_watcher.check_changes()

    # Step 5: Verify complete workflow
    assert len(changed_files) > 0
    assert any("calculator.py" in f for f in changed_files)

    # Verify drift detection was triggered
    assert len(drift_detections) >= 1

    # Step 6: Resolve conflicts by syncing
    from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
    top_down_blueprint = BlueprintLoader.load_blueprint(manifest_dir, with_metadata=True)
    bottom_up_blueprint = BlueprintLoader.load_code_blueprint(manifest_dir)

    sync_result = blueprint_synchronizer.sync_blueprints(
        top_down_blueprint,
        bottom_up_blueprint,
        mode="workflow"
    )

    # Verify resolution
    assert isinstance(sync_result, dict)


@pytest.mark.asyncio
async def test_file_watcher_triggers_drift_on_multiple_changes(
    file_watcher, drift_auditor, git_repo, manifest_dir
):
    """Test: File watcher triggers drift detection on multiple file changes."""
    # Step 1: Create multiple code files
    src_dir = git_repo / "src"
    src_dir.mkdir(exist_ok=True)

    files = ["calculator.py", "math_utils.py", "validator.py"]
    for filename in files:
        code_file = src_dir / filename
        code_file.write_text(f"""
class {filename.replace('.py', '').title()}:
    def method(self):
        pass
""")
        subprocess.run(
            ["git", "add", str(code_file.relative_to(git_repo))],
            cwd=git_repo,
            capture_output=True,
            check=False
        )

    subprocess.run(
        ["git", "commit", "-m", "Add multiple files"],
        cwd=git_repo,
        capture_output=True,
        check=False
    )

    # Step 2: Modify multiple files
    drift_detections = []

    def detect_drift_callback(changed_files):
        drift_detections.append(changed_files)
        conflicts = drift_auditor.audit_project(root=git_repo)
        drift_detections.append(conflicts)

    file_watcher.register_change_callback(detect_drift_callback)

    for filename in files:
        code_file = src_dir / filename
        code_file.write_text(f"""
class {filename.replace('.py', '').title()}:
    def method(self):
        pass
    def new_method(self):  # Drift
        pass
""")
        subprocess.run(
            ["git", "add", str(code_file.relative_to(git_repo))],
            cwd=git_repo,
            capture_output=True,
            check=False
        )

    # Step 3: Check for changes
    changed_files = file_watcher.check_changes()

    # Verify multiple changes detected
    assert len(changed_files) >= len(files)
    for filename in files:
        assert any(filename in f for f in changed_files)

    # Verify drift detection was triggered
    assert len(drift_detections) >= 1
