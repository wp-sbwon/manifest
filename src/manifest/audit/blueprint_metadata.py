"""
Blueprint Metadata Utilities - Ensures blueprint JSON files have proper metadata.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


def ensure_blueprint_metadata(blueprint: Dict[str, Any], source: str, 
                              ground_truth: bool, extraction_method: str = None) -> Dict[str, Any]:
    """
    Ensure blueprint has required metadata fields.
    
    Args:
        blueprint: Blueprint dictionary
        source: "code_extraction" | "llm_design" | "llm_architecture"
        ground_truth: True if ground truth, False otherwise
        extraction_method: "ast_parsing" | "llm_inference" | "manual"
    
    Returns:
        Blueprint with metadata ensured
    """
    if "version" not in blueprint:
        blueprint["version"] = "1.0"
    
    blueprint["source"] = source
    blueprint["ground_truth"] = ground_truth
    
    if "last_updated" not in blueprint:
        blueprint["last_updated"] = datetime.utcnow().isoformat()
    
    if extraction_method:
        blueprint["extraction_method"] = extraction_method
    elif "extraction_method" not in blueprint:
        if source == "code_extraction":
            blueprint["extraction_method"] = "ast_parsing"
        elif source in ["llm_design", "llm_architecture"]:
            blueprint["extraction_method"] = "llm_inference"
        else:
            blueprint["extraction_method"] = "manual"
    
    return blueprint


def load_blueprint_with_metadata(blueprint_file: Path, default_source: str = "llm_design",
                                 default_ground_truth: bool = False) -> Dict[str, Any]:
    """
    Load blueprint file and ensure it has metadata.
    
    Args:
        blueprint_file: Path to blueprint JSON file
        default_source: Default source if not present
        default_ground_truth: Default ground_truth if not present
    
    Returns:
        Blueprint dictionary with metadata
    """
    if not blueprint_file.exists():
        return {
            "version": "1.0",
            "source": default_source,
            "ground_truth": default_ground_truth,
            "last_updated": datetime.utcnow().isoformat(),
            "extraction_method": "llm_inference" if default_source.startswith("llm") else "ast_parsing",
            "zones": {"client": [], "server": [], "data": []},
            "components": [],
            "contracts": []
        }
    
    try:
        with open(blueprint_file, "r", encoding="utf-8") as f:
            blueprint = json.load(f)
        
        # Ensure metadata
        if blueprint_file.name == "blueprint_code.json":
            blueprint = ensure_blueprint_metadata(blueprint, "code_extraction", True, "ast_parsing")
        else:
            blueprint = ensure_blueprint_metadata(blueprint, default_source, default_ground_truth)
        
        return blueprint
    except Exception:
        # Return default blueprint with metadata
        return {
            "version": "1.0",
            "source": default_source,
            "ground_truth": default_ground_truth,
            "last_updated": datetime.utcnow().isoformat(),
            "extraction_method": "llm_inference" if default_source.startswith("llm") else "ast_parsing",
            "zones": {"client": [], "server": [], "data": []},
            "components": [],
            "contracts": []
        }


def save_blueprint_with_metadata(blueprint: Dict[str, Any], blueprint_file: Path,
                                 source: str, ground_truth: bool, 
                                 extraction_method: str = None) -> bool:
    """
    Save blueprint file with metadata.
    
    Args:
        blueprint: Blueprint dictionary
        blueprint_file: Path to save blueprint
        source: Source type
        ground_truth: Whether it's ground truth
        extraction_method: Extraction method
    
    Returns:
        True if successful, False otherwise
    """
    try:
        blueprint = ensure_blueprint_metadata(blueprint, source, ground_truth, extraction_method)
        blueprint["last_updated"] = datetime.utcnow().isoformat()
        
        blueprint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(blueprint_file, "w", encoding="utf-8") as f:
            json.dump(blueprint, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
