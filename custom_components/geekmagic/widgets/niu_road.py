"""Niu scooter road widget for GeekMagic displays.

Visualizes scooter battery as an S-curve road with the scooter icon
riding along the path. Flag at the destination (100%), battery % and
range in km shown prominently, lock status in the corner.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, ClassVar

from .base import Widget, WidgetConfig
from .colors import (
    THEME_ERROR,
    THEME_MUTED,
    THEME_SUCCESS,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    THEME_TEXT_TERTIARY,
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


def _bezier_point(
    t: float,
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
) -> tuple[float, float]:
    """Evaluate cubic bezier at parameter t (0..1)."""
    u = 1 - t
    x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
    y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
    return (x, y)


def _build_s_curve(
    x1: float, y_center: float, x2: float, amplitude: float, steps: int = 60
) -> list[tuple[int, int]]:
    """Build an S-curve path from (x1, y_center) to (x2, y_center).

    Two cubic bezier segments form the S shape.
    """
    mid_x = (x1 + x2) / 2
    # First half: curves down
    p0 = (x1, y_center)
    p1 = (x1 + (mid_x - x1) * 0.5, y_center + amplitude)
    p2 = (mid_x - (mid_x - x1) * 0.3, y_center + amplitude)
    p3 = (mid_x, y_center)
    # Second half: curves up
    q0 = (mid_x, y_center)
    q1 = (mid_x + (x2 - mid_x) * 0.3, y_center - amplitude)
    q2 = (x2 - (x2 - mid_x) * 0.5, y_center - amplitude)
    q3 = (x2, y_center)

    half = steps // 2
    points: list[tuple[int, int]] = []
    for i in range(half + 1):
        t = i / half
        bx, by = _bezier_point(t, p0, p1, p2, p3)
        points.append((int(bx), int(by)))
    for i in range(1, half + 1):
        t = i / half
        bx, by = _bezier_point(t, q0, q1, q2, q3)
        points.append((int(bx), int(by)))
    return points


class _NiuRoadCanvas(Component):
    """Custom drawing: S-curve road with scooter + flag."""

    def __init__(
        self,
        battery_pct: float,
        range_km: float | None,
        is_locked: bool,
    ) -> None:
        self.battery_pct = battery_pct
        self.range_km = range_km
        self.is_locked = is_locked

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        pct = max(0.0, min(100.0, self.battery_pct))
        bar_color = resolve_theme_color(_battery_color(pct), ctx.theme)
        track_color = resolve_theme_color(THEME_MUTED, ctx.theme)
        text_primary = resolve_theme_color(THEME_TEXT_PRIMARY, ctx.theme)
        text_secondary = resolve_theme_color(THEME_TEXT_SECONDARY, ctx.theme)
        text_tertiary = resolve_theme_color(THEME_TEXT_TERTIARY, ctx.theme)

        padding = max(8, int(width * 0.06))

        # --- Top section: battery % (left) + range km (right) ---
        pct_font = ctx.get_font("xlarge", bold=True)
        pct_str = f"{pct:.0f}%"
        ctx.draw_text(pct_str, (x + padding, y + padding + 10), pct_font, text_primary, "lm")

        if self.range_km is not None:
            range_font = ctx.get_font("small", bold=False)
            range_str = f"{self.range_km:.0f} km"
            ctx.draw_text(
                range_str,
                (x + width - padding, y + padding + 10),
                range_font,
                text_secondary,
                "rm",
            )

        # --- S-curve road ---
        road_y_center = y + int(height * 0.55)
        amplitude = int(height * 0.12)
        road_x1 = x + padding + 4
        road_x2 = x + width - padding - 4
        path = _build_s_curve(road_x1, road_y_center, road_x2, amplitude, steps=60)

        # Draw track (full S-curve, thick muted line)
        road_width = max(6, int(height * 0.04))
        if len(path) >= 2:
            # Track
            for i in range(len(path) - 1):
                ctx.draw_line(
                    [path[i], path[i + 1]],
                    fill=track_color,
                    width=road_width,
                )

            # Filled portion (battery level) — draw the first pct% of the path in color
            fill_count = max(1, int(len(path) * pct / 100))
            for i in range(min(fill_count, len(path) - 1)):
                ctx.draw_line(
                    [path[i], path[i + 1]],
                    fill=bar_color,
                    width=road_width,
                )

            # Scooter icon at the current position along the S-curve
            scooter_idx = min(fill_count, len(path) - 1)
            sx, sy = path[scooter_idx]
            icon_size = max(18, int(height * 0.14))
            ctx.draw_icon("moped", (sx - icon_size // 2, sy - icon_size - 2), icon_size, bar_color)

            # Flag at the end of the road (destination)
            ex, ey = path[-1]
            flag_size = max(14, int(height * 0.11))
            ctx.draw_icon(
                "flag-checkered", (ex - flag_size // 2, ey - flag_size - 2), flag_size, text_tertiary
            )

        # --- Lock status bottom-right ---
        lock_icon = "lock" if self.is_locked else "lock-open-variant"
        lock_color = resolve_theme_color(THEME_SUCCESS if self.is_locked else THEME_WARNING, ctx.theme)
        lock_size = max(12, int(height * 0.09))
        lock_x = x + width - padding - lock_size
        lock_y = y + height - padding - lock_size
        ctx.draw_icon(lock_icon, (lock_x, lock_y), lock_size, lock_color)


class NiuRoadWidget(Widget):
    """Niu scooter — S-curve road with flag, battery % + range km."""

    WIDGET_TYPE: ClassVar[str] = "niu_road"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Niu Scooter Road",
        "needs_entity": True,
        "entity_domains": ["sensor"],
        "options": [
            {
                "key": "range_entity",
                "type": "entity",
                "label": "Range (km) Entity",
            },
            {
                "key": "lock_entity",
                "type": "entity",
                "label": "Lock Status Entity",
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        super().__init__(config)
        self.range_entity_id = config.options.get("range_entity")
        self.lock_entity_id = config.options.get("lock_entity")

    def get_entities(self) -> list[str]:
        entities = []
        if self.config.entity_id:
            entities.append(self.config.entity_id)
        if self.range_entity_id:
            entities.append(self.range_entity_id)
        if self.lock_entity_id:
            entities.append(self.lock_entity_id)
        return entities

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        battery = 0.0
        if state.entity:
            battery = state.entity.numeric(default=0.0)

        range_km: float | None = None
        if self.range_entity_id:
            r_entity = state.get_entity(self.range_entity_id)
            if r_entity:
                range_km = r_entity.numeric(default=0.0)

        is_locked = True
        if self.lock_entity_id:
            lock_entity = state.get_entity(self.lock_entity_id)
            if lock_entity:
                is_locked = lock_entity.state.lower() in ("on", "true", "locked", "1")

        return _NiuRoadCanvas(
            battery_pct=battery,
            range_km=range_km,
            is_locked=is_locked,
        )
