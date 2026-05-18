"""Word clock widget for GeekMagic displays.

Displays the current time as illuminated words on a letter grid,
e.g. "IT IS QUARTER PAST THREE". Active words are highlighted,
inactive letters are dimmed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from .base import Widget, WidgetConfig
from .colors import (
    THEME_MUTED,
    THEME_PRIMARY,
    THEME_TEXT_PRIMARY,
    THEME_WARNING,
    Color,
    resolve_theme_color,
)
from .components import Component

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState

# The letter grid — each row is 11 characters.
# Words are defined by (row, start_col, end_col) positions.
GRID = [
    "ITLISASAMPM",
    "ACQUARTERDC",
    "TWENTYFIVEX",
    "HALFBTENFTO",
    "PASTERUNINE",
    "ONESIXTHREE",
    "FOURFIVETWO",
    "EIGHTELEVEN",
    "SEVENTWELVE",
    "TENSEOCLOCK",
]

# Word positions: (row, col_start, col_end) — col_end is exclusive
_IT = (0, 0, 2)
_IS = (0, 3, 5)
_A = (0, 5, 6)
_AM = (0, 7, 9)
_PM = (0, 9, 11)
_QUARTER = (1, 2, 9)
_TWENTY = (2, 0, 6)
_FIVE_M = (2, 6, 10)
_HALF = (3, 0, 4)
_TEN_M = (3, 5, 8)
_TO = (3, 9, 11)
_PAST = (4, 0, 4)
_NINE = (4, 7, 11)
_ONE = (5, 0, 3)
_SIX = (5, 3, 6)
_THREE = (5, 6, 11)
_FOUR = (6, 0, 4)
_FIVE_H = (6, 4, 8)
_TWO = (6, 8, 11)
_EIGHT = (7, 0, 5)
_ELEVEN = (7, 5, 11)
_SEVEN = (8, 0, 5)
_TWELVE = (8, 5, 11)
_TEN_H = (9, 0, 3)
_OCLOCK = (9, 5, 11)

_HOURS = {
    1: _ONE, 2: _TWO, 3: _THREE, 4: _FOUR, 5: _FIVE_H, 6: _SIX,
    7: _SEVEN, 8: _EIGHT, 9: _NINE, 10: _TEN_H, 11: _ELEVEN, 12: _TWELVE,
}


def _active_words(hour: int, minute: int) -> list[tuple[int, int, int]]:
    """Return which grid words to illuminate for the given time."""
    words: list[tuple[int, int, int]] = [_IT, _IS]

    # Round to nearest 5 minutes
    m = (minute + 2) // 5 * 5
    # If rounding pushes to 60, advance the hour
    if m == 60:
        m = 0
        hour += 1

    h = hour % 12 or 12

    if m == 0:
        words.append(_HOURS[h])
        words.append(_OCLOCK)
    elif m == 5:
        words.extend([_FIVE_M, _PAST, _HOURS[h]])
    elif m == 10:
        words.extend([_TEN_M, _PAST, _HOURS[h]])
    elif m == 15:
        words.extend([_A, _QUARTER, _PAST, _HOURS[h]])
    elif m == 20:
        words.extend([_TWENTY, _PAST, _HOURS[h]])
    elif m == 25:
        words.extend([_TWENTY, _FIVE_M, _PAST, _HOURS[h]])
    elif m == 30:
        words.extend([_HALF, _PAST, _HOURS[h]])
    elif m == 35:
        next_h = (h % 12) + 1
        words.extend([_TWENTY, _FIVE_M, _TO, _HOURS[next_h]])
    elif m == 40:
        next_h = (h % 12) + 1
        words.extend([_TWENTY, _TO, _HOURS[next_h]])
    elif m == 45:
        next_h = (h % 12) + 1
        words.extend([_A, _QUARTER, _TO, _HOURS[next_h]])
    elif m == 50:
        next_h = (h % 12) + 1
        words.extend([_TEN_M, _TO, _HOURS[next_h]])
    elif m == 55:
        next_h = (h % 12) + 1
        words.extend([_FIVE_M, _TO, _HOURS[next_h]])

    return words


class _WordClockGrid(Component):
    """Custom component that renders the word clock letter grid."""

    def __init__(self, hour: int, minute: int, active_color: Color, dim_color: Color) -> None:
        self.hour = hour
        self.minute = minute
        self.active_color = active_color
        self.dim_color = dim_color

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        active = _active_words(self.hour, self.minute)
        # Build a set of (row, col) positions that are active
        active_positions: set[tuple[int, int]] = set()
        for row, col_start, col_end in active:
            for col in range(col_start, col_end):
                active_positions.add((row, col))

        rows = len(GRID)
        cols = len(GRID[0])
        padding = max(4, int(min(width, height) * 0.06))
        inner_w = width - 2 * padding
        inner_h = height - 2 * padding
        cell_w = inner_w / cols
        cell_h = inner_h / rows

        font_size = max(8, int(min(cell_w, cell_h) * 0.75))
        font = ctx.get_font("tiny", bold=True)

        active_rgb = resolve_theme_color(self.active_color, ctx.theme)
        dim_rgb = resolve_theme_color(self.dim_color, ctx.theme)

        for r, row_text in enumerate(GRID):
            for c, letter in enumerate(row_text):
                lx = x + padding + int(c * cell_w + cell_w / 2)
                ly = y + padding + int(r * cell_h + cell_h / 2)
                color = active_rgb if (r, c) in active_positions else dim_rgb
                ctx.draw_text(letter, (lx, ly), font, color, "mm")


class WordClockWidget(Widget):
    """Widget that displays time as illuminated words on a letter grid.

    The grid reads like a sentence: "IT IS QUARTER PAST THREE".
    Active words glow in the theme accent color, inactive letters are dimmed.
    """

    WIDGET_TYPE: ClassVar[str] = "word_clock"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Word Clock",
        "needs_entity": False,
        "options": [
            {
                "key": "color_scheme",
                "type": "select",
                "label": "Color Scheme",
                "options": ["white", "green", "amber"],
                "default": "white",
            },
            {
                "key": "timezone",
                "type": "timezone",
                "label": "Timezone",
            },
        ],
    }

    _COLOR_MAP: ClassVar[dict[str, Color]] = {
        "white": THEME_TEXT_PRIMARY,
        "green": THEME_PRIMARY,
        "amber": THEME_WARNING,
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the word clock widget."""
        super().__init__(config)
        self.color_scheme = config.options.get("color_scheme", "white")
        self.timezone = config.options.get("timezone")

    def get_entities(self) -> list[str]:
        """Word clock doesn't depend on entities."""
        return []

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the word clock grid."""
        now = state.now or datetime.now(tz=UTC)
        active_color = self._COLOR_MAP.get(self.color_scheme, THEME_TEXT_PRIMARY)
        return _WordClockGrid(
            hour=now.hour,
            minute=now.minute,
            active_color=self.config.color or active_color,
            dim_color=THEME_MUTED,
        )
