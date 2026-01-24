"""
Architecture Metadata Utilities - Ensures architecture.json has proper schema.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


def ensure_architecture_metadata(architecture: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure architecture.json has required metadata and schema extensions.
    
    Schema extensions:
    - Features have components list and completion_percentage
    - Requirements have components list
    - Components are linked to Features and Requirements
    
    Args:
        architecture: Architecture dictionary
    
    Returns:
        Architecture with metadata ensured
    """
    if "version" not in architecture:
        architecture["version"] = "1.0"
    
    if "source" not in architecture:
        architecture["source"] = "llm_architecture"
    
    if "ground_truth" not in architecture:
        architecture["ground_truth"] = False
    
    if "last_updated" not in architecture:
        architecture["last_updated"] = datetime.utcnow().isoformat()
    
    # Ensure features have required fields
    if "features" not in architecture:
        architecture["features"] = []
    
    for feature in architecture["features"]:
        if "components" not in feature:
            feature["components"] = []
        if "completion_percentage" not in feature:
            feature["completion_percentage"] = 0
        if "status" not in feature:
            feature["status"] = "pending"
        
        # Ensure requirements have components list
        if "requirements" not in feature:
            feature["requirements"] = []
        
        for req in feature.get("requirements", []):
            if "components" not in req:
                req["components"] = []
            if "state" not in req:
                req["state"] = "pending"
    
    # Ensure requirements list exists (top-level)
    if "requirements" not in architecture:
        architecture["requirements"] = []
    
    for req in architecture["requirements"]:
        if "components" not in req:
            req["components"] = []
        if "state" not in req:
            req["state"] = "pending"
    
    # Ensure goals list exists
    if "goals" not in architecture:
        architecture["goals"] = []
    
    return architecture


def load_architecture_with_metadata(architecture_file: Path) -> Dict[str, Any]:
    """
    Load architecture.json file and ensure it has metadata and schema extensions.
    
    Args:
        architecture_file: Path to architecture.json file
    
    Returns:
        Architecture dictionary with metadata
    """
    if not architecture_file.exists():
        return {
            "version": "1.0",
            "source": "llm_architecture",
            "ground_truth": False,
            "last_updated": datetime.utcnow().isoformat(),
            "extraction_method": "llm_inference",
            "features": [],
            "requirements": [],
            "goals": []
        }
    
    try:
        with open(architecture_file, "r", encoding="utf-8") as f:
            architecture = json.load(f)
        
        # Ensure metadata and schema
        architecture = ensure_architecture_metadata(architecture)
        
        return architecture
    except Exception:
        # Return default architecture with metadata
        return {
            "version": "1.0",
            "source": "llm_architecture",
            "ground_truth": False,
            "last_updated": datetime.utcnow().isoformat(),
            "extraction_method": "llm_inference",
            "features": [],
            "requirements": [],
            "goals": []
        }


def save_architecture_with_metadata(architecture: Dict[str, Any], architecture_file: Path) -> bool:
    """
    Save architecture.json file with metadata.
    
    Args:
        architecture: Architecture dictionary
        architecture_file: Path to save architecture
    
    Returns:
        True if successful, False otherwise
    """
    try:
        architecture = ensure_architecture_metadata(architecture)
        architecture["last_updated"] = datetime.utcnow().isoformat()
        
        architecture_file.parent.mkdir(parents=True, exist_ok=True)
        with open(architecture_file, "w", encoding="utf-8") as f:
            json.dump(architecture, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
