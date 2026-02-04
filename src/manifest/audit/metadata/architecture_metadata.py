"""
Fix and load architecture.json so it has the right shape.

View needs: goals (list of {id, name, description, status}), metrics (code_quality, test_coverage, binary_size).
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

VIEW_GOALS_ITEM = {"id": "string", "name": "string", "description": "string", "status": "string"}
VIEW_METRICS_KEYS = ("code_quality", "test_coverage", "binary_size")


def ensure_architecture_metadata(architecture: Dict[str, Any]) -> Dict[str, Any]:
    """Fix architecture so it has version, features, goals, metrics. Goals become list of {id, name, description, status}."""
    if "version" not in architecture:
        architecture["version"] = "1.0"

    if "source" not in architecture:
        architecture["source"] = "llm_architecture"

    if "from_actual_code" not in architecture:
        architecture["from_actual_code"] = architecture.get("ground_truth", False)
    if "ground_truth" not in architecture:
        architecture["ground_truth"] = architecture.get("from_actual_code", False)

    if "last_updated" not in architecture:
        architecture["last_updated"] = datetime.utcnow().isoformat()

    if "mission" not in architecture:
        architecture["mission"] = ""
    if "global_rules" not in architecture:
        architecture["global_rules"] = []
    if "architecture_style" not in architecture:
        architecture["architecture_style"] = ""

    if "features" not in architecture:
        architecture["features"] = []

    for feature in architecture["features"]:
        if not isinstance(feature, dict):
            continue
        if "components" not in feature:
            feature["components"] = []
        if "completion_percentage" not in feature:
            feature["completion_percentage"] = 0
        if "status" not in feature:
            feature["status"] = "pending"
        if "requirements" not in feature:
            feature["requirements"] = []

        for req in feature.get("requirements", []):
            if isinstance(req, dict):
                if "components" not in req:
                    req["components"] = []
                if "state" not in req:
                    req["state"] = "pending"

    if "requirements" not in architecture:
        architecture["requirements"] = []

    for req in architecture["requirements"]:
        if isinstance(req, dict):
            if "components" not in req:
                req["components"] = []
            if "state" not in req:
                req["state"] = "pending"

    if "goals" not in architecture:
        architecture["goals"] = []
    fixed_goals: List[Dict[str, Any]] = []
    for i, g in enumerate(architecture["goals"]):
        if isinstance(g, dict):
            fixed_goals.append({
                "id": g.get("id") or f"goal_{i+1}",
                "name": (g.get("name") or g.get("id") or f"Goal {i+1}").strip() or f"Goal {i+1}",
                "description": (g.get("description") or "").strip(),
                "status": (g.get("status") or "Planned").strip() or "Planned",
            })
        else:
            fixed_goals.append({"id": f"goal_{i+1}", "name": str(g)[:80], "description": "", "status": "Planned"})
    architecture["goals"] = fixed_goals

    if "metrics" not in architecture:
        architecture["metrics"] = {}
    if not isinstance(architecture["metrics"], dict):
        architecture["metrics"] = {}

    return architecture


def load_architecture_with_metadata(architecture_file: Path) -> Dict[str, Any]:
    """Load architecture.json and fix shape (goals, metrics)."""
    if not architecture_file.exists():
        return {
            "version": "1.0",
            "source": "llm_architecture",
            "ground_truth": False,
            "last_updated": datetime.utcnow().isoformat(),
            "extraction_method": "llm_inference",
            "features": [],
            "requirements": [],
            "goals": [],
            "metrics": {},
        }

    try:
        with open(architecture_file, "r", encoding="utf-8") as f:
            architecture = json.load(f)

        architecture = ensure_architecture_metadata(architecture)

        return architecture
    except Exception:
        return {
            "version": "1.0",
            "source": "llm_architecture",
            "ground_truth": False,
            "last_updated": datetime.utcnow().isoformat(),
            "extraction_method": "llm_inference",
            "features": [],
            "requirements": [],
            "goals": [],
            "metrics": {},
        }


def save_architecture_with_metadata(architecture: Dict[str, Any], architecture_file: Path) -> bool:
    """Save architecture.json (fix shape first)."""
    try:
        architecture = ensure_architecture_metadata(architecture)
        architecture["last_updated"] = datetime.utcnow().isoformat()

        architecture_file.parent.mkdir(parents=True, exist_ok=True)
        with open(architecture_file, "w", encoding="utf-8") as f:
            json.dump(architecture, f, indent=2, ensure_ascii=False)
        from manifest.core.design_history import record_design_save
        record_design_save(architecture_file.parent, "architecture", "architecture.json")
        return True
    except Exception:
        return False
