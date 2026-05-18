"""Server stats widget for GeekMagic displays.

Homepage-style compact overview showing key service metrics at a glance:
Pi-hole queries/blocked, Uptime Kuma status, CPU/RAM from Glances.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from .base import Widget, WidgetConfig
from .colors import (
    THEME_ERROR,
    THEME_INFO,
    THEME_MUTED,
    THEME_SUCCESS,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    THEME_WARNING,
    Color,
    resolve_theme_color,
)
from .components import Column, Component, Row, Text

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import EntityState, WidgetState

_LOGGER = logging.getLogger(__name__)


def _format_count(value: float) -> str:
    """Format large numbers compactly: 12387 → '12.4k'."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return f"{value:.0f}"


class _StatsRows(Component):
    """Renders compact stat rows: icon-like dot + label + value."""

    def __init__(self, rows: list[tuple[str, str, Color]]) -> None:
        # Each row: (label, value_str, accent_color)
        self.rows = rows

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        if not self.rows:
            font = ctx.get_font("tiny", bold=False)
            muted = resolve_theme_color(THEME_MUTED, ctx.theme)
            ctx.draw_text("No data", (x + width // 2, y + height // 2), font, muted, "mm")
            return

        padding = max(6, int(width * 0.05))
        inner_w = width - 2 * padding
        inner_h = height - 2 * padding
        n = len(self.rows)
        gap = max(3, int(inner_h * 0.04))
        row_h = (inner_h - gap * (n - 1)) // n

        label_font = ctx.get_font("tiny", bold=False)
        value_font = ctx.get_font("small", bold=True)

        cy = y + padding
        for label, value_str, accent in self.rows:
            accent_rgb = resolve_theme_color(accent, ctx.theme)
            label_rgb = resolve_theme_color(THEME_TEXT_SECONDARY, ctx.theme)
            value_rgb = resolve_theme_color(THEME_TEXT_PRIMARY, ctx.theme)

            # Colored dot indicator (left)
            dot_r = max(3, int(row_h * 0.15))
            dot_cx = x + padding + dot_r
            dot_cy = cy + row_h // 2
            ctx.draw_ellipse(
                (dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r),
                fill=accent_rgb,
            )

            # Label (after dot)
            label_x = dot_cx + dot_r + 6
            ctx.draw_text(label, (label_x, dot_cy), label_font, label_rgb, "lm")

            # Value (right-aligned)
            value_x = x + width - padding
            ctx.draw_text(value_str, (value_x, dot_cy), value_font, value_rgb, "rm")

            cy += row_h + gap


class ServerStatsWidget(Widget):
    """Homepage-style server stats — compact key metrics at a glance."""

    WIDGET_TYPE: ClassVar[str] = "server_stats"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Server Stats",
        "needs_entity": False,
        "options": [
            {
                "key": "pihole_queries_entity",
                "type": "entity",
                "label": "Pi-hole Queries Entity",
            },
            {
                "key": "pihole_blocked_entity",
                "type": "entity",
                "label": "Pi-hole Blocked % Entity",
            },
            {
                "key": "uptime_entity",
                "type": "entity",
                "label": "Uptime Kuma Entity",
            },
            {
                "key": "glances_url",
                "type": "text",
                "label": "Glances URL",
                "default": "http://192.168.2.110:61208",
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        super().__init__(config)
        self.pihole_queries_id = config.options.get("pihole_queries_entity")
        self.pihole_blocked_id = config.options.get("pihole_blocked_entity")
        self.uptime_id = config.options.get("uptime_entity")
        self.glances_url = config.options.get("glances_url", "http://192.168.2.110:61208")
        self._cached_cpu: float | None = None
        self._cached_ram: float | None = None

    def get_entities(self) -> list[str]:
        entities = []
        if self.pihole_queries_id:
            entities.append(self.pihole_queries_id)
        if self.pihole_blocked_id:
            entities.append(self.pihole_blocked_id)
        if self.uptime_id:
            entities.append(self.uptime_id)
        return entities

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        rows: list[tuple[str, str, Color]] = []

        # Pi-hole queries
        if self.pihole_queries_id:
            q_ent: EntityState | None = state.get_entity(self.pihole_queries_id)
            if q_ent:
                queries = q_ent.numeric(default=0.0)
                rows.append(("DNS Queries", _format_count(queries), THEME_INFO))

        # Pi-hole blocked %
        if self.pihole_blocked_id:
            b_ent: EntityState | None = state.get_entity(self.pihole_blocked_id)
            if b_ent:
                blocked = b_ent.numeric(default=0.0)
                color = THEME_SUCCESS if blocked >= 20 else THEME_WARNING
                rows.append(("Blocked", f"{blocked:.0f}%", color))

        # Uptime Kuma
        if self.uptime_id:
            u_ent: EntityState | None = state.get_entity(self.uptime_id)
            if u_ent:
                status = u_ent.state
                if status.lower() in ("up", "on", "ok", "1"):
                    rows.append(("Services", "All Up", THEME_SUCCESS))
                else:
                    rows.append(("Services", status.title(), THEME_ERROR))

        # CPU + RAM from Glances (quick fetch)
        cpu, ram = self._fetch_glances()
        if cpu is not None:
            cpu_color = THEME_SUCCESS if cpu < 70 else (THEME_WARNING if cpu < 90 else THEME_ERROR)
            rows.append(("CPU", f"{cpu:.0f}%", cpu_color))
        if ram is not None:
            ram_color = THEME_SUCCESS if ram < 70 else (THEME_WARNING if ram < 90 else THEME_ERROR)
            rows.append(("RAM", f"{ram:.0f}%", ram_color))

        # Fallback if nothing configured
        if not rows:
            rows.append(("No entities", "Configure in settings", THEME_MUTED))

        # Caption + stat rows
        return Column(
            gap=4,
            padding=4,
            align="stretch",
            justify="space-evenly",
            children=[
                Row(
                    children=[Text("SERVER", font="tertiary", color=THEME_TEXT_SECONDARY, auto_fit=True)],
                    justify="center",
                    align="center",
                ),
                _StatsRows(rows),
            ],
        )

    def _fetch_glances(self) -> tuple[float | None, float | None]:
        """Quick fetch CPU + RAM from Glances. Returns cached on failure."""
        try:
            import httpx  # noqa: PLC0415

            base = self.glances_url.rstrip("/")
            with httpx.Client(timeout=2.0) as client:
                try:
                    resp = client.get(f"{base}/api/4/quicklook")
                    if resp.status_code == 200:
                        data = resp.json()
                        self._cached_cpu = data.get("cpu", 0.0)
                        self._cached_ram = data.get("mem", 0.0)
                except Exception:
                    pass
        except Exception:
            _LOGGER.debug("Failed to connect to Glances for server stats")
        return self._cached_cpu, self._cached_ram
