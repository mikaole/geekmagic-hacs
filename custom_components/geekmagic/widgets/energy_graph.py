"""Green energy graph widget for GeekMagic displays.

Colored timeline bar chart of renewable energy share (0-100%) over time.
Each bar is colored green (>60%), amber (30-60%), or red (<30%) based
on how much clean energy was available at that point.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, ClassVar

from .base import Widget, WidgetConfig
from .colors import (
    THEME_ERROR,
    THEME_MUTED,
    THEME_SUCCESS,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    THEME_WARNING,
    Color,
    resolve_theme_color,
)
from .components import Column, Component, Flex, Row, Text

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


def _pct_color(pct: float) -> Color:
    """Color for a renewable energy percentage value."""
    if pct >= 60:
        return THEME_SUCCESS
    if pct >= 30:
        return THEME_WARNING
    return THEME_ERROR


def _pct_label(pct: float) -> tuple[str, Color]:
    """Current status label and color."""
    if pct >= 60:
        return "Grün", THEME_SUCCESS
    if pct >= 30:
        return "Gelb", THEME_WARNING
    return "Rot", THEME_ERROR


class _EnergyTimeline(Component):
    """Colored vertical bars — each bar colored by renewable % at that time."""

    def __init__(self, data: list[float], current_pct: float) -> None:
        self.data = data
        self.current_pct = current_pct

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        if not self.data:
            font = ctx.get_font("tiny", bold=False)
            muted = resolve_theme_color(THEME_MUTED, ctx.theme)
            ctx.draw_text("No history data", (x + width // 2, y + height // 2), font, muted, "mm")
            return

        n = len(self.data)
        padding = max(4, int(width * 0.04))
        inner_w = width - 2 * padding
        inner_h = height - 4  # small margin top/bottom

        # Bar width and gap
        gap = 1
        bar_w = max(1, (inner_w - gap * (n - 1)) // n)

        # Find data range for scaling (0-100 for percentages)
        d_min = 0.0
        d_max = 100.0

        track_color = resolve_theme_color(THEME_MUTED, ctx.theme)

        for i, val in enumerate(self.data):
            bx = x + padding + i * (bar_w + gap)
            # Clamp value and compute bar height
            clamped = max(d_min, min(d_max, val))
            bar_h = max(1, int(inner_h * clamped / d_max))

            # Track (full height, very subtle)
            ctx.draw_rect(
                (bx, y + 2, bx + bar_w, y + 2 + inner_h),
                fill=track_color,
            )

            # Colored bar (height = value %)
            bar_color = resolve_theme_color(_pct_color(clamped), ctx.theme)
            bar_top = y + 2 + inner_h - bar_h
            ctx.draw_rect(
                (bx, bar_top, bx + bar_w, y + 2 + inner_h),
                fill=bar_color,
            )


class EnergyGraphWidget(Widget):
    """Green energy timeline — colored bars showing renewable availability."""

    WIDGET_TYPE: ClassVar[str] = "energy_graph"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Energy Graph",
        "needs_entity": True,
        "entity_domains": ["sensor"],
        "options": [
            {
                "key": "period",
                "type": "select",
                "label": "Period",
                "options": ["6 hours", "12 hours", "24 hours"],
                "default": "24 hours",
            },
        ],
    }

    PERIOD_TO_HOURS: ClassVar[dict[str, float]] = {
        "6 hours": 6,
        "12 hours": 12,
        "24 hours": 24,
    }

    def __init__(self, config: WidgetConfig) -> None:
        super().__init__(config)
        period = config.options.get("period", "24 hours")
        self.hours = self.PERIOD_TO_HOURS.get(period, 24) if isinstance(period, str) else 24

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        entity = state.entity
        current_value = 0.0
        if entity is not None:
            with contextlib.suppress(ValueError, TypeError):
                current_value = float(entity.state)

        label_text, label_color = _pct_label(current_value)

        return Column(
            gap=4,
            padding=6,
            align="stretch",
            justify="space-evenly",
            children=[
                Row(
                    children=[
                        Text("GRÜNSTROM", font="tertiary", color=THEME_TEXT_SECONDARY, auto_fit=True),
                    ],
                    justify="center",
                    align="center",
                ),
                Row(
                    children=[
                        Text(
                            f"{current_value:.0f}%",
                            font="large",
                            bold=True,
                            color=label_color,
                            auto_fit=True,
                        ),
                        Text(label_text, font="small", color=label_color),
                    ],
                    gap=8,
                    justify="center",
                    align="center",
                ),
                Flex(_EnergyTimeline(data=list(state.history), current_pct=current_value)),
            ],
        )
