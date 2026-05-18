"""Niu scooter road widget for GeekMagic displays.

Visualizes scooter battery as a road/path — the scooter icon rides
along the road bar at the current battery percentage. Big battery
number top-right, lock status bottom-right.
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
from .components import Component

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


def _battery_color(pct: float) -> Color:
    """Color based on battery level."""
    if pct > 50:
        return THEME_SUCCESS
    if pct > 20:
        return THEME_WARNING
    return THEME_ERROR


class _NiuRoadCanvas(Component):
    """Custom drawing: road bar with scooter icon riding along it."""

    def __init__(
        self,
        battery_pct: float,
        is_locked: bool,
        label: str,
    ) -> None:
        self.battery_pct = battery_pct
        self.is_locked = is_locked
        self.label = label

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        pct = max(0.0, min(100.0, self.battery_pct))
        bar_color = resolve_theme_color(_battery_color(pct), ctx.theme)
        track_color = resolve_theme_color(THEME_MUTED, ctx.theme)
        text_primary = resolve_theme_color(THEME_TEXT_PRIMARY, ctx.theme)
        text_secondary = resolve_theme_color(THEME_TEXT_SECONDARY, ctx.theme)

        padding = max(8, int(width * 0.06))

        # Label "NIU" top-left
        label_font = ctx.get_font("tiny", bold=True)
        ctx.draw_text(
            self.label.upper(),
            (x + padding, y + padding + 6),
            label_font,
            text_secondary,
            "lm",
        )

        # Big battery percentage top-right
        pct_font = ctx.get_font("xlarge", bold=True)
        pct_str = f"{pct:.0f}%"
        ctx.draw_text(
            pct_str,
            (x + width - padding, y + padding + int(height * 0.12)),
            pct_font,
            text_primary,
            "rm",
        )

        # Road bar — centered vertically, spans most of the width
        road_y = y + int(height * 0.55)
        road_h = max(10, int(height * 0.09))
        road_x1 = x + padding
        road_x2 = x + width - padding
        road_w = road_x2 - road_x1
        road_radius = road_h // 2

        # Track (full road)
        ctx.draw_rounded_rect(
            (road_x1, road_y, road_x2, road_y + road_h),
            radius=road_radius,
            fill=track_color,
        )

        # Filled portion (battery level)
        fill_w = int(road_w * pct / 100)
        if fill_w > 0:
            ctx.draw_rounded_rect(
                (road_x1, road_y, road_x1 + fill_w, road_y + road_h),
                radius=road_radius,
                fill=bar_color,
            )

        # Scooter icon positioned along the road
        icon_size = max(18, int(height * 0.16))
        scooter_x = road_x1 + fill_w
        scooter_y = road_y - icon_size - 4
        ctx.draw_icon("moped", (scooter_x - icon_size // 2, scooter_y), icon_size, bar_color)

        # Road dashes for visual texture
        dash_y = road_y + road_h // 2
        dash_color = resolve_theme_color(THEME_TEXT_SECONDARY, ctx.theme)
        for dx in range(road_x1 + 12, road_x2 - 6, 16):
            # Only draw dashes on the unfilled part
            if dx > road_x1 + fill_w + 4:
                ctx.draw.line(
                    [(dx, dash_y), (dx + 6, dash_y)],
                    fill=(*dash_color, 80) if len(dash_color) == 3 else dash_color,
                    width=1,
                )

        # Lock status bottom-right
        lock_icon = "lock" if self.is_locked else "lock-open-variant"
        lock_color = resolve_theme_color(THEME_SUCCESS if self.is_locked else THEME_WARNING, ctx.theme)
        lock_size = max(14, int(height * 0.10))
        lock_x = x + width - padding - lock_size
        lock_y = y + height - padding - lock_size
        ctx.draw_icon(lock_icon, (lock_x, lock_y), lock_size, lock_color)

        # "Locked" / "Unlocked" text next to lock
        lock_font = ctx.get_font("tiny", bold=False)
        lock_text = "Locked" if self.is_locked else "Unlocked"
        ctx.draw_text(
            lock_text,
            (lock_x - 4, lock_y + lock_size // 2),
            lock_font,
            lock_color,
            "rm",
        )


class NiuRoadWidget(Widget):
    """Niu scooter battery as a road — icon rides along the bar."""

    WIDGET_TYPE: ClassVar[str] = "niu_road"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Niu Scooter Road",
        "needs_entity": True,
        "entity_domains": ["sensor"],
        "options": [
            {
                "key": "lock_entity",
                "type": "entity",
                "label": "Lock Status Entity",
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        super().__init__(config)
        self.lock_entity_id = config.options.get("lock_entity")

    def get_entities(self) -> list[str]:
        entities = []
        if self.config.entity_id:
            entities.append(self.config.entity_id)
        if self.lock_entity_id:
            entities.append(self.lock_entity_id)
        return entities

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        battery = 0.0
        if state.entity:
            battery = state.entity.numeric(default=0.0)

        is_locked = True
        if self.lock_entity_id:
            lock_entity = state.get_entity(self.lock_entity_id)
            if lock_entity:
                is_locked = lock_entity.state.lower() in ("on", "true", "locked", "1")

        label = self.label_for(state.entity, fallback="NIU")

        return _NiuRoadCanvas(
            battery_pct=battery,
            is_locked=is_locked,
            label=label,
        )
