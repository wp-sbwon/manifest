"""
Agent Channels View Widget.

Displays agent communication channels with channel selection and log output.
"""
from typing import Dict, Any, Optional, List
from textual.widgets import Static, RichLog, Button, Horizontal
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class ChannelSelected(Message):
    """Message sent when a channel is selected."""

    def __init__(self, channel_name: str):
        super().__init__()
        self.channel_name = channel_name


class AgentChannelsView(Vertical):
    """View showing agent channels with selection and log output."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_channel: str = "main"
        self.channel_buttons: Dict[str, Button] = {}

    def compose(self):
        """Compose the widget."""
        yield Static("[bold]Agent Channels[/]", id="channels-header")
        with Horizontal(id="channel-selector-buttons"):
            # Channel buttons will be added dynamically
            pass
        with VerticalScroll(id="channel-log-scroll"):
            yield RichLog(id="channel-log", markup=True, wrap=True)

    async def update_channels(self, channels: Dict[str, Dict[str, Any]]) -> None:
        """Update available channels.

        Args:
            channels: Dictionary mapping channel names to channel info.
        """
        try:
            selector = self.query_one("#channel-selector-buttons", Horizontal)

            # Remove old buttons
            for button in list(self.channel_buttons.values()):
                try:
                    await selector.remove(button)
                except Exception:
                    pass
            self.channel_buttons.clear()

            # Add main channel button
            main_button = Button("Main", id="btn-channel-main-view", variant="default")
            await selector.mount(main_button)
            self.channel_buttons["main"] = main_button
            main_button.on_click = lambda: self._switch_channel("main")

            # Add squad channel buttons
            for channel_name, channel_info in channels.items():
                if channel_name == "main":
                    continue

                task_id = channel_info.get("task_id", "unknown")
                agent_type = channel_info.get("agent_type", "agent")
                message_count = channel_info.get("message_count", 0)

                label = f"{agent_type.title()}({task_id[:8]})"
                if message_count > 0:
                    label += f" [{message_count}]"

                button_id = f"btn-channel-view-{channel_name}"
                button = Button(label, id=button_id, variant="default")
                await selector.mount(button)
                self.channel_buttons[channel_name] = button

                # Create closure for channel name
                def make_handler(ch_name):
                    def handler():
                        self._switch_channel(ch_name)
                    return handler
                button.on_click = make_handler(channel_name)

            # Highlight current channel
            self._highlight_current_channel()

        except Exception as e:
            logger.error(f"Error updating channels: {e}", exc_info=True)

    def _switch_channel(self, channel_name: str) -> None:
        """Switch to a different channel.

        Args:
            channel_name: Name of the channel to switch to.
        """
        self.current_channel = channel_name
        self._highlight_current_channel()
        self._load_channel_logs(channel_name)
        self.post_message(ChannelSelected(channel_name))

    def _highlight_current_channel(self) -> None:
        """Highlight the currently selected channel button."""
        for name, button in self.channel_buttons.items():
            if name == self.current_channel:
                button.variant = "primary"
            else:
                button.variant = "default"

    def _load_channel_logs(self, channel_name: str) -> None:
        """Load and display logs for a channel.

        Args:
            channel_name: Name of the channel.
        """
        log_widget = self.query_one("#channel-log", RichLog)
        log_widget.clear()

        try:
            app_ref = getattr(self, "app_ref", None)
            if not app_ref or not hasattr(app_ref, "state_manager"):
                log_widget.write("[dim]No state manager available[/]")
                return

            state_manager = app_ref.state_manager
            history = state_manager.get_chat_history(channel_name)

            if not history:
                log_widget.write(f"[dim]No messages in channel: {channel_name}[/]")
                return

            log_widget.write(f"[bold cyan]Channel: {channel_name}[/]")
            log_widget.write(f"[dim]{len(history)} messages[/]\n")

            for msg in history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")

                if role == "user":
                    log_widget.write(f"[bold]User[/] {timestamp}: {content}")
                elif role == "assistant":
                    log_widget.write(f"[cyan]Agent[/] {timestamp}: {content}")
                elif role == "system":
                    log_widget.write(f"[yellow]System[/] {timestamp}: {content}")
                else:
                    log_widget.write(f"[dim]{role}[/] {timestamp}: {content}")

        except Exception as e:
            logger.error(f"Error loading channel logs: {e}", exc_info=True)
            log_widget.write(f"[red]Error loading logs: {e}[/]")

    def add_message(self, channel_name: str, role: str, content: str) -> None:
        """Add a message to the channel log if it's the active channel.

        Args:
            channel_name: Name of the channel.
            role: Message role (user, assistant, system).
            content: Message content.
        """
        if channel_name != self.current_channel:
            return

        try:
            log_widget = self.query_one("#channel-log", RichLog)
            if role == "user":
                log_widget.write(f"[bold]User[/]: {content}")
            elif role == "assistant":
                log_widget.write(f"[cyan]Agent[/]: {content}")
            elif role == "system":
                log_widget.write(f"[yellow]System[/]: {content}")
            else:
                log_widget.write(f"[dim]{role}[/]: {content}")
        except Exception as e:
            logger.error(f"Error adding message to channel log: {e}", exc_info=True)

    def set_app(self, app: Any) -> None:
        """Set reference to app for accessing state manager.

        Args:
            app: ManifestApp instance.
        """
        self.app_ref = app
        # Load initial channel
        self._load_channel_logs(self.current_channel)
