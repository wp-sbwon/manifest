"""
Settings Screen - Interactive settings management UI.
Opens as a separate screen (not a tab) when /config command is used.
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Header, Footer, TabbedContent, TabPane, Input, Button, Static, Label, RichLog, Select, TextArea
from textual import on
from textual.binding import Binding
from pathlib import Path
from typing import Dict, Any, Optional
from manifest.core.settings_manager import SettingsManager


class SettingsScreen(Screen):
    """Settings management screen."""
    
    BINDINGS = [
        Binding("escape", "close", "Close", priority=True),
        Binding("ctrl+s", "save", "Save", priority=True),
    ]
    
    CSS = """
    Screen {
        background: #0d1117;
    }
    
    #settings-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    #settings-header {
        height: 3;
        border-bottom: solid #30363d;
        margin-bottom: 1;
    }
    
    #settings-tabs {
        height: 1fr;
    }
    
    #settings-footer {
        height: 3;
        border-top: solid #30363d;
        margin-top: 1;
    }
    
    .settings-section {
        padding: 1;
        margin-bottom: 1;
    }
    
    .settings-label {
        color: #8b949e;
        margin-bottom: 1;
    }
    
    .settings-input {
        width: 100%;
        margin-bottom: 1;
    }
    
    .settings-button {
        margin: 0 1;
    }
    
    .status-success {
        color: #3fb950;
    }
    
    .status-error {
        color: #f85149;
    }
    
    .status-warning {
        color: #d29922;
    }
    
    .masked-key {
        color: #8b949e;
    }
    """
    
    def __init__(self, manifest_dir: Path = None, project_root: Path = None, initial_tab: str = "api_keys"):
        super().__init__()
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.project_root = project_root or Path.cwd()
        self.settings_manager = SettingsManager(self.manifest_dir, self.project_root)
        self.initial_tab = initial_tab
        self.unsaved_changes = False
        
        # Store current values for comparison
        self._api_keys = {}
        self._agent_models = {}
        self._agent_skills = {}
        self._policy_content = ""
        self._agents_md_content = ""
    
    def compose(self) -> ComposeResult:
        """Compose the settings screen."""
        yield Header(show_clock=False)
        
        with Container(id="settings-container"):
            with Vertical(id="settings-header"):
                yield Label("Settings", id="settings-title")
                yield Static("Press Esc to close, Ctrl+S to save", id="settings-hint")
            
            with TabbedContent(id="settings-tabs"):
                # Tab 1: API Keys
                with TabPane("API Keys", id="tab-api-keys"):
                    yield from self._compose_api_keys_tab()
                
                # Tab 2: Agent Models
                with TabPane("Agent Models", id="tab-models"):
                    yield from self._compose_models_tab()
                
                # Tab 3: Agent Skills
                with TabPane("Skills", id="tab-skills"):
                    yield from self._compose_skills_tab()
                
                # Tab 4: Agent Permissions
                with TabPane("Permissions", id="tab-permissions"):
                    yield from self._compose_permissions_tab()
                
                # Tab 5: Policy
                with TabPane("Policy", id="tab-policy"):
                    yield from self._compose_policy_tab()
            
            with Horizontal(id="settings-footer"):
                yield Button("Save", id="btn-save", variant="primary")
                yield Button("Cancel", id="btn-cancel")
                yield Button("Reload", id="btn-reload")
                yield Static("", id="status-message")
        
        yield Footer()
    
    def _compose_api_keys_tab(self) -> ComposeResult:
        """Compose API Keys tab."""
        with VerticalScroll():
            with Vertical(classes="settings-section"):
                yield Label("Anthropic API Key", classes="settings-label")
                yield Input(
                    placeholder="sk-ant-...",
                    id="input-anthropic-key",
                    password=True,
                    classes="settings-input"
                )
                yield Static("", id="status-anthropic")
                yield Button("Test", id="btn-test-anthropic", classes="settings-button")
            
            with Vertical(classes="settings-section"):
                yield Label("OpenAI API Key", classes="settings-label")
                yield Input(
                    placeholder="sk-...",
                    id="input-openai-key",
                    password=True,
                    classes="settings-input"
                )
                yield Static("", id="status-openai")
                yield Button("Test", id="btn-test-openai", classes="settings-button")
            
            with Vertical(classes="settings-section"):
                yield Label("Google API Key", classes="settings-label")
                yield Input(
                    placeholder="...",
                    id="input-google-key",
                    password=True,
                    classes="settings-input"
                )
                yield Static("", id="status-google")
                yield Button("Test", id="btn-test-google", classes="settings-button")
    
    def _compose_models_tab(self) -> ComposeResult:
        """Compose Agent Models tab."""
        with VerticalScroll():
            agent_types = ["orchestrator", "planner", "coder", "test", "review"]
            providers = ["anthropic", "openai", "google"]
            
            for agent_type in agent_types:
                with Vertical(classes="settings-section"):
                    yield Label(f"{agent_type.title()} Agent", classes="settings-label")
                    
                    with Horizontal():
                        yield Select(
                            [(p, p) for p in providers],
                            prompt="Provider",
                            id=f"select-{agent_type}-provider",
                            classes="settings-input"
                        )
                        yield Select(
                            [],  # Will be populated based on provider
                            prompt="Model",
                            id=f"select-{agent_type}-model",
                            classes="settings-input"
                        )
    
    def _compose_skills_tab(self) -> ComposeResult:
        """Compose Skills tab."""
        with VerticalScroll():
            with Vertical(classes="settings-section"):
                yield Label("Agent Default Skills", classes="settings-label")
                yield RichLog(id="agent-skills-log", markup=True)
                yield Static("Use agent_config.json to configure default skills", id="skills-hint")
            
            with Vertical(classes="settings-section"):
                yield Label("Project Skills (AGENTS.md)", classes="settings-label")
                yield TextArea(
                    id="textarea-agents-md",
                    language="markdown",
                    classes="settings-input"
                )
                yield Static("Edit AGENTS.md to configure project-scoped skills", id="agents-md-hint")
    
    def _compose_policy_tab(self) -> ComposeResult:
        """Compose Policy tab."""
        with VerticalScroll():
            with Vertical(classes="settings-section"):
                yield Label("Manifest Policy (.claude/rules/manifest-policy.md)", classes="settings-label")
                yield TextArea(
                    id="textarea-policy",
                    language="markdown",
                    classes="settings-input"
                )
                yield Static("This is Tier 0 policy - injected into every agent context", id="policy-hint")
    
    async def on_mount(self) -> None:
        """Load settings when screen mounts."""
        await self.load_settings()
        
        # Set initial tab
        tabs = self.query_one("#settings-tabs", TabbedContent)
        if self.initial_tab == "api_keys":
            tabs.active = "tab-api-keys"
        elif self.initial_tab == "models":
            tabs.active = "tab-models"
        elif self.initial_tab == "skills":
            tabs.active = "tab-skills"
        elif self.initial_tab == "permissions":
            tabs.active = "tab-permissions"
        elif self.initial_tab == "policy":
            tabs.active = "tab-policy"
    
    async def load_settings(self):
        """Load all settings into UI."""
        # Load API keys
        api_keys = self.settings_manager.get_api_keys()
        for provider in ["anthropic", "openai", "google"]:
            key_input = self.query_one(f"#input-{provider}-key", Input)
            key = api_keys.get(provider)
            if key:
                # Show masked version
                key_input.value = key
            self._api_keys[provider] = key
        
        # Load agent models
        models = self.settings_manager.get_all_agent_models()
        for agent_type, config in models.items():
            provider_select = self.query_one(f"#select-{agent_type}-provider", Select)
            model_select = self.query_one(f"#select-{agent_type}-model", Select)
            
            provider = config.get("provider", "anthropic")
            model = config.get("model", "")
            
            # Set provider
            provider_select.value = provider
            
            # Update models based on provider
            await self._update_model_options(agent_type, provider)
            
            # Set model
            if model:
                model_select.value = model
            
            self._agent_models[agent_type] = {"provider": provider, "model": model}
        
        # Load policy
        policy_content = self.settings_manager.get_policy_content()
        try:
            policy_textarea = self.query_one("#textarea-policy", TextArea)
            # TextArea uses load_text() method
            policy_textarea.load_text(policy_content)
            self._policy_content = policy_content
        except Exception:
            # TextArea might not be visible yet
            self._policy_content = policy_content
        
        # Load AGENTS.md
        agents_md_content = self.settings_manager.get_agents_md_content()
        try:
            agents_md_textarea = self.query_one("#textarea-agents-md", TextArea)
            agents_md_textarea.load_text(agents_md_content)
            self._agents_md_content = agents_md_content
        except Exception:
            # TextArea might not be visible yet
            self._agents_md_content = agents_md_content
        
        # Load agent skills
        agent_skills = self.settings_manager.get_agent_skills()
        self._agent_skills = agent_skills.copy()
        skills_log = self.query_one("#agent-skills-log", RichLog)
        skills_log.clear()
        for agent_type, skill_ids in agent_skills.items():
            if skill_ids:
                skills_log.write(f"[bold]{agent_type}:[/] {', '.join(skill_ids)}")
            else:
                skills_log.write(f"[dim]{agent_type}:[/] (no skills)")
    
    async def _update_model_options(self, agent_type: str, provider: str):
        """Update model options based on provider."""
        model_select = self.query_one(f"#select-{agent_type}-model", Select)
        
        # Model options per provider
        models = {
            "anthropic": [
                ("claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20241022"),
                ("claude-3-opus-20240229", "claude-3-opus-20240229"),
                ("claude-3-sonnet-20240229", "claude-3-sonnet-20240229"),
                ("claude-3-haiku-20240307", "claude-3-haiku-20240307"),
            ],
            "openai": [
                ("gpt-4-turbo-preview", "gpt-4-turbo-preview"),
                ("gpt-4", "gpt-4"),
                ("gpt-3.5-turbo", "gpt-3.5-turbo"),
            ],
            "google": [
                ("gemini-pro", "gemini-pro"),
                ("gemini-pro-vision", "gemini-pro-vision"),
            ]
        }
        
        model_options = models.get(provider, [])
        model_select.set_options(model_options)
    
    @on(Select.Changed)
    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle provider selection change."""
        # Check if this is a provider select
        select_id = event.select.id
        if "-provider" in select_id:
            # Extract agent_type from select ID
            agent_type = select_id.replace("select-", "").replace("-provider", "")
            
            provider = event.value
            if provider:
                await self._update_model_options(agent_type, provider)
    
    @on(Button.Pressed, "#btn-test-anthropic")
    async def test_anthropic_key(self) -> None:
        """Test Anthropic API key."""
        key_input = self.query_one("#input-anthropic-key", Input)
        status = self.query_one("#status-anthropic", Static)
        
        key = key_input.value.strip()
        if not key:
            status.update("❌ No key provided", classes="status-error")
            return
        
        status.update("Testing...", classes="status-warning")
        is_valid = await self.settings_manager.validate_key("anthropic", key)
        if is_valid:
            status.update("✅ Valid", classes="status-success")
        else:
            status.update("❌ Invalid", classes="status-error")
    
    @on(Button.Pressed, "#btn-test-openai")
    async def test_openai_key(self) -> None:
        """Test OpenAI API key."""
        key_input = self.query_one("#input-openai-key", Input)
        status = self.query_one("#status-openai", Static)
        
        key = key_input.value.strip()
        if not key:
            status.update("❌ No key provided", classes="status-error")
            return
        
        status.update("Testing...", classes="status-warning")
        is_valid = await self.settings_manager.validate_key("openai", key)
        if is_valid:
            status.update("✅ Valid", classes="status-success")
        else:
            status.update("❌ Invalid", classes="status-error")
    
    @on(Button.Pressed, "#btn-test-google")
    async def test_google_key(self) -> None:
        """Test Google API key."""
        key_input = self.query_one("#input-google-key", Input)
        status = self.query_one("#status-google", Static)
        
        key = key_input.value.strip()
        if not key:
            status.update("❌ No key provided", classes="status-error")
            return
        
        status.update("Testing...", classes="status-warning")
        is_valid = await self.settings_manager.validate_key("google", key)
        if is_valid:
            status.update("✅ Valid", classes="status-success")
        else:
            status.update("❌ Invalid", classes="status-error")
    
    @on(Button.Pressed, "#btn-save")
    async def on_save(self) -> None:
        """Save all settings."""
        status_msg = self.query_one("#status-message", Static)
        status_msg.update("Saving...", classes="status-warning")
        
        try:
            # Save API keys
            api_keys = {}
            for provider in ["anthropic", "openai", "google"]:
                key_input = self.query_one(f"#input-{provider}-key", Input)
                key = key_input.value.strip()
                if key:
                    api_keys[provider] = key
                else:
                    # Keep existing key if not changed
                    existing = self._api_keys.get(provider)
                    if existing:
                        api_keys[provider] = existing
            
            if api_keys:
                self.settings_manager.save_api_keys(api_keys)
            
            # Save agent models
            agent_types = ["orchestrator", "planner", "coder", "test", "review"]
            for agent_type in agent_types:
                provider_select = self.query_one(f"#select-{agent_type}-provider", Select)
                model_select = self.query_one(f"#select-{agent_type}-model", Select)
                
                provider = provider_select.value if provider_select.value else "anthropic"
                model = model_select.value if model_select.value else ""
                
                if provider and model:
                    self.settings_manager.set_agent_model(agent_type, provider, model)
            
            # Save policy
            policy_textarea = self.query_one("#textarea-policy", TextArea)
            policy_content = policy_textarea.text
            if policy_content != self._policy_content:
                self.settings_manager.save_policy_content(policy_content)
            
            # Save AGENTS.md
            agents_md_textarea = self.query_one("#textarea-agents-md", TextArea)
            agents_md_content = agents_md_textarea.text
            if agents_md_content != self._agents_md_content:
                self.settings_manager.save_agents_md_content(agents_md_content)
            
            # Save agent permissions
            try:
                agent_types = ["orchestrator", "planner", "coder", "test", "review", "debug", "approver", "project_review", "e2e_test", "integration_test"]
                permission_types = ["read", "write", "edit", "bash", "websearch", "webfetch"]
                
                for agent_type in agent_types:
                    for perm_type in permission_types:
                        try:
                            select = self.query_one(f"#select-{agent_type}-{perm_type}", Select)
                            value = select.value if select.value else "deny"
                            self.settings_manager.set_agent_permission(agent_type, perm_type, value)
                        except Exception:
                            # Select might not exist if tab wasn't visited
                            pass
            except Exception as e:
                # Permissions tab might not be visible
                pass
            
            status_msg.update("✅ Settings saved", classes="status-success")
            self.unsaved_changes = False
            
            # Reload settings to reflect changes
            await self.load_settings()
            
        except Exception as e:
            status_msg.update(f"❌ Error saving: {e}", classes="status-error")
    
    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        """Close settings screen."""
        self.action_close()
    
    @on(Button.Pressed, "#btn-reload")
    async def on_reload(self) -> None:
        """Reload settings from disk."""
        status_msg = self.query_one("#status-message", Static)
        status_msg.update("Reloading...", classes="status-warning")
        await self.load_settings()
        status_msg.update("✅ Settings reloaded", classes="status-success")
    
    def action_close(self) -> None:
        """Close the settings screen."""
        self.app.pop_screen()
    
    def action_save(self) -> None:
        """Save settings (keyboard shortcut)."""
        # Trigger save button press
        save_btn = self.query_one("#btn-save", Button)
        save_btn.press()
