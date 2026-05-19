"""Pixel art clock widget for GeekMagic displays.

Displays the current time as large blocky pixel-art digits on a
true-black background with a retro aesthetic. Each digit is drawn
as filled rectangles on a 4x7 grid, giving a chunky CRT look.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar
from zoneinfo import ZoneInfo

from .base import Widget, WidgetConfig
from .colors import (
    THEME_MUTED,
    THEME_PRIMARY,
    THEME_SUCCESS,
    THEME_TEXT_PRIMARY,
    THEME_WARNING,
    Color,
    resolve_theme_color,
)
from .components import Component

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState

# Each digit is a 4-wide x 7-tall bitmap (1 = filled, 0 = empty).
_DIGITS: dict[str, list[list[int]]] = {
    "0": [
        [1, 1, 1, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 1, 1, 1],
    ],
    "1": [
        [0, 0, 1, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 0],
        [0, 1, 1, 1],
    ],
    "2": [
        [1, 1, 1, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [1, 1, 1, 1],
        [1, 0, 0, 0],
        [1, 0, 0, 0],
        [1, 1, 1, 1],
    ],
    "3": [
        [1, 1, 1, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [1, 1, 1, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [1, 1, 1, 1],
    ],
    "4": [
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 1, 1, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
    ],
    "5": [
        [1, 1, 1, 1],
        [1, 0, 0, 0],
        [1, 0, 0, 0],
        [1, 1, 1, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [1, 1, 1, 1],
    ],
    "6": [
        [1, 1, 1, 1],
        [1, 0, 0, 0],
        [1, 0, 0, 0],
        [1, 1, 1, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 1, 1, 1],
    ],
    "7": [
        [1, 1, 1, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [0, 0, 1, 0],
        [0, 0, 1, 0],
        [0, 1, 0, 0],
        [0, 1, 0, 0],
    ],
    "8": [
        [1, 1, 1, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 1, 1, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 1, 1, 1],
    ],
    "9": [
        [1, 1, 1, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 1, 1, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [1, 1, 1, 1],
    ],
    ":": [
        [0, 0, 0, 0],
        [0, 1, 1, 0],
        [0, 1, 1, 0],
        [0, 0, 0, 0],
        [0, 1, 1, 0],
        [0, 1, 1, 0],
        [0, 0, 0, 0],
    ],
}


class _PixelClockCanvas(Component):
    """Custom component that draws pixel-art digits directly."""

    def __init__(
        self,
        time_str: str,
        date_str: str,
        digit_color: Color,
        date_color: Color,
    ) -> None:
        self.time_str = time_str
        self.date_str = date_str
        self.digit_color = digit_color
        self.date_color = date_color

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        digit_rgb = resolve_theme_color(self.digit_color, ctx.theme)
        date_rgb = resolve_theme_color(self.date_color, ctx.theme)

        chars = list(self.time_str)
        total_char_cols = len(chars) * 4 + (len(chars) - 1)  # 1-col gap between chars
        char_rows = 7
        has_date = bool(self.date_str)

        # When date is off, time fills 100% and centers vertically.
        # When date is on, time uses top 68%, date sits at 82%.
        if has_date:
            time_area_h = int(height * 0.68)
            date_area_y = y + int(height * 0.82)
        else:
            time_area_h = height
            date_area_y = 0  # unused

        # Minimal padding (4px) so digits fill more of the 240px canvas
        pad = 4
        px_w = max(1, (width - 2 * pad) // total_char_cols)
        px_h = max(1, (time_area_h - 2 * pad) // char_rows)
        px = min(px_w, px_h)

        # Center the time block
        block_w = total_char_cols * px
        block_h = char_rows * px
        start_x = x + (width - block_w) // 2
        start_y = y + (time_area_h - block_h) // 2

        # Draw each character
        cursor_x = start_x
        for ch in chars:
            bitmap = _DIGITS.get(ch)
            if bitmap is None:
                cursor_x += 2 * px
                continue
            for row_i, row_data in enumerate(bitmap):
                for col_i, val in enumerate(row_data):
                    if val:
                        rx = cursor_x + col_i * px
                        ry = start_y + row_i * px
                        ctx.draw_rect(
                            (rx, ry, rx + px - 1, ry + px - 1),
                            fill=digit_rgb,
                        )
            cursor_x += (4 + 1) * px  # 4 cols + 1 gap

        # Draw date text centered below (bold, large enough to read)
        if has_date:
            font = ctx.get_font("medium", bold=True)
            date_x = x + width // 2
            ctx.draw_text(self.date_str, (date_x, date_area_y), font, date_rgb, "mm")


class PixelClockWidget(Widget):
    """Widget that displays time as chunky pixel-art digits.

    Retro aesthetic with large blocky digits on true-black background.
    Supports green (terminal), amber (CRT), and white color schemes.
    """

    WIDGET_TYPE: ClassVar[str] = "pixel_clock"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Pixel Clock",
        "needs_entity": False,
        "options": [
            {
                "key": "color_scheme",
                "type": "select",
                "label": "Color Scheme",
                "options": ["green", "amber", "white"],
                "default": "green",
            },
            {"key": "show_date", "type": "boolean", "label": "Show Date", "default": True},
            {
                "key": "time_format",
                "type": "select",
                "label": "Time Format",
                "options": ["24h", "12h"],
                "default": "24h",
            },
            {
                "key": "timezone",
                "type": "timezone",
                "label": "Timezone",
            },
        ],
    }

    _COLOR_MAP: ClassVar[dict[str, Color]] = {
        "green": THEME_SUCCESS,
        "amber": THEME_WARNING,
        "white": THEME_TEXT_PRIMARY,
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the pixel clock widget."""
        super().__init__(config)
        self.color_scheme = config.options.get("color_scheme", "green")
        self.show_date = config.options.get("show_date", True)
        self.time_format = config.options.get("time_format", "24h")
        self.timezone = config.options.get("timezone")

    def get_entities(self) -> list[str]:
        """Pixel clock doesn't depend on entities."""
        return []

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the pixel art clock."""
        now = state.now or datetime.now(tz=UTC)
        # Apply timezone: use configured tz, fallback to Europe/Berlin
        try:
            tz = ZoneInfo(self.timezone) if self.timezone else ZoneInfo("Europe/Berlin")
            now = now.astimezone(tz)
        except Exception:
            pass

        fmt = "%I:%M" if self.time_format == "12h" else "%H:%M"
        time_str = now.strftime(fmt)
        date_str = now.strftime("%a %b %d") if self.show_date else ""

        digit_color = self._COLOR_MAP.get(self.color_scheme, THEME_SUCCESS)
        return _PixelClockCanvas(
            time_str=time_str,
            date_str=date_str,
            digit_color=self.config.color or digit_color,
            date_color=THEME_MUTED,
        )
