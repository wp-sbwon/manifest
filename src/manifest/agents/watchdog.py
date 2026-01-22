"""
Agent Watchdog - Monitors and supervises agent squad operations.
Detects hanging processes, resource issues, and other problems.
"""
import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from pathlib import Path
from manifest.core.state_manager import StateManager
from manifest.runtime.router.terminal_router import TerminalRouter


class AgentWatchdog:
    """
    Watchdog system for monitoring agent squad operations.
    Detects and handles:
    - Hanging terminal commands
    - Resource exhaustion
    - Agent unresponsiveness
    - Process failures
    """
    
    def __init__(
        self,
        state_manager: StateManager,
        terminal_router: Optional["TerminalRouter"],
        check_interval: float = 5.0,
        command_timeout: float = 300.0  # 5 minutes default
    ):
        """
        Initialize watchdog.
        
        Args:
            state_manager: State manager for persistence
            terminal_router: Terminal router to monitor
            check_interval: How often to check (seconds)
            command_timeout: Default timeout for commands (seconds)
        """
        self.state_manager = state_manager
        self.terminal_router: Optional["TerminalRouter"] = terminal_router
        self.check_interval = check_interval
        self.command_timeout = command_timeout
        
        self.monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._command_timestamps: Dict[str, float] = {}  # command_id -> start_time
        self._agent_status: Dict[str, Dict[str, Any]] = {}  # agent_id -> status
        self._alerts: List[Dict[str, Any]] = []
        self._alert_callbacks: List[Callable] = []
        
        # Resource monitor
        self.resource_monitor: Optional["ResourceMonitor"] = None
    
    async def start(self):
        """Start watchdog monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        # Start resource monitor if available
        if self.resource_monitor:
            await self.resource_monitor.start()
    
    async def stop(self):
        """Stop watchdog monitoring."""
        self.monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Stop resource monitor
        if self.resource_monitor:
            await self.resource_monitor.stop()
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                await asyncio.sleep(self.check_interval)
                
                # Check for hanging commands
                await self._check_hanging_commands()
                
                # Check agent responsiveness
                await self._check_agent_responsiveness()
                
                # Check resource usage
                await self._check_resources()
                
                # Check resource thresholds
                await self._check_resource_thresholds()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in watchdog loop: {e}")
    
    async def _check_hanging_commands(self):
        """Check for hanging terminal commands."""
        current_time = time.time()
        
        for command_id, start_time in list(self._command_timestamps.items()):
            elapsed = current_time - start_time
            
            if elapsed > self.command_timeout:
                # Command is hanging
                await self._handle_hanging_command(command_id, elapsed)
    
    async def _handle_hanging_command(self, command_id: str, elapsed: float):
        """
        Handle a hanging command.
        
        Args:
            command_id: Command identifier
            elapsed: Time elapsed since command started
        """
        # Cancel the command
        if hasattr(self.terminal_router, 'cancel_command'):
            self.terminal_router.cancel_command(command_id)
        
        # Remove from tracking
        if command_id in self._command_timestamps:
            del self._command_timestamps[command_id]
        
        # Create alert
        alert = {
            "type": "hanging_command",
            "severity": "high",
            "command_id": command_id,
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now().isoformat(),
            "action": "cancelled"
        }
        
        await self._raise_alert(alert)
    
    async def _check_agent_responsiveness(self):
        """Check if agents are responsive."""
        # Get active agents from state
        state = self.state_manager.get_state()
        tasks = state.get("task_checklist", [])
        
        for task in tasks:
            agent_info = task.get("agent")
            if not agent_info:
                continue
            
            agent_id = task.get("id")
            agent_type = agent_info.get("type")
            status = agent_info.get("status")
            
            # Check last activity timestamp
            last_activity = agent_info.get("last_activity")
            if last_activity:
                try:
                    last_time = datetime.fromisoformat(last_activity)
                    elapsed = datetime.now() - last_time
                    
                    # If no activity for 10 minutes, consider unresponsive
                    if elapsed > timedelta(minutes=10):
                        await self._handle_unresponsive_agent(agent_id, agent_type, elapsed)
                except Exception:
                    pass
    
    async def _handle_unresponsive_agent(
        self,
        agent_id: str,
        agent_type: str,
        elapsed: timedelta
    ):
        """Handle an unresponsive agent."""
        alert = {
            "type": "unresponsive_agent",
            "severity": "medium",
            "agent_id": agent_id,
            "agent_type": agent_type,
            "elapsed_minutes": elapsed.total_seconds() / 60,
            "timestamp": datetime.now().isoformat(),
            "action": "monitoring"
        }
        
        await self._raise_alert(alert)
    
    async def _check_resources(self):
        """Check resource usage."""
        # This would integrate with container stats or system monitoring
        # For now, we'll check terminal router's active commands count
        if hasattr(self.terminal_router, 'active_commands'):
            active_count = len(self.terminal_router.active_commands)
            
            # Alert if too many concurrent commands
            if active_count > 10:
                alert = {
                    "type": "resource_warning",
                    "severity": "medium",
                    "metric": "active_commands",
                    "value": active_count,
                    "threshold": 10,
                    "timestamp": datetime.now().isoformat(),
                    "action": "monitoring"
                }
                await self._raise_alert(alert)
    
    async def _check_resource_thresholds(self):
        """Check resource usage against thresholds."""
        if not self.resource_monitor:
            return
        
        thresholds = {
            "system.cpu_percent": 80.0,
            "system.memory.percent": 85.0,
            "system.disk.percent": 90.0
        }
        
        violations = self.resource_monitor.check_thresholds(thresholds)
        
        for violation in violations:
            alert = {
                "type": "resource_threshold",
                "severity": "high" if violation["value"] > violation["threshold"] * 1.1 else "medium",
                "metric": violation["metric"],
                "value": violation["value"],
                "threshold": violation["threshold"],
                "timestamp": violation["timestamp"],
                "action": "monitoring"
            }
            await self._raise_alert(alert)
    
    def set_resource_monitor(self, resource_monitor: "ResourceMonitor"):
        """Set resource monitor instance."""
        self.resource_monitor = resource_monitor
    
    async def _raise_alert(self, alert: Dict[str, Any]):
        """Raise an alert and notify callbacks."""
        self._alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self._alerts) > 100:
            self._alerts = self._alerts[-100:]
        
        # Notify callbacks
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                print(f"Error in alert callback: {e}")
        
        # Save to state
        await self._save_alert(alert)
    
    async def _save_alert(self, alert: Dict[str, Any]):
        """Save alert to state."""
        state = self.state_manager.get_state()
        alerts = state.get("watchdog_alerts", [])
        alerts.append(alert)
        
        # Keep only last 50 alerts in state
        if len(alerts) > 50:
            alerts = alerts[-50:]
        
        state["watchdog_alerts"] = alerts
        await self.state_manager.save_state()
    
    def register_command(self, command_id: str):
        """Register a command for monitoring."""
        self._command_timestamps[command_id] = time.time()
    
    def unregister_command(self, command_id: str):
        """Unregister a command from monitoring."""
        if command_id in self._command_timestamps:
            del self._command_timestamps[command_id]
    
    def add_alert_callback(self, callback: Callable):
        """Add a callback for alerts."""
        self._alert_callbacks.append(callback)
    
    def get_alerts(
        self,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent alerts.
        
        Args:
            alert_type: Filter by alert type
            severity: Filter by severity
            limit: Maximum number of alerts to return
            
        Returns:
            List of alerts
        """
        alerts = self._alerts
        
        if alert_type:
            alerts = [a for a in alerts if a.get("type") == alert_type]
        
        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]
        
        return alerts[-limit:]
    
    def get_status(self) -> Dict[str, Any]:
        """Get watchdog status."""
        return {
            "monitoring": self.monitoring,
            "active_commands": len(self._command_timestamps),
            "recent_alerts": len([a for a in self._alerts if 
                                 datetime.fromisoformat(a["timestamp"]) > 
                                 datetime.now() - timedelta(hours=1)]),
            "total_alerts": len(self._alerts)
        }
