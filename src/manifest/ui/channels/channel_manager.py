"""
Channel management for agent output and communication.

This module handles creation and management of communication channels for
agent output. Each agent gets its own channel (tab) in the UI, allowing
users to see output from different agents separately. Channels are created
dynamically when agents start and can be switched between.

The ChannelManager was separated from ManifestApp to improve code organization
and maintainability.
"""
from typing import Dict, Any, Optional
from textual.widgets import RichLog, Button, Horizontal, TabbedContent
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class ChannelManager:
    """Manages communication channels for agent output.
    
    Creates and manages UI channels (tabs) where agent output is displayed.
    Each agent working on a task gets its own channel, allowing users to
    monitor multiple agents simultaneously. Channels can be switched via
    buttons in the channel selector.
    
    Attributes:
        app: Reference to ManifestApp for UI widget access.
        state_manager: Reference to StateManager for chat history persistence.
        squad_channels: Dictionary tracking all created channels.
        active_channel: Name of the currently active/visible channel.
    """
    
    def __init__(self, app: Any, state_manager: Any):
        """Initialize the channel manager.
        
        Args:
            app: ManifestApp instance that provides access to UI widgets.
            state_manager: StateManager instance for loading/saving chat history.
        """
        self.app = app
        self.state_manager = state_manager
        self.squad_channels: Dict[str, Dict[str, Any]] = {}  # channel_name -> channel info
        self.active_channel: str = "main"  # Currently active channel
    
    async def create_squad_channel(self, task_id: str, agent_type: str) -> Optional[str]:
        """Create a new channel for an agent's output.
        
        Creates a UI tab and button for the channel, allowing users to
        view and switch to this agent's output. The channel name follows
        the pattern "squad-{task_id}-{agent_type}".
        
        Args:
            task_id: ID of the task the agent is working on.
            agent_type: Type of agent (e.g., "coder", "planner", "test").
        
        Returns:
            Tab ID string if channel was created successfully, None if
            creation failed. Returns existing tab ID if channel already exists.
        """
        channel_name = f"squad-{task_id}-{agent_type}"
        tab_id = f"tab-{channel_name}"
        
        # Check if channel already exists
        if channel_name in self.squad_channels:
            return tab_id
        
        try:
            # Create channel button in selector
            channel_selector = self.app.query_one("#channel-selector", Horizontal)
            
            # Create button for this channel
            button_id = f"btn-channel-{channel_name}"
            # Get message count for label
            history = self.state_manager.get_chat_history(channel_name)
            message_count = len(history)
            label = f"{agent_type.title()}({task_id[:8]})"
            if message_count > 0:
                label += f" [{message_count}]"
            
            channel_button = Button(
                label,
                id=button_id,
                variant="default"
            )
            
            # Mount button
            await channel_selector.mount(channel_button)
            
            # Track channel
            self.squad_channels[channel_name] = {
                "tab_id": tab_id,
                "button_id": button_id,
                "task_id": task_id,
                "agent_type": agent_type,
                "message_count": message_count
            }
            
            # Set up button click handler
            self.app.set_timer(0.1, lambda: self._setup_channel_button(button_id, channel_name))
            
            # Load existing chat history if any
            history = self.state_manager.get_chat_history(channel_name)
            if history:
                log = self.app.query_one("#log-main", RichLog)
                log.write(f"[bold cyan]Channel {channel_name} has {len(history)} messages[/]")
            
            return tab_id
        except Exception as e:
            logger.error(f"Error creating squad channel: {e}", exc_info=True)
            return None
    
    def _setup_channel_button(self, button_id: str, channel_name: str):
        """Set up click handler for channel button.
        
        Creates a closure-based click handler that properly captures the
        channel name when the button is clicked. This ensures the correct
        channel is switched to when the button is pressed.
        
        Args:
            button_id: ID of the button widget to set up.
            channel_name: Name of the channel to switch to when clicked.
        """
        try:
            button = self.app.query_one(f"#{button_id}", Button)
            # Use a closure to properly capture channel_name
            def make_handler(ch_name):
                """Create a click handler closure for a specific channel.
                
                Args:
                    ch_name: Channel name to capture in closure.
                
                Returns:
                    Handler function that switches to the channel.
                """
                def handler():
                    """Handle button click to switch channel."""
                    self.switch_channel(ch_name)
                return handler
            button.on_click = make_handler(channel_name)
        except Exception as e:
            logger.error(f"Error setting up channel button {button_id}: {e}", exc_info=True)
    
    async def switch_channel(self, channel_name: str):
        """
        Switch to a different chat channel.
        
        Args:
            channel_name: Name of channel to switch to
        """
        # Update active channel
        self.active_channel = channel_name
        
        # Update button states
        for ch_name, ch_info in self.squad_channels.items():
            button_id = ch_info.get("button_id")
            if button_id:
                try:
                    button = self.app.query_one(f"#{button_id}", Button)
                    if ch_name == channel_name:
                        button.variant = "primary"
                    else:
                        button.variant = "default"
                except Exception:
                    pass
        
        # Update main button
        try:
            main_button = self.app.query_one("#btn-channel-main", Button)
            if channel_name == "main" or channel_name == "main-orchestrator":
                main_button.variant = "primary"
            else:
                main_button.variant = "default"
        except Exception:
            pass
        
        # Refresh log display
        await self.refresh_channel_log(channel_name)
    
    async def refresh_channel_log(self, channel_name: str):
        """
        Refresh log display for current channel.
        
        Improved version that formats output based on channel type and
        provides better visual distinction between different agent types.
        
        Args:
            channel_name: Name of channel to refresh
        """
        log = self.app.query_one("#log-main", RichLog)
        log.clear()
        
        # Load chat history for this channel
        history = self.state_manager.get_chat_history(channel_name)
        
        if not history:
            log.write(f"[dim]No messages in channel: {channel_name}[/]")
            return
        
        # Format based on channel type
        if channel_name == "main" or channel_name == "main-orchestrator":
            # Main channel - simple format
            for msg in history:
                role = msg.get("role", "assistant")
                content = msg.get("content", "")
                
                if role == "user":
                    log.write(f"[bold blue]User:[/] {content}")
                else:
                    log.write(f"[bold green]Assistant:[/] {content}")
        else:
            # Squad or shadow channel - format with channel label
            parts = channel_name.split("-")
            if len(parts) >= 3:
                task_id_short = parts[1][:8] if len(parts[1]) > 8 else parts[1]
                agent_type = parts[2] if len(parts) > 2 else "agent"
                
                channel_label = f"{agent_type.title()}[{task_id_short}]"
                if channel_name.startswith("shadow-"):
                    channel_label = f"Shadow:{agent_type.title()}[{task_id_short}]"
                
                for msg in history:
                    role = msg.get("role", "assistant")
                    content = msg.get("content", "")
                    
                    if role == "user":
                        log.write(f"[bold blue][{channel_label}] User:[/] {content}")
                    else:
                        if channel_name.startswith("shadow-"):
                            log.write(f"[bold yellow][{channel_label}] {agent_type.title()}:[/] {content}")
                        else:
                            log.write(f"[bold cyan][{channel_label}] {agent_type.title()}:[/] {content}")
            else:
                # Fallback for unknown channel format
                for msg in history:
                    role = msg.get("role", "assistant")
                    content = msg.get("content", "")
                    
                    if role == "user":
                        log.write(f"[bold blue][{channel_name}] User:[/] {content}")
                    else:
                        log.write(f"[bold green][{channel_name}] Assistant:[/] {content}")
    
    async def update_squad_channels(self, agent_coordinator: Any):
        """
        Update squad channels based on active tasks.
        
        Args:
            agent_coordinator: AgentCoordinator instance
        """
        if not agent_coordinator:
            return
        
        # Get active agents
        active_agents = agent_coordinator.get_active_agents()
        active_channels = set()
        
        # Create channels for active agents
        for task_id, agent_info in active_agents.items():
            if agent_info.get("status") == "active":
                channel_name = agent_info.get("channel")
                if channel_name:
                    agent_type = agent_info.get("agent_type", "unknown")
                    tab_id = await self.create_squad_channel(task_id, agent_type)
                    if tab_id:
                        active_channels.add(channel_name)
        
        # Also check tasks for agent assignments
        tasks = self.state_manager.get_task_checklist()
        for task in tasks:
            agent_info = task.get("agent")
            if agent_info and agent_info.get("status") == "active":
                task_id = task.get("id")
                agent_type = agent_info.get("type", "unknown")
                channel_name = agent_info.get("channel")
                if channel_name and channel_name not in self.squad_channels:
                    await self.create_squad_channel(task_id, agent_type)
    
    async def handle_agent_output(self, channel: str, content: str, role: str = "assistant"):
        """
        Handle agent output and display in appropriate channel.
        
        Improved version with better real-time streaming and channel filtering.
        Always updates state, but only displays in UI if channel is active or
        if "show all" mode is enabled.
        
        Args:
            channel: Channel name (e.g., "main", "squad-task-1-planner")
            content: Message content
            role: Message role ("user" or "assistant")
        """
        # Always update state (for persistence)
        self.state_manager.add_chat_message(channel, role, content)
        await self.state_manager.save_state()
        
        # Update channel message count
        if channel in self.squad_channels:
            if "message_count" not in self.squad_channels[channel]:
                self.squad_channels[channel]["message_count"] = 0
            self.squad_channels[channel]["message_count"] += 1
            # Update button label with count
            await self._update_channel_button_label(channel)
        
        # Display in UI only if this is the active channel
        try:
            # Normalize channel names
            display_channel = channel
            if channel == "main-orchestrator":
                display_channel = "main"
            
            # Only display if this is the active channel
            if (self.active_channel == channel or 
                self.active_channel == display_channel or 
                (self.active_channel == "main" and channel == "main-orchestrator")):
                log = self.app.query_one("#log-main", RichLog)
                
                if channel == "main" or channel == "main-orchestrator":
                    # Main channel
                    if role == "user":
                        log.write(f"[bold blue]User:[/] {content}")
                    else:
                        log.write(f"[bold green]Assistant:[/] {content}")
                else:
                    # Squad or shadow channel - format with better visual distinction
                    parts = channel.split("-")
                    if len(parts) >= 3:
                        task_id_short = parts[1][:8] if len(parts[1]) > 8 else parts[1]
                        agent_type = parts[2] if len(parts) > 2 else "agent"
                        
                        channel_label = f"{agent_type.title()}[{task_id_short}]"
                        if channel.startswith("shadow-"):
                            channel_label = f"Shadow:{agent_type.title()}[{task_id_short}]"
                        
                        if role == "user":
                            log.write(f"[bold blue][{channel_label}] User:[/] {content}")
                        else:
                            if channel.startswith("shadow-"):
                                log.write(f"[bold yellow][{channel_label}] {agent_type.title()}:[/] {content}")
                            else:
                                log.write(f"[bold cyan][{channel_label}] {agent_type.title()}:[/] {content}")
                    else:
                        # Fallback for unknown channel format
                        if role == "user":
                            log.write(f"[bold blue][{channel}] User:[/] {content}")
                        else:
                            log.write(f"[bold green][{channel}] Assistant:[/] {content}")
                
                # Ensure channel button exists
                if channel not in self.squad_channels and channel != "main" and channel != "main-orchestrator":
                    parts = channel.split("-")
                    if len(parts) >= 3:
                        task_id = parts[1]
                        agent_type = parts[2]
                        await self.create_squad_channel(task_id, agent_type)
        except Exception as e:
            logger.error(f"Error displaying agent output: {e}", exc_info=True)
    
    async def _update_channel_button_label(self, channel_name: str):
        """Update channel button label with message count.
        
        Args:
            channel_name: Name of the channel to update.
        """
        if channel_name not in self.squad_channels:
            return
        
        try:
            channel_info = self.squad_channels[channel_name]
            button_id = channel_info.get("button_id")
            if not button_id:
                return
            
            button = self.app.query_one(f"#{button_id}", Button)
            agent_type = channel_info.get("agent_type", "agent")
            task_id = channel_info.get("task_id", "")
            task_id_short = task_id[:8] if len(task_id) > 8 else task_id
            message_count = channel_info.get("message_count", 0)
            
            # Update button label with count
            label = f"{agent_type.title()}({task_id_short})"
            if message_count > 0:
                label += f" [{message_count}]"
            button.label = label
        except Exception as e:
            logger.debug(f"Could not update channel button label: {e}")
    
    def get_channel_summary(self) -> Dict[str, Any]:
        """Get summary of all channels with message counts.
        
        Returns:
            Dictionary mapping channel names to their info including message counts.
        """
        summary = {}
        for channel_name, channel_info in self.squad_channels.items():
            history = self.state_manager.get_chat_history(channel_name)
            summary[channel_name] = {
                "task_id": channel_info.get("task_id"),
                "agent_type": channel_info.get("agent_type"),
                "message_count": len(history),
                "is_active": channel_name == self.active_channel
            }
        return summary
