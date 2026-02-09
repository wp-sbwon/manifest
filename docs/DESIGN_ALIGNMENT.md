# Design alignment

How the codebase aligns with the project’s design and intent (redesign: View = visualization only, OpenCode = chat/terminal/tools).

## Aligned (no action)

| Area | Design intent | Current state |
|------|----------------|---------------|
| **Entry** | Launcher starts View + OpenCode | `__main__.py` → launcher; View and OpenCode started as designed. |
| **View** | Visualization only; .manifest watch | ManifestViewApp: Diagram, Files, Timeline, Mission, Inspector. No chat. |
| **Chat/terminal** | OpenCode only; no duplicate | No Manifest chat UI. TerminalRouter is for programmatic agent execution, not a user terminal adapter. |
| **OpenCode terminal adapter** | Do not use | `terminal_router.is_opencode_available()` returns False; comment: "OpenCode terminal adapter removed". |
| **channel_manager** | Optional; fallback to state | AgentBridge takes optional `channel_manager`; when None, saves to state only. |
| **Config** | ConfigManager, .manifest/, .rules/ | ConfigManager and SkillsManager used directly. No settings screen in View. |

## Removed (design)

| Item | Reason |
|------|--------|
| **manifest.ui** | Chat TUI removed by redesign; only stub remained. Package removed. |
| **SettingsManager** | Unified settings layer for a settings UI that design does not include. Module removed. |

## Reference

- Redesign and legacy assessment: `docs/archive/pre-reorg-2026/REDESIGN_ARCHITECTURE_AND_INTENT.md`
- View app behavior: `docs/view-app.md`
