"""
Task Edit Screen - Modal screen for editing task details.
"""
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Input, Button, Label, Static
from textual import on
from typing import Dict, Any, Optional


class TaskEditScreen(ModalScreen):
    """Modal screen for editing a task's name and description."""
    
    CSS = """
    TaskEditScreen {
        align: center middle;
    }
    
    #edit-container {
        width: 60;
        height: auto;
        padding: 2;
        background: #161b22;
        border: thick #2ea043;
    }
    
    .edit-label {
        margin-top: 1;
        color: #8b949e;
    }
    
    .edit-input {
        margin-bottom: 1;
        width: 100%;
    }
    
    #edit-buttons {
        margin-top: 2;
        align: right middle;
    }
    
    #edit-buttons Button {
        margin-left: 1;
    }
    """
    
    def __init__(self, task: Dict[str, Any]):
        super().__init__()
        self.task = task
        self.task_id = task.get("id", "")
        self.task_name = task.get("name", "")
        self.task_description = task.get("description", "")
    
    def compose(self) -> ComposeResult:
        """Compose the edit UI."""
        with Container(id="edit-container"):
            yield Label(f"Edit Task: {self.task_id}", id="edit-title")
            
            yield Label("Name:", classes="edit-label")
            yield Input(value=self.task_name, id="edit-name", classes="edit-input")
            
            yield Label("Description:", classes="edit-label")
            yield Input(value=self.task_description, id="edit-description", classes="edit-input")
            
            with Horizontal(id="edit-buttons"):
                yield Button("Cancel", id="btn-cancel")
                yield Button("Save", id="btn-save", variant="primary")
    
    @on(Button.Pressed, "#btn-save")
    def on_save(self) -> None:
        """Save changes and close."""
        new_name = self.query_one("#edit-name", Input).value.strip()
        new_desc = self.query_one("#edit-description", Input).value.strip()
        
        self.dismiss({
            "name": new_name,
            "description": new_desc
        })
    
    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        """Cancel editing."""
        self.dismiss(None)
