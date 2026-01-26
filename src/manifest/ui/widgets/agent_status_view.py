"""
Agent Status View - Display detailed status of active agents.

This module provides widgets for displaying real-time status information
about active agents including CPU usage, memory consumption, execution time,
and current stage.
"""
from typing import Dict, Any, List, Optional
from textual.widgets import Static, RichLog
from textual.containers import Vertical, Horizontal, VerticalScroll
from datetime import datetime, timedelta
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class AgentStatusCard(Static):
    """Card displaying status of a single agent."""

    def __init__(self, task_id: str, agent_info: Dict[str, Any], *args, **kwargs):
        """Initialize agent status card.

        Args:
            task_id: Task ID the agent is working on.
            agent_info: Dictionary containing agent status information.
        """
        super().__init__(*args, **kwargs)
        self.task_id = task_id
        self.agent_info = agent_info
        self._start_time: Optional[datetime] = None

        # Parse start time if available
        if "started_at" in agent_info:
            try:
                self._start_time = datetime.fromisoformat(agent_info["started_at"])
            except (ValueError, TypeError):
                pass
        elif "created_at" in agent_info:
            try:
                self._start_time = datetime.fromisoformat(agent_info["created_at"])
            except (ValueError, TypeError):
                pass

    def update_info(self, agent_info: Dict[str, Any]):
        """Update agent information.

        Args:
            agent_info: Updated agent status information.
        """
        self.agent_info = agent_info
        self.refresh()

    def render(self) -> str:
        """Render the agent status card."""
        agent_type = self.agent_info.get("agent_type", "unknown")
        status = self.agent_info.get("status", "unknown")
        stage = self.agent_info.get("stage", "unknown")
        channel = self.agent_info.get("channel", "unknown")
        execution_mode = self.agent_info.get("execution_mode", "direct")

        # Status icon
        status_icon = {
            "active": "⚡",
            "in_progress": "⚡",
            "completed": "✅",
            "failed": "❌",
            "stopped": "⏸",
            "pending": "⏳"
        }.get(status, "○")

        lines = []
        lines.append(f"[bold cyan]{status_icon} {self.task_id}: {agent_type}[/]")
        lines.append(f"Status: [bold]{status}[/]")
        lines.append(f"Stage: {stage}")
        lines.append(f"Channel: {channel}")
        lines.append(f"Mode: {execution_mode}")

        # Resource usage (if available)
        data = self.agent_info.get("data", {})
        cpu_usage = data.get("cpu_usage")
        memory_usage = data.get("memory_usage")
        memory_limit = data.get("memory_limit")

        if cpu_usage is not None:
            cpu_color = "green" if cpu_usage < 50 else "yellow" if cpu_usage < 80 else "red"
            lines.append(f"CPU: [{cpu_color}]{cpu_usage:.1f}%[/]")
            # Add CPU bar chart
            cpu_bar = self._create_bar_chart(cpu_usage, 20)
            lines.append(f"     [{cpu_color}]{cpu_bar}[/]")

        if memory_usage is not None:
            memory_mb = memory_usage / (1024 * 1024) if memory_usage > 0 else 0
            if memory_limit:
                memory_limit_mb = memory_limit / (1024 * 1024)
                memory_pct = (memory_usage / memory_limit * 100) if memory_limit > 0 else 0
                memory_color = "green" if memory_pct < 50 else "yellow" if memory_pct < 80 else "red"
                lines.append(f"Memory: [{memory_color}]{memory_mb:.0f}MB/{memory_limit_mb:.0f}MB ({memory_pct:.1f}%)[/]")
                # Add memory bar chart
                memory_bar = self._create_bar_chart(memory_pct, 20)
                lines.append(f"        [{memory_color}]{memory_bar}[/]")
            else:
                lines.append(f"Memory: {memory_mb:.0f}MB")

        # Execution time
        if self._start_time:
            runtime = datetime.now() - self._start_time
            runtime_str = self._format_runtime(runtime)
            lines.append(f"Runtime: {runtime_str}")

        # Container ID (if container mode)
        if execution_mode == "container":
            container_id = data.get("container_id")
            if container_id:
                lines.append(f"Container: {container_id[:12]}...")

        return "\n".join(lines)

    def _format_runtime(self, runtime: timedelta) -> str:
        """Format runtime duration.

        Args:
            runtime: Time delta representing runtime.

        Returns:
            Formatted string like "2m 34s" or "1h 23m".
        """
        total_seconds = int(runtime.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def _create_bar_chart(self, percentage: float, width: int = 20) -> str:
        """Create an ASCII bar chart for resource usage.

        Args:
            percentage: Percentage value (0-100).
            width: Width of the bar in characters.

        Returns:
            ASCII bar chart string.
        """
        filled = int(percentage / 100 * width)
        empty = width - filled
        bar = "█" * filled + "░" * empty
        return bar


class AgentStatusView(VerticalScroll):
    """View displaying status of all active agents."""

    def __init__(self, *args, **kwargs):
        """Initialize agent status view."""
        super().__init__(*args, **kwargs)
        self.agent_cards: Dict[str, AgentStatusCard] = {}
        self.app_ref: Optional[Any] = None

    def set_app(self, app: Any):
        """Set reference to app for accessing agent coordinator.

        Args:
            app: ManifestApp instance.
        """
        self.app_ref = app

    async def update_agents(self):
        """Update agent status cards with current information."""
        if not self.app_ref or not self.app_ref.agent_coordinator:
            # Clear all cards if no coordinator
            for card in self.agent_cards.values():
                try:
                    await card.remove()
                except Exception:
                    pass
            self.agent_cards.clear()
            return

        # Get active agents
        active_agents = self.app_ref.agent_coordinator.get_active_agents()

        # Get detailed status for each agent
        current_task_ids = set()
        for task_id, agent_info in active_agents.items():
            if agent_info.get("status") == "active":
                current_task_ids.add(task_id)

                # Get detailed status
                try:
                    detailed_status = await self.app_ref.agent_coordinator.get_agent_status(task_id)
                    if detailed_status and detailed_status.get("status") != "not_active":
                        # Merge detailed status into agent_info
                        agent_info.update(detailed_status.get("data", {}))
                        agent_info["status"] = detailed_status.get("status", agent_info.get("status"))
                except Exception as e:
                    logger.debug(f"Could not get detailed status for {task_id}: {e}")

                # Update or create card
                if task_id in self.agent_cards:
                    self.agent_cards[task_id].update_info(agent_info)
                else:
                    card = AgentStatusCard(task_id, agent_info)
                    self.agent_cards[task_id] = card
                    await self.mount(card)

        # Remove cards for inactive agents
        for task_id in list(self.agent_cards.keys()):
            if task_id not in current_task_ids:
                card = self.agent_cards.pop(task_id)
                try:
                    await card.remove()
                except Exception:
                    pass

        # If no active agents, show message
        if not self.agent_cards:
            try:
                # Check if message already exists
                existing = self.query_one("#no-active-agents", raise_if_missing=False)
                if not existing:
                    no_agents = Static("[dim]No active agents[/]", id="no-active-agents")
                    await self.mount(no_agents)
            except Exception:
                pass
        else:
            # Remove message if agents exist
            try:
                existing = self.query_one("#no-active-agents", raise_if_missing=False)
                if existing:
                    await existing.remove()
            except Exception:
                pass

    def compose(self):
        """Compose the view."""
        # Cards will be added dynamically
        yield Static("[bold]Active Agents Status[/]", id="agent-status-header")
        # Agent cards and "no active agents" message will be mounted via update_agents()
