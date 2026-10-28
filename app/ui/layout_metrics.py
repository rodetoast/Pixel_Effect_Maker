"""Shared editor layout metrics for the Resource and Effect workspaces."""

HIERARCHY_LABEL_WIDTH = 220
COMPACT_TOOL_BUTTON_SIZE = 30

RESOURCE_BROWSER_MIN_WIDTH = 185
RESOURCE_BROWSER_DEFAULT_WIDTH = 205
RESOURCE_INSPECTOR_MIN_WIDTH = 300
RESOURCE_INSPECTOR_DEFAULT_WIDTH = 320

EFFECT_LIBRARY_MIN_WIDTH = 280
EFFECT_LIBRARY_DEFAULT_WIDTH = 280
EFFECT_INSPECTOR_MIN_WIDTH = 320
EFFECT_INSPECTOR_DEFAULT_WIDTH = 340

RESOURCE_TIMELINE_MIN_HEIGHT = 150
RESOURCE_TIMELINE_DEFAULT_HEIGHT = 235
EFFECT_TIMELINE_MIN_HEIGHT = 190
EFFECT_TIMELINE_MAX_HEIGHT = 360

# Inspector roles extend the existing source of layout truth. Heights are
# minimums, not fixed sizes: components still follow the current font metrics.
SPACING_XS = 3
SPACING_SM = 5
SPACING_MD = 8
SPACING_LG = 12
INSPECTOR_SECTION_MARGIN = 7
INSPECTOR_SECTION_SPACING = SPACING_SM
INSPECTOR_ROW_SPACING = 4
CONTROL_HEIGHT_INLINE = 28
CONTROL_HEIGHT_TOOL = COMPACT_TOOL_BUTTON_SIZE
CONTROL_HEIGHT_PRIMARY = 36
SECTION_HEADER_HEIGHT = CONTROL_HEIGHT_TOOL


def inspector_color(role, palette):
    """Resolve semantic colors from the active palette, including disabled text.

    No swatch/data color is passed through this resolver. Info/error messages
    also carry text and badges, so theme colors are not the only signal.
    """
    from PySide6.QtGui import QPalette

    roles = {
        "text_primary": QPalette.ColorRole.Text,
        "text_secondary": QPalette.ColorRole.WindowText,
        "text_muted": QPalette.ColorRole.PlaceholderText,
        "state_info": QPalette.ColorRole.Link,
        "state_warning": QPalette.ColorRole.Text,
        "state_error": QPalette.ColorRole.LinkVisited,
        "state_danger": QPalette.ColorRole.LinkVisited,
        "focus": QPalette.ColorRole.Highlight,
        "border": QPalette.ColorRole.Mid,
        "disabled": QPalette.ColorRole.Text,
    }
    group = QPalette.ColorGroup.Disabled if role == "disabled" else QPalette.ColorGroup.Active
    return palette.color(group, roles[role])
