"""
View content builders: pure functions that take data and return strings or Rich renderables.

- inspector: Inspector panel (info hub node view, diff view, sections, deviation formatting).
- sidebar: Sidebar health and view-name text.
- main_views: Files view and Timeline view body text (Diagram remains in app; it uses render_diagram).
- header: Header strip (Planning/Differences, STATUS, TIME) and tab bar.
"""

from manifest.view.content.header_content import (
    build_header_strip_content,
    build_tab_bar_content,
)
from manifest.view.content.inspector_content import (
    format_for_display,
    inspection_section,
    deviation_box,
    deviates_at,
    deviations_from_view_entity,
    build_info_hub_node_content,
    build_info_hub_diff_view,
)
from manifest.view.content.sidebar_content import (
    get_sidebar_health_text,
    get_sidebar_viz_text,
)
from manifest.view.content.main_views import (
    build_files_view_content,
    build_timeline_view_content,
)

__all__ = [
    "build_header_strip_content",
    "build_tab_bar_content",
    "format_for_display",
    "inspection_section",
    "deviation_box",
    "deviates_at",
    "deviations_from_view_entity",
    "build_info_hub_node_content",
    "build_info_hub_diff_view",
    "get_sidebar_health_text",
    "get_sidebar_viz_text",
    "build_files_view_content",
    "build_timeline_view_content",
]
