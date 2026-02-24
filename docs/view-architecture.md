# View architecture

Directory layout and responsibilities for the Manifest View TUI. See [view-app](view-app.md) for UI behavior and data sources.

## Directory structure

```
view/
  app.py                 # Textual app: lifecycle, layout, keybindings, data → content → widgets
  constants.py           # Default labels, inspector accent, diagram title
  data_access.py         # Timeline events, chat/shadow state, health metrics (wraps GitManager, StateManager)
  entity_model.py        # View pipeline: get_entities_for_view, view schema, comp_status
  file_watcher.py        # Watch .manifest for changes, trigger refresh
  views_content.py       # Shared display helpers (status_label, entities_for_display, etc.)
  content/               # Content builders: data in → str or Rich renderable out
    __init__.py
    header_content.py    # Header strip (Planning/Differences, STATUS, TIME), tab bar
    inspector_content.py # Inspector: node view, diff table, sections, deviation formatting
    sidebar_content.py   # Sidebar: health summary, view-name text
    main_views.py        # Files view (source tree), Timeline view (event list)
  diagram/               # Diagram spec, config load, render (TUI)
```

## Layers

| Layer | Role |
|-------|------|
| **app.py** | Compose UI, handle keys, cache design/code blueprints, call content builders with current data, update widgets. No long content-construction blocks. |
| **view/content/** | Pure or near-pure content: take dicts/lists (e.g. comp_status, blueprints, view_entity) and return strings or Rich types. No I/O, no app state. |
| **views_content.py** | Helpers used by app and content (e.g. status_color_tag, entities_for_display). |
| **entity_model.py** | Load/validate/compare blueprints, build view schema, write blueprint_view.json. |
| **data_access.py** | Timeline (git), chat/shadow state, health metrics. app.py imports from data_access, not core. |

## Content API

- **header_content**: `build_header_strip_content(comp_status, right_panel_differences, time_str)`, `build_tab_bar_content(current_view_value)`
- **inspector_content**: `format_for_display`, `inspection_section`, `deviation_box`, `deviates_at`, `deviations_from_view_entity`, `build_info_hub_node_content`, `build_info_hub_diff_view`
- **sidebar_content**: `get_sidebar_health_text(comp_status, metrics)`, `get_sidebar_viz_text(view_name)`
- **main_views**: `build_files_view_content(comp_status, code_blueprint, project_root)`, `build_timeline_view_content(events)`

Diagram view stays in app: it calls `render_diagram(spec, config, selected_node_id)` from `view/diagram/`.
