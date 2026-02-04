import asyncio
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll, Grid
from textual.widgets import Header, Footer, Tree, Input, RichLog, TabbedContent, TabPane, Static, Label
from textual import on, work

# --- MOCK DATA ---
ARCHITECT_DATA = {
    "sprint": "Sprint 2: Order & Payment",
    "progress": 50,
    "features": [
        {
            "name": "🔐 Auth System",
            "status": "In Progress",
            "reqs": [
                {"id": "REQ-01", "desc": "Login UI", "state": "done"},
                {"id": "REQ-02", "desc": "OAuth Widget", "state": "wip"},
            ]
        }
    ]
}

class ManifestApp(App):
    """Manifest AI Native IDE - Unified Control Edition"""

    CSS = """
    /* --- Global Theme --- */
    Screen { background: #0d1117; color: #c9d1d9; }

    /* --- Layout Regions --- */
    #sidebar {
        width: 30;
        dock: left;
        background: #161b22;
        border-right: solid #30363d;
        height: 100%;
    }

    #main-workspace {
        height: 65%;
        layout: horizontal; /* left-right split */
    }

    #bottom-panel {
        height: 35%;
        dock: bottom;
        background: #161b22;
        border-top: solid #30363d;
    }

    /* --- Workspace Split --- */
    #design-side {
        width: 60%;
        background: #0d1117;
        border-right: solid #30363d;
    }

    #inspector-side {
        width: 40%;
        background: #090c10;
        padding: 1;
    }

    /* --- Common Widgets --- */
    Tree { background: #161b22; padding: 1; color: #c9d1d9; }
    RichLog { background: #0d1117; color: #8b949e; border: none; padding: 1; }
    TabbedContent { background: #161b22; height: 100%; }
    ContentSwitcher { background: #0d1117; height: 100%; }
    TabPane { height: 100%; padding: 1; }

    #global-input {
        dock: bottom;
        border: none;
        border-top: solid #2ea043;
        background: #1e1e1e;
        color: #c9d1d9;
        height: 3;
    }

    .status-header { background: #21262d; color: #8b949e; text-align: center; text-style: bold; padding: 1; }
    .side-title { color: #8b949e; text-style: bold; margin-bottom: 1; padding: 0 1; }

    /* --- Architect Diagram --- */
    .feature-card {
        width: 100%;
        height: auto;
        border: solid #2ea043;
        background: #161b22;
        margin-bottom: 1;
        padding: 1;
    }
    .card-title { text-align: center; background: #2ea043; color: #0d1117; text-style: bold; margin-bottom: 1; }
    .req-item { color: #c9d1d9; padding-left: 1; }
    .req-done { color: #3fb950; }

    /* --- Blueprint Diagram --- */
    .blueprint-grid {
        layout: grid;
        grid-size: 3 1;
        grid-columns: 1fr 1fr 1fr;
        height: 100%;
    }
    .zone-box { border: dashed #30363d; background: #0d1117; padding: 1; margin: 0 1; }
    .zone-title { text-align: center; text-style: bold; border-bottom: solid #30363d; margin-bottom: 1; }
    .component-box { border: solid #8b949e; background: #21262d; margin-bottom: 1; padding: 0 1; text-align: center; }
    .comp-active { border: solid #2ea043; background: #1a2e1e; }

    /* --- Inspector Styles --- */
    .inspector-card {
        background: #161b22;
        border: round #30363d;
        margin-bottom: 1;
        padding: 1;
    }
    .insp-header { color: #3fb950; text-style: bold; margin-bottom: 1; }
    .visual-preview {
        background: white;
        color: black;
        text-align: center;
        padding: 2;
        margin-bottom: 1;
    }
    .data-trace {
        color: #79c0ff;
        background: #0d1117;
        padding: 1;
    }

    /* Added classes for the fix */
    .match-status {
        color: green;
        text-align: center;
    }

    #insp-data {
        display: none;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+b", "toggle_sidebar", "Sidebar toggle"),
        ("i", "toggle_inspector", "Inspector toggle"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal():
            # 1. Mission Control
            with Vertical(id="sidebar"):
                yield Label("MISSION CONTROL", classes="status-header")
                yield Tree("Active Missions", id="task-tree")

            # 2. Unified Workspace (Split Side-by-Side)
            with Container(id="main-workspace"):
                # 2-A. Design Side (Architect / Blueprint)
                with Vertical(id="design-side"):
                    with TabbedContent(id="design-tabs"):
                        with TabPane("Architect (Intent)", id="tab-architect"):
                            with VerticalScroll():
                                yield Label("📊 Sprint Progress: 50%", classes="side-title")
                                with Vertical(classes="feature-card"):
                                    yield Label("🔐 Auth System", classes="card-title")
                                    yield Label("✔ REQ-01: Login UI", classes="req-item req-done")
                                    yield Label("⚡ REQ-02: OAuth Widget", classes="req-item")

                        with TabPane("Blueprint (Structure)", id="tab-blueprint"):
                            with Grid(classes="blueprint-grid"):
                                with Vertical(classes="zone-box"):
                                    yield Label("📱 CLIENT", classes="zone-title")
                                    yield Label("LoginButton", classes="component-box comp-active")
                                with Vertical(classes="zone-box"):
                                    yield Label("⚙️ SERVER", classes="zone-title")
                                    yield Label("AuthService", classes="component-box comp-active")
                                with Vertical(classes="zone-box"):
                                    yield Label("💾 DATA", classes="zone-title")
                                    yield Label("UserDB", classes="component-box")

                # 2-B. Inspector Side (Verification)
                with Vertical(id="inspector-side"):
                    yield Label("INSPECTOR (Verification)", classes="side-title")

                    # Context-sensitive Content
                    with Container(id="inspector-content"):
                        # Visual Mode (default for Architect)
                        with Vertical(id="insp-visual"):
                            with Vertical(classes="inspector-card"):
                                yield Label("LIVE UI PREVIEW", classes="insp-header")
                                yield Label("------------------\n|  [ Google ]   |\n|  Login Here   |\n------------------", classes="visual-preview")
                                # Fixed: Moved style to .match-status class
                                yield Label("✅ Design Match: 100%", classes="match-status")

                        # Data Mode (for Blueprint)
                        # Fixed: Moved 'display: none' to CSS #insp-data selector
                        with Vertical(id="insp-data"):
                            with Vertical(classes="inspector-card"):
                                yield Label("EXECUTION TRACE", classes="insp-header")
                                yield Label("> AuthService.verify()\n> JWT.sign(payload)\n> DB.Users.find(id: 1)\n\nResult: 200 OK", classes="data-trace")

            # 3. Bottom Panel
            with Container(id="bottom-panel"):
                with TabbedContent(id="chat-tabs"):
                    with TabPane("Manifest AI", id="tab-main"):
                        yield RichLog(id="log-main", markup=True)
                    with TabPane("Squad: Auth", id="tab-auth"):
                        yield RichLog(id="log-auth", markup=True)

                yield Input(placeholder="Enter command...", id="global-input")

        yield Footer()

    def on_mount(self) -> None:
        tree = self.query_one("#task-tree", Tree)
        tree.root.expand()
        t101 = tree.root.add("[bold green]🚀 TASK-101: Social Login[/]", expand=True)
        t101.data = "tab-auth"

        self.query_one("#log-main").write("[bold green]Manifest AI[/] initialized.\nUse [Tab] to switch Design/Structure and [I] to toggle Inspector.")
        self.query_one("#global-input").focus()

    @on(TabbedContent.TabActivated, "#design-tabs")
    def on_tab_switched(self, event: TabbedContent.TabActivated) -> None:
        """Sync inspector content when design tab changes."""
        visual_pane = self.query_one("#insp-visual")
        data_pane = self.query_one("#insp-data")

        if event.pane.id == "tab-architect":
            visual_pane.styles.display = "block"
            data_pane.styles.display = "none"
        else:
            visual_pane.styles.display = "none"
            data_pane.styles.display = "block"

    def action_toggle_inspector(self) -> None:
        """Toggle inspector panel visibility."""
        side = self.query_one("#inspector-side")
        side.styles.display = "none" if side.styles.display == "block" else "block"

    @on(Input.Submitted)
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value.strip()
        if not user_input: return
        self.query_one("#global-input").value = ""

        log = self.query_one("#log-main", RichLog)
        log.write(f"[bold blue]User:[/]{user_input}")

        # Simulate AI response
        await self.process_ai(user_input, log)

    @work(exclusive=False)
    async def process_ai(self, user_input, log):
        await asyncio.sleep(0.5)
        log.write(f"[bold green]Manifest AI:[/] Analyzing {user_input}. Check Inspector for live status.")

if __name__ == "__main__":
    app = ManifestApp()
    app.run()
