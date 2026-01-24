"""
Command Handler - Handles user commands with routing.
Replaces the large if-elif chain in ManifestApp.process_command.
"""
from typing import Dict, Any, Optional, Callable, Awaitable, List
from textual.widgets import RichLog
from manifest.ui.commands.command_parser import CommandParser


class CommandHandler:
    """Handles user commands with routing."""
    
    def __init__(self, app: Any):
        """
        Initialize Command Handler.
        
        Args:
            app: ManifestApp instance
        """
        self.app = app
        self.parser = CommandParser()
        self.handlers: Dict[str, Callable[[List[str], RichLog], Awaitable[None]]] = {}
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all command handlers."""
        self.handlers = {
            "audit": self._handle_audit,
            "reload": self._handle_reload,
            "status": self._handle_status,
            "start_agent": self._handle_start_agent,
            "stop_agent": self._handle_stop_agent,
            "sync_blueprints": self._handle_sync_blueprints,
            "resolve_conflict": self._handle_resolve_conflict,
            "config": self._handle_config,
            "sprint_history": self._handle_sprint_history,
            "orchestrator": self._handle_orchestrator,
            "create_task": self._handle_create_task,
            "update_task": self._handle_update_task,
            "delete_task": self._handle_delete_task,
            "list_tasks": self._handle_list_tasks,
            "approve_sprint": self._handle_approve_sprint,
            "start_sprint": self._handle_start_sprint,
            "apply_blueprint_updates": self._handle_apply_blueprint_updates,
            "apply_blueprint_update": self._handle_apply_blueprint_update,
            "shadow_status": self._handle_shadow_status,
            "shadow_stop": self._handle_shadow_stop,
        }
    
    async def handle(self, user_input: str, log: RichLog) -> bool:
        """
        Handle user input (command or regular message).
        
        Args:
            user_input: User input string
            log: RichLog widget for output
            
        Returns:
            True if handled as command, False if regular message
        """
        if not user_input.startswith("/"):
            return False
        
        command, args = self.parser.parse(user_input)
        
        if command in self.handlers:
            await self.handlers[command](args, log)
            return True
        else:
            log.write(f"[bold yellow]Unknown command: {command}[/]")
            return True
    
    async def _handle_audit(self, args: List[str], log: RichLog):
        """Handle /audit command."""
        log.write("[bold green]Running drift audit...[/]")
        await self.app.audit_drift()
        log.write("[bold green]Drift audit complete.[/]")
    
    async def _handle_reload(self, args: List[str], log: RichLog):
        """Handle /reload command."""
        await self.app.load_intent_data()
        await self.app.load_blueprint_data()
        await self.app.load_project_data()
        await self.app.update_architect_view()
        await self.app.update_blueprint_view()
        await self.app.update_project_view()
        log.write("[bold green]Data reloaded.[/]")
    
    async def _handle_status(self, args: List[str], log: RichLog):
        """Handle /status command."""
        if self.app.agent_bridge and self.app.agent_bridge.is_connected:
            status = await self.app.agent_bridge.get_status()
            log.write(f"[bold green]Status: {status}[/]")
        else:
            log.write("[bold yellow]Agent bridge not connected.[/]")
    
    async def _handle_start_agent(self, args: List[str], log: RichLog):
        """Handle /start_agent command."""
        if len(args) < 1:
            log.write("[bold yellow]Usage: /start_agent <task_id> [agent_type][/]")
            return
        
        task_id = args[0]
        agent_type = args[1] if len(args) > 1 else "coder"
        
        if self.app.agent_coordinator:
            log.write(f"[bold green]Starting {agent_type} agent for task {task_id}...[/]")
            success = await self.app.agent_coordinator.start_worker_agent(task_id, agent_type)
            if success:
                log.write(f"[bold green]Agent started. Channel: squad-{task_id}-{agent_type}[/]")
                await self.app.update_squad_channels()
            else:
                log.write(f"[bold red]Failed to start agent.[/]")
        else:
            log.write("[bold yellow]Agent coordinator not available.[/]")
    
    async def _handle_stop_agent(self, args: List[str], log: RichLog):
        """Handle /stop_agent command."""
        if len(args) < 1:
            log.write("[bold yellow]Usage: /stop_agent <task_id>[/]")
            return
        
        task_id = args[0]
        if self.app.agent_coordinator:
            success = await self.app.agent_coordinator.stop_agent(task_id)
            if success:
                log.write(f"[bold green]Agent stopped for task {task_id}.[/]")
                await self.app.update_squad_channels()
            else:
                log.write(f"[bold red]Failed to stop agent.[/]")
        else:
            log.write("[bold yellow]Agent coordinator not available.[/]")
    
    async def _handle_sync_blueprints(self, args: List[str], log: RichLog):
        """Handle /sync_blueprints command."""
        log.write("[bold green]Synchronizing blueprints...[/]")
        await self.app.sync_blueprints()
        log.write("[bold green]Blueprint sync complete.[/]")
    
    async def _handle_resolve_conflict(self, args: List[str], log: RichLog):
        """Handle /resolve_conflict command."""
        if len(args) < 1:
            log.write("[bold red]Usage: /resolve_conflict <conflict_id> [approved|rejected][/]")
            return
        
        conflict_id = args[0]
        action = args[1] if len(args) > 1 else "approved"
        await self.app.resolve_conflict(conflict_id, action)
        log.write(f"[bold green]Conflict {conflict_id} {action}.[/]")
    
    async def _handle_config(self, args: List[str], log: RichLog):
        """Handle /config command."""
        initial_tab = args[0] if args else "api_keys"
        tab_map = {
            "api_keys": "api_keys",
            "keys": "api_keys",
            "models": "models",
            "skills": "skills",
            "policy": "policy"
        }
        tab = tab_map.get(initial_tab, "api_keys")
        self.app.action_open_settings(tab)
    
    async def _handle_sprint_history(self, args: List[str], log: RichLog):
        """Handle /sprint_history command."""
        await self.app.show_sprint_history()
    
    async def _handle_orchestrator(self, args: List[str], log: RichLog):
        """Handle /orchestrator command."""
        await self.app.show_orchestrator_chat()
    
    async def _handle_create_task(self, args: List[str], log: RichLog):
        """Handle /create_task command."""
        if len(args) < 1:
            log.write("[bold yellow]Usage: /create_task <name> [description] [stage] [status] [sprint_id][/]")
            return
        
        name = args[0] if args else "New Task"
        description = args[1] if len(args) > 1 else ""
        stage = args[2] if len(args) > 2 else "planning"
        status = args[3] if len(args) > 3 else "pending"
        sprint_id = args[4] if len(args) > 4 else None
        
        task_id = self.app.state_manager.create_task(
            name=name,
            description=description,
            stage=stage,
            status=status,
            sprint_id=sprint_id
        )
        await self.app.state_manager.save_state()
        await self.app._load_project_data()
        log.write(f"[bold green]Task created: {task_id} - {name}[/]")
    
    async def _handle_update_task(self, args: List[str], log: RichLog):
        """Handle /update_task command."""
        if len(args) < 1:
            log.write("[bold yellow]Usage: /update_task <task_id> [name=value] [status=value] ...[/]")
            return
        
        task_id = args[0]
        updates = self.parser.parse_key_value_pairs(
            args[1:],
            allowed_keys=["name", "description", "status", "stage"]
        )
        
        if updates:
            success = self.app.state_manager.update_task(task_id, **updates)
            if success:
                await self.app.state_manager.save_state()
                await self.app._load_project_data()
                log.write(f"[bold green]Task {task_id} updated.[/]")
            else:
                log.write(f"[bold red]Task {task_id} not found.[/]")
        else:
            log.write("[bold yellow]No updates specified. Usage: /update_task <task_id> [name=value] [status=value] ...[/]")
    
    async def _handle_delete_task(self, args: List[str], log: RichLog):
        """Handle /delete_task command."""
        if len(args) < 1:
            log.write("[bold yellow]Usage: /delete_task <task_id>[/]")
            return
        
        task_id = args[0]
        success = self.app.state_manager.delete_task(task_id)
        if success:
            await self.app.state_manager.save_state()
            await self.app._load_project_data()
            log.write(f"[bold green]Task {task_id} deleted.[/]")
        else:
            log.write(f"[bold red]Task {task_id} not found.[/]")
    
    async def _handle_list_tasks(self, args: List[str], log: RichLog):
        """Handle /list_tasks command."""
        filters = self.parser.parse_filters(args)
        status = filters.get("status")
        stage = filters.get("stage")
        sprint_id = filters.get("sprint")
        
        tasks = self.app.state_manager.find_tasks(status=status, stage=stage, sprint_id=sprint_id)
        if tasks:
            log.write(f"[bold green]Found {len(tasks)} task(s):[/]")
            for task in tasks:
                task_id = task.get("id", "unknown")
                name = task.get("name", "Unnamed")
                task_status = task.get("status", "pending")
                task_stage = task.get("stage", "planning")
                log.write(f"  • {task_id}: {name} [{task_status}] [{task_stage}]")
        else:
            log.write("[bold yellow]No tasks found.[/]")
    
    async def _handle_approve_sprint(self, args: List[str], log: RichLog):
        """Handle /approve_sprint command."""
        if len(args) < 1:
            log.write("[bold yellow]Usage: /approve_sprint <sprint_id>[/]")
            return
        
        sprint_id = args[0]
        await self.app.show_sprint_approval_ui(sprint_id)
    
    async def _handle_start_sprint(self, args: List[str], log: RichLog):
        """Handle /start_sprint command."""
        if len(args) < 1:
            log.write("[bold yellow]Usage: /start_sprint <sprint_id>[/]")
            return
        
        sprint_id = args[0]
        if self.app.agent_coordinator:
            log.write(f"[bold green]Starting Sprint {sprint_id}...[/]")
            result = await self.app.agent_coordinator.start_sprint(sprint_id)
            if result.get("success"):
                log.write(f"[bold green]Sprint started. {len(result.get('started_tasks', []))} tasks started.[/]")
            else:
                log.write(f"[bold red]Failed to start Sprint: {result.get('error', 'Unknown error')}[/]")
        else:
            log.write("[bold yellow]Agent coordinator not available.[/]")
    
    async def _handle_apply_blueprint_updates(self, args: List[str], log: RichLog):
        """Handle /apply_blueprint_updates command."""
        if not self.app._pending_blueprint_suggestions:
            log.write("[bold yellow]No pending Blueprint update suggestions.[/]")
            return
        
        log.write(f"[bold green]Applying {len(self.app._pending_blueprint_suggestions)} Blueprint updates...[/]")
        results = self.app.structure_manager.apply_blueprint_updates_batch(
            self.app._pending_blueprint_suggestions,
            auto_apply=True
        )
        if results["applied"] > 0:
            log.write(f"[bold green]Applied {results['applied']} updates successfully.[/]")
            self.app._pending_blueprint_suggestions = []
            await self.app.load_blueprint_data()
            await self.app._load_structure_data()
        if results["failed"] > 0:
            log.write(f"[bold red]Failed to apply {results['failed']} updates.[/]")
            for error in results["errors"][:5]:
                log.write(f"  • {error}")
    
    async def _handle_apply_blueprint_update(self, args: List[str], log: RichLog):
        """Handle /apply_blueprint_update command."""
        if len(args) < 1:
            log.write("[bold yellow]Usage: /apply_blueprint_update <index>[/]")
            return
        
        try:
            index = int(args[0])
            if 0 <= index < len(self.app._pending_blueprint_suggestions):
                suggestion = self.app._pending_blueprint_suggestions[index]
                log.write(f"[bold green]Applying Blueprint update: {suggestion.suggestion_type}...[/]")
                success = self.app.structure_manager.apply_blueprint_update(suggestion, auto_apply=True)
                if success:
                    log.write(f"[bold green]Update applied successfully.[/]")
                    self.app._pending_blueprint_suggestions.pop(index)
                    await self.app.load_blueprint_data()
                    await self.app._load_structure_data()
                else:
                    log.write(f"[bold red]Failed to apply update.[/]")
            else:
                log.write(f"[bold yellow]Invalid index. Available: 0-{len(self.app._pending_blueprint_suggestions)-1}[/]")
        except ValueError:
            log.write("[bold yellow]Usage: /apply_blueprint_update <index>[/]")
    
    async def _handle_shadow_status(self, args: List[str], log: RichLog):
        """Handle /shadow_status command."""
        if self.app.agent_bridge and self.app.agent_bridge.shadow_manager:
            processes = self.app.agent_bridge.shadow_manager.list_active_processes()
            if processes:
                log.write(f"[bold cyan]Active Shadow Processes: {len(processes)}[/]")
                for proc in processes[:10]:
                    status_icon = "✅" if proc["status"] == "completed" else "⚡" if proc["status"] == "running" else "❌"
                    log.write(f"  {status_icon} {proc['process_id']}: {proc['agent_type']} [{proc['status']}]")
                    if proc.get("end_time"):
                        log.write(f"    Completed: {proc['end_time']}")
            else:
                log.write("[bold yellow]No active shadow processes.[/]")
        else:
            log.write("[bold yellow]Shadow Manager not available.[/]")
    
    async def _handle_shadow_stop(self, args: List[str], log: RichLog):
        """Handle /shadow_stop command."""
        if len(args) < 1:
            log.write("[bold yellow]Usage: /shadow_stop <process_id>[/]")
            return
        
        process_id = args[0]
        if self.app.agent_bridge and self.app.agent_bridge.shadow_manager:
            success = await self.app.agent_bridge.shadow_manager.stop_shadow_process(process_id)
            if success:
                log.write(f"[bold green]Shadow process {process_id} stopped.[/]")
            else:
                log.write(f"[bold red]Failed to stop shadow process {process_id}.[/]")
        else:
            log.write("[bold yellow]Shadow Manager not available.[/]")
