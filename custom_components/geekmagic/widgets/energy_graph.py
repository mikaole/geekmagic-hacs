"""Green energy graph widget for GeekMagic displays.

Sparkline chart of the green energy signal over time with color-coded
current value label (Grün/Gelb/Rot). Uses entity history for the graph.
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
)
from .components import Column, Component, Flex, Row, Sparkline, Text

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


def _signal_label(value: float) -> tuple[str, Color]:
    """Map numeric green energy value to label and color."""
    if value >= 2:
        return "Grün", THEME_SUCCESS
    if value >= 1:
        return "Gelb", THEME_WARNING
    return "Rot", THEME_ERROR


class EnergyGraphWidget(Widget):
    """Green energy sparkline — shows clean energy availability over time."""

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
            {"key": "fill", "type": "boolean", "label": "Fill Area", "default": True},
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
        self.fill = config.options.get("fill", True)

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        entity = state.entity
        current_value = 0.0
        if entity is not None:
            with contextlib.suppress(ValueError, TypeError):
                current_value = float(entity.state)

        label_text, label_color = _signal_label(current_value)

        # Build: caption → value → sparkline
        children: list[Component] = [
            Row(
                children=[
                    Text("GRÜNSTROM", font="tertiary", color=THEME_TEXT_SECONDARY, auto_fit=True),
                ],
                justify="center",
                align="center",
            ),
            Row(
                children=[
                    Text(label_text, font="large", bold=True, color=label_color, auto_fit=True),
                ],
                justify="center",
                align="center",
            ),
        ]

        # Sparkline from history
        if state.has_history():
            children.append(
                Flex(
                    Sparkline(
                        data=list(state.history),
                        color=THEME_SUCCESS,
                        fill=self.fill,
                    )
                )
            )
        else:
            children.append(
                Row(
                    children=[Text("No history", font="tiny", color=THEME_MUTED)],
                    justify="center",
                    align="center",
                ),
            )

        return Column(
            gap=4,
            padding=6,
            align="stretch",
            justify="space-evenly",
            children=children,
        )
