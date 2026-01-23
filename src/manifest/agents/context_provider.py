"""
Context Provider - Provides tiered context to agents.
Implements the Tiered Orchestration system:
- Tier 0: The Law (manifest-policy.md)
- Tier 1: The Intent (intent.json, architecture.json)
- Tier 2: The Blueprint (blueprint.json - scoped)
- Tier 3: Surgical Code (files - scoped)
- Skills: Agent skills (from agent_config.json and AGENTS.md)
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from manifest.agents.task_scoper import TaskScoper
from manifest.agents.skills_manager import SkillsManager


class ContextProvider:
    """Provides tiered context to agents."""
    
    def __init__(self, manifest_dir: Path = None, task_scoper: Optional[TaskScoper] = None, project_root: Path = None):
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.project_root = project_root or Path.cwd()
        self.task_scoper = task_scoper or TaskScoper(manifest_dir)
        self.skills_manager = SkillsManager(manifest_dir, self.project_root)
        self.policy_file = Path(".claude/rules/manifest-policy.md")
        self.intent_file = self.manifest_dir / "intent.json"
        self.architecture_file = self.manifest_dir / "architecture.json"
        self.blueprint_file = self.manifest_dir / "blueprint.json"
    
    def get_skills_context(self, agent_type: str, task_scope: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get skills context for an agent."""
        skills = self.skills_manager.get_skills_for_agent(agent_type, task_scope)
        return {
            "skills": skills,
            "skills_formatted": self.skills_manager.format_skills_for_prompt(skills),
            "skills_count": len(skills)
        }
    
    def get_orchestrator_context(self) -> Dict[str, Any]:
        """Context for orchestrator."""
        context = {
            "tier": "orchestrator",
            "tier_0": self._load_tier_0(),
            "tier_1": self._load_tier_1(),
            "skills": self.get_skills_context("orchestrator"),
            "version": "1.0"
        }
        return context
    
    def get_worker_context(self, task_id: str, agent_type: str) -> Dict[str, Any]:
        """Context for worker agents (scoped to task)."""
        # Get task scope
        task_context = self.task_scoper.get_task_context(task_id)
        
        # Get task scope for skills
        task_scope = {
            "components": task_context.get("components", []),
            "allowed_files": task_context.get("files", []),
            "allowed_modifications": task_context.get("allowed_modifications", []),
            "requirements": task_context.get("requirements", [])
        }
        
        context = {
            "tier": "worker",
            "task_id": task_id,
            "agent_type": agent_type,
            "tier_0": self._load_tier_0(),
            "tier_2": self._load_tier_2_scoped(task_context),
            "tier_3": self._load_tier_3_scoped(task_context),
            "task_scope": task_scope,
            "skills": self.get_skills_context(agent_type, task_scope),
            "version": "1.0"
        }
        return context
    
    def _load_tier_0(self) -> Dict[str, Any]:
        """Load Tier 0: The Law (manifest-policy.md)."""
        if self.policy_file.exists():
            try:
                with open(self.policy_file, "r", encoding="utf-8") as f:
                    content = f.read()
                return {
                    "source": ".claude/rules/manifest-policy.md",
                    "content": content,
                    "type": "policy"
                }
            except Exception as e:
                return {
                    "source": ".claude/rules/manifest-policy.md",
                    "content": f"Error loading policy: {e}",
                    "type": "policy",
                    "error": True
                }
        return {
            "source": ".claude/rules/manifest-policy.md",
            "content": "",
            "type": "policy",
            "missing": True
        }
    
    def _load_tier_1(self) -> Dict[str, Any]:
        """Load Tier 1: The Intent (intent.json, architecture.json)."""
        tier_1 = {}
        
        # Load intent.json
        if self.intent_file.exists():
            try:
                with open(self.intent_file, "r") as f:
                    tier_1["intent"] = json.load(f)
            except Exception:
                tier_1["intent"] = {"version": "1.0", "sprint": "", "features": []}
        else:
            tier_1["intent"] = {"version": "1.0", "sprint": "", "features": []}
        
        # Load architecture.json
        if self.architecture_file.exists():
            try:
                with open(self.architecture_file, "r") as f:
                    tier_1["architecture"] = json.load(f)
            except Exception:
                tier_1["architecture"] = {"version": "1.0", "features": [], "requirements": [], "goals": []}
        else:
            tier_1["architecture"] = {"version": "1.0", "features": [], "requirements": [], "goals": []}
        
        return tier_1
    
    def _load_tier_2_scoped(self, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Load Tier 2: The Blueprint (scoped to task)."""
        if not self.blueprint_file.exists():
            return {"version": "1.0", "zones": {}, "components": [], "contracts": []}
        
        try:
            with open(self.blueprint_file, "r") as f:
                blueprint_data = json.load(f)
        except Exception:
            return {"version": "1.0", "zones": {}, "components": [], "contracts": []}
        
        # Filter to scoped components
        scoped_components = task_context.get("components", [])
        component_ids = {comp.get("id") for comp in scoped_components if comp.get("id")}
        
        # Filter components
        all_components = blueprint_data.get("components", [])
        filtered_components = [
            comp for comp in all_components
            if comp.get("id") in component_ids or not component_ids  # If no scope, include all
        ]
        
        # Filter zones to include only relevant components
        zones = blueprint_data.get("zones", {})
        filtered_zones = {}
        for zone_name, zone_components in zones.items():
            filtered_zone_components = [
                comp for comp in zone_components
                if comp.get("id") in component_ids or not component_ids
            ]
            if filtered_zone_components:
                filtered_zones[zone_name] = filtered_zone_components
        
        # Filter contracts related to scoped components
        contracts = blueprint_data.get("contracts", [])
        filtered_contracts = [
            contract for contract in contracts
            if any(
                comp_id in contract.get("components", []) or comp_id in contract.get("providers", []) or comp_id in contract.get("consumers", [])
                for comp_id in component_ids
            ) or not component_ids
        ]
        
        return {
            "version": blueprint_data.get("version", "1.0"),
            "zones": filtered_zones,
            "components": filtered_components,
            "contracts": filtered_contracts
        }
    
    def _load_tier_3_scoped(self, task_context: Dict[str, Any]) -> Dict[str, Any]:
        """Load Tier 3: Surgical Code (only files in task scope)."""
        allowed_files = task_context.get("files", [])
        file_contents = {}
        
        for file_path in allowed_files:
            path = Path(file_path)
            if path.exists() and path.is_file():
                try:
                    # Only read text files (code files)
                    if path.suffix in [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp", ".c", ".h", ".hpp", ".md", ".json", ".yaml", ".yml", ".toml"]:
                        with open(path, "r", encoding="utf-8") as f:
                            file_contents[str(path)] = {
                                "path": str(path),
                                "content": f.read(),
                                "type": "file"
                            }
                except Exception as e:
                    file_contents[str(path)] = {
                        "path": str(path),
                        "content": f"Error reading file: {e}",
                        "type": "file",
                        "error": True
                    }
        
        return {
            "files": file_contents,
            "file_count": len(file_contents),
            "allowed_modifications": task_context.get("allowed_modifications", [])
        }
    
    def get_context_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get a summary of context for logging/debugging."""
        summary = {
            "tier": context.get("tier"),
            "version": context.get("version")
        }
        
        if context.get("tier") == "orchestrator":
            tier_1 = context.get("tier_1", {})
            intent = tier_1.get("intent", {})
            summary["features_count"] = len(intent.get("features", []))
            summary["sprint"] = intent.get("sprint", "")
        elif context.get("tier") == "worker":
            task_scope = context.get("task_scope", {})
            summary["task_id"] = context.get("task_id")
            summary["agent_type"] = context.get("agent_type")
            summary["component_count"] = len(task_scope.get("components", []))
            summary["file_count"] = len(task_scope.get("allowed_files", []))
            tier_3 = context.get("tier_3", {})
            summary["loaded_files_count"] = tier_3.get("file_count", 0)
        
        return summary