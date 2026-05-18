"""Pi-hole dashboard widget for GeekMagic displays.

Shows DNS blocking stats: blocked percentage as an arc gauge,
total queries and blocked count as compact text below.
"""

from __future__ import annotations

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
from .components import Arc, Column, Component, Row, Text

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import EntityState, WidgetState


def _format_count(value: float) -> str:
    """Format large numbers compactly: 12387 → '12.4k'."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return f"{value:.0f}"


def _blocked_color(pct: float) -> Color:
    """Color based on how effective the blocking is."""
    if pct >= 30:
        return THEME_SUCCESS
    if pct >= 10:
        return THEME_WARNING
    return THEME_ERROR


class PiholeDashboardWidget(Widget):
    """Pi-hole DNS shield — arc gauge with blocked % and query counts."""

    WIDGET_TYPE: ClassVar[str] = "pihole_dashboard"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Pi-hole Dashboard",
        "needs_entity": True,
        "entity_domains": ["sensor"],
        "options": [
            {
                "key": "queries_entity",
                "type": "entity",
                "label": "Queries Today Entity",
            },
            {
                "key": "blocked_entity",
                "type": "entity",
                "label": "Ads Blocked Today Entity",
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        super().__init__(config)
        self.queries_entity_id = config.options.get("queries_entity")
        self.blocked_entity_id = config.options.get("blocked_entity")

    def get_entities(self) -> list[str]:
        entities = []
        if self.config.entity_id:
            entities.append(self.config.entity_id)
        if self.queries_entity_id:
            entities.append(self.queries_entity_id)
        if self.blocked_entity_id:
            entities.append(self.blocked_entity_id)
        return entities

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        # Primary entity = ads_percentage_blocked_today
        pct = 0.0
        if state.entity:
            pct = state.entity.numeric(default=0.0)

        queries = 0.0
        blocked = 0.0

        if self.queries_entity_id:
            q_entity: EntityState | None = state.get_entity(self.queries_entity_id)
            if q_entity:
                queries = q_entity.numeric(default=0.0)

        if self.blocked_entity_id:
            b_entity: EntityState | None = state.get_entity(self.blocked_entity_id)
            if b_entity:
                blocked = b_entity.numeric(default=0.0)

        arc_color = _blocked_color(pct)
        queries_str = _format_count(queries)
        blocked_str = _format_count(blocked)

        from .components import Flex, Stack  # noqa: PLC0415

        # Build: caption → arc with hero inside → stats row
        return Column(
            gap=4,
            padding=6,
            align="stretch",
            justify="space-evenly",
            children=[
                Row(
                    children=[Text("PIHOLE", font="tertiary", color=THEME_TEXT_SECONDARY, auto_fit=True)],
                    justify="center",
                    align="center",
                ),
                Flex(
                    Stack(
                        children=[
                            Arc(percent=min(100.0, pct), color=arc_color),
                            Column(
                                align="center",
                                justify="center",
                                children=[
                                    Text(f"{pct:.0f}%", font="primary", bold=True, color=THEME_TEXT_PRIMARY, auto_fit=True),
                                    Text("blocked", font="tiny", color=THEME_MUTED),
                                ],
                            ),
                        ]
                    )
                ),
                Row(
                    children=[
                        Text(f"{queries_str} queries", font="tiny", color=THEME_TEXT_SECONDARY, auto_fit=True),
                        Text("·", font="tiny", color=THEME_MUTED),
                        Text(f"{blocked_str} blocked", font="tiny", color=THEME_TEXT_SECONDARY, auto_fit=True),
                    ],
                    gap=4,
                    justify="center",
                    align="center",
                ),
            ],
        )
