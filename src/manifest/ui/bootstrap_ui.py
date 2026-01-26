"""
Bootstrap Mode TUI for API key configuration.
"""
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Input, Button, Label, Static
from textual import on
from manifest.core.config import get_config_manager
import asyncio


class BootstrapApp(App):
    """Bootstrap mode TUI for configuring API keys."""

    CSS = """
    Screen { background: #0d1117; color: #c9d1d9; }
    .bootstrap-container {
        width: 80;
        height: auto;
        margin: 2;
        padding: 2;
        border: solid #2ea043;
        background: #161b22;
    }
    .key-input {
        margin: 1;
        width: 100%;
    }
    .status-label {
        margin: 1;
        text-align: center;
    }
    .error { color: #f85149; }
    .success { color: #3fb950; }
    .info { color: #79c0ff; }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        self.config = get_config_manager()
        self.keys = self.config.get_api_keys()
        self.validation_results = {}

    def compose(self) -> ComposeResult:
        """Compose the bootstrap UI layout.

        Creates the initial UI structure with API key input fields for
        Anthropic, OpenAI, and Google providers, along with validation
        and save buttons.

        Returns:
            ComposeResult containing all UI widgets to be mounted.
        """
        yield Header()
        with Container(classes="bootstrap-container"):
            yield Label("🔐 Manifest API Key Configuration", classes="status-header")
            yield Label("Please configure your API keys to continue.", classes="info status-label")

            yield Label("Anthropic API Key:", classes="status-label")
            yield Input(
                value=self.keys.get("anthropic", "") or "",
                placeholder="sk-ant-...",
                id="anthropic-key",
                password=True,
                classes="key-input"
            )
            yield Label("", id="anthropic-status", classes="status-label")

            yield Label("OpenAI API Key:", classes="status-label")
            yield Input(
                value=self.keys.get("openai", "") or "",
                placeholder="sk-...",
                id="openai-key",
                password=True,
                classes="key-input"
            )
            yield Label("", id="openai-status", classes="status-label")

            yield Label("Google API Key:", classes="status-label")
            yield Input(
                value=self.keys.get("google", "") or "",
                placeholder="Enter Google API key",
                id="google-key",
                password=True,
                classes="key-input"
            )
            yield Label("", id="google-status", classes="status-label")

            with Horizontal():
                yield Button("Validate & Save", id="save-btn", variant="success")
                yield Button("Skip (Demo Mode)", id="skip-btn", variant="default")

        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount event.

        Sets focus to the Anthropic API key input field when the app
        is mounted, providing a better user experience by starting
        at the first input.
        """
        self.query_one("#anthropic-key").focus()

    @on(Button.Pressed, "#save-btn")
    async def on_save(self) -> None:
        """Validate and save API keys."""
        anthropic_key = self.query_one("#anthropic-key", Input).value.strip()
        openai_key = self.query_one("#openai-key", Input).value.strip()
        google_key = self.query_one("#google-key", Input).value.strip()

        # Update status labels
        self.query_one("#anthropic-status").update("Validating...")
        self.query_one("#openai-status").update("Validating...")
        self.query_one("#google-status").update("Validating...")

        # Validate keys
        anthropic_valid = await self.config.validate_key("anthropic", anthropic_key) if anthropic_key else False
        openai_valid = await self.config.validate_key("openai", openai_key) if openai_key else False
        google_valid = await self.config.validate_key("google", google_key) if google_key else False

        # Update status
        self.query_one("#anthropic-status").update(
            "✅ Valid" if anthropic_valid else ("❌ Invalid" if anthropic_key else "⏭️  Skipped"),
            classes="success" if anthropic_valid else ("error" if anthropic_key else "info")
        )
        self.query_one("#openai-status").update(
            "✅ Valid" if openai_valid else ("❌ Invalid" if openai_key else "⏭️  Skipped"),
            classes="success" if openai_valid else ("error" if openai_key else "info")
        )
        self.query_one("#google-status").update(
            "✅ Valid" if google_valid else ("❌ Invalid" if google_key else "⏭️  Skipped"),
            classes="success" if google_valid else ("error" if google_key else "info")
        )

        # Save keys
        keys = {
            "anthropic": anthropic_key if anthropic_key else self.keys.get("anthropic", ""),
            "openai": openai_key if openai_key else self.keys.get("openai", ""),
            "google": google_key if google_key else self.keys.get("google", "")
        }

        if self.config.save_api_keys(keys):
            self.query_one("#save-btn").label = "✅ Saved!"
            await asyncio.sleep(1)
            self.exit(True)
        else:
            self.query_one("#save-btn").label = "❌ Save Failed"

    @on(Button.Pressed, "#skip-btn")
    def on_skip(self) -> None:
        """Skip configuration (demo mode)."""
        self.exit(False)


def run_bootstrap() -> bool:
    """Run bootstrap mode and return True if keys were configured."""
    app = BootstrapApp()
    return app.run()
