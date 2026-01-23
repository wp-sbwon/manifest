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
from manifest.core.state_manager import StateManager


class ContextProvider:
    """Provides tiered context to agents."""
    
    def __init__(self, manifest_dir: Path = None, task_scoper: Optional[TaskScoper] = None, project_root: Path = None, state_manager: Optional[StateManager] = None):
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.project_root = project_root or Path.cwd()
        self.task_scoper = task_scoper or TaskScoper(manifest_dir)
        self.skills_manager = SkillsManager(manifest_dir, self.project_root)
        self.state_manager = state_manager or StateManager(manifest_dir)
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
        
        # Load architecture.json with metadata
        from manifest.audit.architecture_metadata import load_architecture_with_metadata
        tier_1["architecture"] = load_architecture_with_metadata(self.architecture_file)
        
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
    
    def get_stage_specific_context(
        self,
        task_id: str,
        agent_type: str,
        stage: str,
        previous_stages: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get stage-specific context for worker agents.
        
        Args:
            task_id: Task ID
            agent_type: Agent type
            stage: Current stage (planner, tdd_test, coder, test, debug, self_review, approver)
            previous_stages: Results from previous stages
            
        Returns:
            Dict with stage-specific context
        """
        previous_stages = previous_stages or {}
        task_context = self.task_scoper.get_task_context(task_id)
        task_scope = {
            "components": task_context.get("components", []),
            "allowed_files": task_context.get("files", []),
            "allowed_modifications": task_context.get("allowed_modifications", []),
            "requirements": task_context.get("requirements", [])
        }
        
        base_context = {
            "tier": "worker",
            "task_id": task_id,
            "agent_type": agent_type,
            "stage": stage,
            "tier_0": self._load_tier_0(),
            "task_scope": task_scope,
            "skills": self.get_skills_context(agent_type, task_scope),
            "version": "1.0"
        }
        
        # Stage-specific context
        if stage == "planner":
            # Planner: Tier 0, Tier 1, Task Scope
            base_context["tier_1"] = self._load_tier_1()
        
        elif stage == "tdd_test":
            # TDD Test: Tier 0, Planner plan, Task Scope
            planner_output = previous_stages.get("planner", {})
            base_context["planner_plan"] = planner_output.get("output", planner_output.get("plan", ""))
            base_context["task_description"] = self._get_task_description(task_id)
            base_context["previous_stages"] = previous_stages
        
        elif stage == "coder":
            # Coder: Tier 0, Tier 2, Tier 3, Planner plan, Test skeleton
            base_context["tier_2"] = self._load_tier_2_scoped(task_context)
            base_context["tier_3"] = self._load_tier_3_scoped(task_context)
            
            planner_output = previous_stages.get("planner", {})
            base_context["planner_plan"] = planner_output.get("output", planner_output.get("plan", ""))
            
            tdd_test_output = previous_stages.get("tdd_test", {})
            base_context["test_plan"] = tdd_test_output.get("test_plan", "")
            base_context["test_skeleton"] = tdd_test_output.get("test_skeleton", "")
            base_context["tdd_test"] = tdd_test_output
        
        elif stage == "test":
            # Test: Tier 0, Coder output, Test skeleton
            coder_output = previous_stages.get("coder", {})
            base_context["coder_output"] = coder_output.get("output", "")
            base_context["files_modified"] = coder_output.get("files_modified", [])
            
            tdd_test_output = previous_stages.get("tdd_test", {})
            base_context["test_plan"] = tdd_test_output.get("test_plan", "")
            base_context["test_skeleton"] = tdd_test_output.get("test_skeleton", "")
        
        elif stage == "debug":
            # Debug: Tier 0, Test results, Coder output, Error messages
            test_output = previous_stages.get("test", {})
            base_context["test_results"] = test_output.get("test_results", {})
            base_context["test_errors"] = test_output.get("errors", [])
            
            coder_output = previous_stages.get("coder", {})
            base_context["coder_output"] = coder_output.get("output", "")
            base_context["files_modified"] = coder_output.get("files_modified", [])
        
        elif stage == "self_review":
            # Self Review: Tier 0, Planner plan, Coder output, Test results
            planner_output = previous_stages.get("planner", {})
            base_context["planner_plan"] = planner_output.get("output", planner_output.get("plan", ""))
            
            coder_output = previous_stages.get("coder", {})
            base_context["coder_output"] = coder_output.get("output", "")
            base_context["files_modified"] = coder_output.get("files_modified", [])
            
            test_output = previous_stages.get("test", {})
            base_context["test_results"] = test_output.get("test_results", {})
        
        elif stage == "approver":
            # Approver: Tier 0, Planner plan, Coder output, Test results, Self Review
            planner_output = previous_stages.get("planner", {})
            base_context["planner_plan"] = planner_output.get("output", planner_output.get("plan", ""))
            
            coder_output = previous_stages.get("coder", {})
            base_context["coder_output"] = coder_output.get("output", "")
            base_context["files_modified"] = coder_output.get("files_modified", [])
            
            test_output = previous_stages.get("test", {})
            base_context["test_results"] = test_output.get("test_results", {})
            
            self_review_output = previous_stages.get("self_review", {})
            base_context["self_review"] = self_review_output
        
        return base_context
    
    def _get_task_description(self, task_id: str) -> str:
        """Get task description from state."""
        # This would need state_manager, but to avoid circular dependency,
        # we'll return a placeholder. In practice, this should be injected.
        return f"Task {task_id}"
    
    def get_sprint_context(self, sprint_id: str) -> Dict[str, Any]:
        """
        Get Sprint-level context for Integration/E2E test writing.
        
        Args:
            sprint_id: Sprint ID
            
        Returns:
            Dict with Sprint-level context including:
            - Tier 0: Policy & Principles
            - Tier 1: PRD, Architecture, Blueprint
            - Sprint tasks information
            - Sprint metadata
        """
        # Load Sprint data
        sprint_data = self.state_manager.load_sprint(sprint_id)
        
        if not sprint_data:
            # Return minimal context if Sprint doesn't exist
            return {
                "tier": "sprint",
                "sprint_id": sprint_id,
                "tier_0": self._load_tier_0(),
                "tier_1": self._load_tier_1(),
                "sprint_data": None,
                "sprint_tasks": [],
                "version": "1.0"
            }
        
        # Get Sprint tasks
        tasks = self.state_manager.get_task_checklist()
        sprint_tasks = [t for t in tasks if t.get("sprint_id") == sprint_id]
        
        # Load PRD
        prd_data = self.state_manager.load_prd()
        
        # Build Tier 1 with PRD included
        tier_1 = self._load_tier_1()
        if prd_data:
            tier_1["prd"] = prd_data
        
        # Include Blueprint in Tier 1
        blueprint = self._load_tier_2_scoped({})  # Full blueprint for Sprint context
        if blueprint:
            tier_1["blueprint"] = blueprint
        
        context = {
            "tier": "sprint",
            "sprint_id": sprint_id,
            "sprint_name": sprint_data.get("name", ""),
            "sprint_description": sprint_data.get("description", ""),
            "tier_0": self._load_tier_0(),
            "tier_1": tier_1,
            "sprint_data": sprint_data,
            "sprint_tasks": sprint_tasks,
            "task_count": len(sprint_tasks),
            "version": "1.0"
        }
        
        return context
    
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
        elif context.get("tier") == "sprint":
            summary["sprint_id"] = context.get("sprint_id")
            summary["task_count"] = context.get("task_count", 0)
        
        return summary