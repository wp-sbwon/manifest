"""
Skills management for agents following OpenCode conventions.

This module provides the SkillsManager class which manages agent skills from
multiple sources:
1. Agent default skills from agent_config.json
2. Project-scoped skills from AGENTS.md
3. Skill definitions from .claude/rules/*.md files

Skills provide agents with capabilities, tools, and knowledge that guide their
behavior. The manager filters and formats skills based on agent type and task scope.
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class SkillsManager:
    """Manages agent skills from multiple sources.
    
    Loads skills from agent_config.json (agent defaults), AGENTS.md
    (project-scoped), and .claude/rules/ (skill definitions). Filters
    and formats skills based on agent type and task scope.
    
    Attributes:
        manifest_dir: Path to .manifest directory.
        project_root: Root directory of the project.
        agent_config_file: Path to agent_config.json.
        agents_md_file: Path to AGENTS.md.
        claude_rules_dir: Path to .claude/rules/ directory.
        _agent_skills: Dictionary mapping agent types to skill ID lists.
        _project_skills: List of project-scoped skill dictionaries.
        _skill_definitions: Dictionary mapping skill IDs to skill definitions.
    """
    
    def __init__(self, manifest_dir: Path = None, project_root: Path = None):
        """Initialize the skills manager.
        
        Sets up paths to skill sources and loads all available skills.
        Skills are loaded from agent_config.json, AGENTS.md, and .claude/rules/.
        
        Args:
            manifest_dir: Path to .manifest directory. Defaults to .manifest.
            project_root: Root directory of the project. Defaults to current directory.
        """
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.project_root = project_root or Path.cwd()
        self.agent_config_file = self.manifest_dir / "agent_config.json"
        self.agents_md_file = self.project_root / "AGENTS.md"
        self.claude_rules_dir = self.project_root / ".claude" / "rules"
        
        self._agent_skills = {}  # agent_type -> list of skill IDs
        self._project_skills = []  # List of project-scoped skills
        self._skill_definitions = {}  # skill_id -> skill definition
        
        self._load_skills()
    
    def _load_skills(self) -> None:
        """Load skills from all available sources.
        
        Loads skills in order: agent defaults, project skills, and skill
        definitions. This is called during initialization.
        """
        # Load agent default skills from agent_config.json
        self._load_agent_default_skills()
        
        # Load project-scoped skills from AGENTS.md
        self._load_project_skills()
        
        # Load skill definitions from .claude/rules/
        self._load_skill_definitions()
    
    def _load_agent_default_skills(self) -> None:
        """Load agent default skills from agent_config.json.
        
        Reads the agent_skills section from agent_config.json which maps
        agent types to lists of skill IDs. These are the default skills
        each agent type has.
        """
        if not self.agent_config_file.exists():
            return
        
        try:
            with open(self.agent_config_file, "r") as f:
                config = json.load(f)
            
            # Load agent_skills section (new)
            agent_skills = config.get("agent_skills", {})
            self._agent_skills = agent_skills.copy()
            
        except Exception as e:
            logger.warning(f"Failed to load agent skills: {e}", exc_info=True)
            self._agent_skills = {}
    
    def _load_project_skills(self):
        """Load project-scoped skills from AGENTS.md (OpenCode convention)."""
        if not self.agents_md_file.exists():
            return
        
        try:
            with open(self.agents_md_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Parse AGENTS.md for skills
            # Look for skills section or skill references
            skills = self._parse_agents_md(content)
            self._project_skills = skills
            
        except Exception as e:
            logger.warning(f"Failed to load AGENTS.md: {e}", exc_info=True)
            self._project_skills = []
    
    def _parse_agents_md(self, content: str) -> List[Dict[str, Any]]:
        """Parse AGENTS.md content to extract skill definitions.
        
        Follows OpenCode conventions for skill definitions in AGENTS.md.
        Looks for skills sections and skill definitions, as well as references
        to .claude/rules/*.md files.
        
        Args:
            content: Full text content of AGENTS.md.
        
        Returns:
            List of skill dictionaries extracted from AGENTS.md.
        """
        skills = []
        
        # Look for skills section
        skills_section_match = re.search(
            r'##\s+Skills?\s*\n(.*?)(?=\n##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        
        if skills_section_match:
            skills_content = skills_section_match.group(1)
            
            # Parse individual skill definitions
            skill_pattern = r'###\s+Skill:\s*(\w+)\s*\n(.*?)(?=\n###|\Z)'
            for match in re.finditer(skill_pattern, skills_content, re.DOTALL):
                skill_id = match.group(1)
                skill_desc = match.group(2).strip()
                
                skills.append({
                    "id": skill_id,
                    "name": skill_id,
                    "description": skill_desc,
                    "source": "AGENTS.md",
                    "type": "project"
                })
        
        # Also look for references to .claude/rules/*.md files
        rule_ref_pattern = r'\.claude/rules/([\w\-]+)\.md'
        for match in re.finditer(rule_ref_pattern, content):
            rule_name = match.group(1)
            rule_file = self.claude_rules_dir / f"{rule_name}.md"
            
            if rule_file.exists():
                skills.append({
                    "id": rule_name,
                    "name": rule_name,
                    "file": str(rule_file.relative_to(self.project_root)),
                    "source": "AGENTS.md",
                    "type": "project"
                })
        
        return skills
    
    def _load_skill_definitions(self) -> None:
        """Load skill definitions from .claude/rules/ directory.
        
        Scans the .claude/rules/ directory for .md files and parses them
        as skill definitions. Each file becomes a skill with metadata
        extracted from the markdown content.
        """
        if not self.claude_rules_dir.exists():
            return
        
        # Load all .md files in .claude/rules/ as potential skills
        for rule_file in self.claude_rules_dir.glob("*.md"):
            # Skip manifest-policy.md (it's Tier 0, not a skill)
            if rule_file.name == "manifest-policy.md":
                continue
            
            skill_id = rule_file.stem
            try:
                with open(rule_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Extract skill metadata from markdown
                skill_def = self._parse_skill_markdown(content, skill_id, rule_file)
                self._skill_definitions[skill_id] = skill_def
                
            except Exception as e:
                logger.warning(f"Failed to load skill {skill_id}: {e}", exc_info=True)
    
    def _parse_skill_markdown(self, content: str, skill_id: str, file_path: Path) -> Dict[str, Any]:
        """Parse a markdown file to extract skill definition metadata.
        
        Extracts title, description, trigger keywords, and applicable agents
        from the markdown content. These are used to match skills to agents
        and tasks.
        
        Args:
            content: Full markdown content of the skill file.
            skill_id: ID of the skill (derived from filename).
            file_path: Path to the skill markdown file.
        
        Returns:
            Dictionary containing skill definition with id, name, description,
            file path, source, type, and optional triggers/agents.
        """
        skill_def = {
            "id": skill_id,
            "name": skill_id,
            "file": str(file_path.relative_to(self.project_root)),
            "content": content,
            "source": ".claude/rules/",
            "type": "rule"
        }
        
        # Extract title (first # heading)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            skill_def["name"] = title_match.group(1).strip()
        
        # Extract description (first paragraph after title)
        desc_match = re.search(
            r'^#\s+.+?\n\n(.+?)(?=\n\n|\n#|\Z)',
            content,
            re.DOTALL
        )
        if desc_match:
            skill_def["description"] = desc_match.group(1).strip()
        
        # Extract trigger keywords (if present)
        trigger_match = re.search(
            r'(?:##\s+)?Trigger(?:s)?(?:\s+Keywords?)?\s*\n(.*?)(?=\n##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        if trigger_match:
            triggers = [
                line.strip().lstrip('-').strip()
                for line in trigger_match.group(1).split('\n')
                if line.strip() and not line.strip().startswith('#')
            ]
            skill_def["triggers"] = triggers
        
        # Extract agent applicability (if present)
        agents_match = re.search(
            r'(?:##\s+)?Agent(?:s)?\s*\n(.*?)(?=\n##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        if agents_match:
            agents = [
                line.strip().lstrip('-').strip()
                for line in agents_match.group(1).split('\n')
                if line.strip() and not line.strip().startswith('#')
            ]
            skill_def["agents"] = agents
        
        return skill_def
    
    def get_skills_for_agent(
        self,
        agent_type: str,
        task_scope: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get applicable skills for a specific agent type.
        
        Combines project-scoped skills and agent default skills, filtering
        by agent applicability. Project skills take priority over defaults.
        
        Args:
            agent_type: Type of agent (e.g., "orchestrator", "coder", "planner").
            task_scope: Optional task scope dictionary. Currently not used but
                reserved for future directory-based skill filtering.
        
        Returns:
            List of skill definition dictionaries applicable to this agent type.
            Skills are ordered with project skills first, then agent defaults.
        """
        skills = []
        
        # First, add project-scoped skills
        for skill in self._project_skills:
            # Check if skill applies to this agent
            if self._skill_applies_to_agent(skill, agent_type):
                skill_def = self._skill_definitions.get(skill["id"], skill)
                skills.append(skill_def)
        
        # Then, add agent default skills (if not already included)
        agent_default_skill_ids = self._agent_skills.get(agent_type, [])
        for skill_id in agent_default_skill_ids:
            # Skip if already added from project skills
            if any(s.get("id") == skill_id for s in skills):
                continue
            
            # Load skill definition
            skill_def = self._skill_definitions.get(skill_id)
            if skill_def:
                skills.append(skill_def)
            else:
                # Skill ID referenced but definition not found
                skills.append({
                    "id": skill_id,
                    "name": skill_id,
                    "description": f"Skill {skill_id} (definition not found)",
                    "source": "agent_config.json",
                    "type": "agent_default"
                })
        
        return skills
    
    def _skill_applies_to_agent(self, skill: Dict[str, Any], agent_type: str) -> bool:
        """Check if a skill applies to a specific agent type."""
        # If skill has explicit agents list, check it
        if "agents" in skill:
            return agent_type in skill["agents"]
        
        # If no agents specified, skill applies to all agents
        return True
    
    def get_skill_content(self, skill_id: str) -> Optional[str]:
        """Get the content of a skill by ID."""
        skill_def = self._skill_definitions.get(skill_id)
        if skill_def:
            return skill_def.get("content", "")
        return None
    
    def format_skills_for_prompt(self, skills: List[Dict[str, Any]]) -> str:
        """Format skills list for inclusion in agent prompt."""
        if not skills:
            return ""
        
        lines = ["## AVAILABLE SKILLS", ""]
        
        for skill in skills:
            skill_id = skill.get("id", "unknown")
            skill_name = skill.get("name", skill_id)
            skill_desc = skill.get("description", "")
            triggers = skill.get("triggers", [])
            
            lines.append(f"### {skill_name} (`{skill_id}`)")
            if skill_desc:
                lines.append(f"{skill_desc}")
            if triggers:
                lines.append(f"**Triggers**: {', '.join(triggers)}")
            lines.append("")
        
        lines.append(
            "**IMPORTANT**: When a request matches a skill trigger, "
            "invoke the skill immediately before proceeding with other steps."
        )
        
        return "\n".join(lines)
    
    def save_agent_skills(self, agent_skills: Dict[str, List[str]]) -> bool:
        """
        Save agent default skills to agent_config.json.
        
        Args:
            agent_skills: Dictionary mapping agent_type -> list of skill IDs
            
        Returns:
            True if saved successfully, False otherwise
        """
        import json
        
        if not self.agent_config_file.exists():
            # Create default config
            config = {
                "version": "1.0",
                "agent_models": {},
                "agent_skills": agent_skills
            }
        else:
            try:
                with open(self.agent_config_file, "r") as f:
                    config = json.load(f)
            except Exception as e:
                logger.error(f"Error loading agent config: {e}", exc_info=True)
                return False
        
        config["agent_skills"] = agent_skills
        
        try:
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            with open(self.agent_config_file, "w") as f:
                json.dump(config, f, indent=2)
            # Reload
            self._load_agent_default_skills()
            return True
        except Exception as e:
            logger.error(f"Error saving agent skills: {e}", exc_info=True)
            return False
    
    def save_skill_file(self, skill_id: str, content: str) -> bool:
        """
        Save a skill file to .claude/rules/.
        
        Args:
            skill_id: Skill identifier (filename without .md)
            content: Markdown content for the skill
            
        Returns:
            True if saved successfully, False otherwise
        """
        skill_file = self.claude_rules_dir / f"{skill_id}.md"
        try:
            self.claude_rules_dir.mkdir(parents=True, exist_ok=True)
            with open(skill_file, "w", encoding="utf-8") as f:
                f.write(content)
            # Reload skill definitions
            self._load_skill_definitions()
            return True
        except Exception as e:
            logger.error(f"Error saving skill file: {e}", exc_info=True)
            return False
    
    def save_agents_md(self, content: str) -> bool:
        """
        Save AGENTS.md content.
        
        Args:
            content: Markdown content for AGENTS.md
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(self.agents_md_file, "w", encoding="utf-8") as f:
                f.write(content)
            # Reload project skills
            self._load_project_skills()
            return True
        except Exception as e:
            logger.error(f"Error saving AGENTS.md: {e}", exc_info=True)
            return False
