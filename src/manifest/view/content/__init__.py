"""
View content builders: pure functions that take data and return strings or Rich renderables.

- inspector: Inspector panel (info hub node view, diff view).
- sidebar: Sidebar health.
- main_views: Files view and Timeline view body text.
- header: Header strip (Planning/Differences, STATUS, TIME) and tab bar.
"""

from manifest.view.content.header_content import (
    build_header_strip_content,
    build_tab_bar_content,
)
from manifest.view.content.inspector_content import (
    build_info_hub_node_content,
    build_info_hub_diff_view,
)
from manifest.view.content.sidebar_content import (
    get_sidebar_health_text,
)
from manifest.view.content.main_views import (
    build_files_view_content,
    build_timeline_view_content,
)

__all__ = [
    "build_header_strip_content",
    "build_tab_bar_content",
    "build_info_hub_node_content",
    "build_info_hub_diff_view",
    "get_sidebar_health_text",
    "build_files_view_content",
    "build_timeline_view_content",
]
