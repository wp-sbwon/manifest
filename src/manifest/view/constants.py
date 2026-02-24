"""
View UI constants: default labels, colors, and layout numbers.

Use these instead of hardcoding strings/hex in app.py and inspector so they can
be changed in one place. Diagram colors (entity, child, status, selected) live
in diagram_config.json; inspector accent and rule length are here.
"""

# Root/diagram defaults when design has no root entity or title
DEFAULT_ROOT_LABEL = "System Core"
DEFAULT_ROOT_DESC = "Project root."
DEFAULT_PROJECT_LABEL = "Project"

# Inspector: section title and rule color; rule length (characters)
INSPECTOR_ACCENT = "#58a6ff"
INSPECTOR_RULE_LENGTH = 44

# Default diagram title when spec/config have no title
DEFAULT_DIAGRAM_TITLE = "ARCHITECTURE FLOW"
