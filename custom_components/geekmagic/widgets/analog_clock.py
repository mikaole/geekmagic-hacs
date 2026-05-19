"""Analog clock widget for GeekMagic displays.

Elegant minimalist analog clock face with thin hands, dot hour markers,
and subtle minute ticks. Designed to look refined on the Liquid Glass theme.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar
from zoneinfo import ZoneInfo

from .base import Widget, WidgetConfig
from .colors import (
    THEME_MUTED,
    THEME_PRIMARY,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    THEME_TEXT_TERTIARY,
    Color,
    resolve_theme_color,
)
from .components import Component

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


class _AnalogClockFace(Component):
    """Draws a minimalist analog clock face with Pillow."""

    def __init__(
        self,
        hour: int,
        minute: int,
        second: int,
        show_seconds: bool,
        show_date: bool,
        date_str: str,
        hand_color: Color,
        marker_color: Color,
        tick_color: Color,
        date_color: Color,
    ) -> None:
        self.hour = hour
        self.minute = minute
        self.second = second
        self.show_seconds = show_seconds
        self.show_date = show_date
        self.date_str = date_str
        self.hand_color = hand_color
        self.marker_color = marker_color
        self.tick_color = tick_color
        self.date_color = date_color

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        hand_rgb = resolve_theme_color(self.hand_color, ctx.theme)
        marker_rgb = resolve_theme_color(self.marker_color, ctx.theme)
        tick_rgb = resolve_theme_color(self.tick_color, ctx.theme)
        date_rgb = resolve_theme_color(self.date_color, ctx.theme)

        cx = x + width // 2
        cy = y + height // 2
        radius = min(width, height) // 2 - 8

        # Hour markers — 12 dots
        for i in range(12):
            angle = math.radians(i * 30 - 90)
            dot_r = 3 if i % 3 == 0 else 2  # Larger dots at 12/3/6/9
            mx = cx + int((radius - 8) * math.cos(angle))
            my = cy + int((radius - 8) * math.sin(angle))
            ctx.draw_ellipse(
                (mx - dot_r, my - dot_r, mx + dot_r, my + dot_r),
                fill=marker_rgb,
            )

        # Minute ticks — 60 fine ticks (skip where hour dots are)
        for i in range(60):
            if i % 5 == 0:
                continue
            angle = math.radians(i * 6 - 90)
            tx1 = cx + int((radius - 4) * math.cos(angle))
            ty1 = cy + int((radius - 4) * math.sin(angle))
            tx2 = cx + int((radius - 1) * math.cos(angle))
            ty2 = cy + int((radius - 1) * math.sin(angle))
            ctx.draw_line([(tx1, ty1), (tx2, ty2)], fill=tick_rgb, width=1)

        # Hour hand
        h_angle = math.radians(
            (self.hour % 12) * 30 + self.minute * 0.5 - 90
        )
        h_len = int(radius * 0.55)
        hx = cx + int(h_len * math.cos(h_angle))
        hy = cy + int(h_len * math.sin(h_angle))
        ctx.draw_line([(cx, cy), (hx, hy)], fill=hand_rgb, width=3)

        # Minute hand
        m_angle = math.radians(self.minute * 6 + self.second * 0.1 - 90)
        m_len = int(radius * 0.78)
        mx = cx + int(m_len * math.cos(m_angle))
        my = cy + int(m_len * math.sin(m_angle))
        ctx.draw_line([(cx, cy), (mx, my)], fill=hand_rgb, width=2)

        # Second hand (optional, thin)
        if self.show_seconds:
            s_angle = math.radians(self.second * 6 - 90)
            s_len = int(radius * 0.85)
            sx = cx + int(s_len * math.cos(s_angle))
            sy = cy + int(s_len * math.sin(s_angle))
            accent = resolve_theme_color(THEME_PRIMARY, ctx.theme)
            ctx.draw_line([(cx, cy), (sx, sy)], fill=accent, width=1)

        # Center dot
        ctx.draw_ellipse(
            (cx - 3, cy - 3, cx + 3, cy + 3),
            fill=hand_rgb,
        )

        # Date at 6 o'clock position
        if self.show_date and self.date_str:
            font = ctx.get_font("tiny", bold=False)
            date_y = cy + int(radius * 0.42)
            ctx.draw_text(self.date_str, (cx, date_y), font, date_rgb, "mm")


class AnalogClockWidget(Widget):
    """Minimalist analog clock face — thin hands, dot markers, optional date."""

    WIDGET_TYPE: ClassVar[str] = "analog_clock"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Analog Clock",
        "needs_entity": False,
        "options": [
            {"key": "show_seconds", "type": "boolean", "label": "Show Seconds", "default": False},
            {"key": "show_date", "type": "boolean", "label": "Show Date", "default": True},
            {
                "key": "timezone",
                "type": "timezone",
                "label": "Timezone",
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        super().__init__(config)
        self.show_seconds = config.options.get("show_seconds", False)
        self.show_date = config.options.get("show_date", True)
        self.timezone = config.options.get("timezone")

    def get_entities(self) -> list[str]:
        return []

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        now = state.now or datetime.now(tz=UTC)
        try:
            tz = ZoneInfo(self.timezone) if self.timezone else ZoneInfo("Europe/Berlin")
            now = now.astimezone(tz)
        except Exception:
            pass
        return _AnalogClockFace(
            hour=now.hour,
            minute=now.minute,
            second=now.second,
            show_seconds=self.show_seconds,
            show_date=self.show_date,
            date_str=now.strftime("%a %d"),
            hand_color=self.config.color or THEME_TEXT_PRIMARY,
            marker_color=THEME_TEXT_SECONDARY,
            tick_color=THEME_TEXT_TERTIARY,
            date_color=THEME_MUTED,
        )
