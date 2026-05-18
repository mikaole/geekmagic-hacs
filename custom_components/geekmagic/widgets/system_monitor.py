"""System monitor widget for GeekMagic displays.

Displays server health metrics (CPU, RAM, disk, temperature) pulled
from the Glances REST API. Renders compact horizontal bars with
labels and percentage values.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from .base import Widget, WidgetConfig
from .colors import (
    THEME_ERROR,
    THEME_INFO,
    THEME_MUTED,
    THEME_PRIMARY,
    THEME_SUCCESS,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    THEME_WARNING,
)
from .components import Bar, Column, Component, Row, Text

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState

_LOGGER = logging.getLogger(__name__)

# Default Glances API base URL
_DEFAULT_GLANCES_URL = "http://192.168.2.110:61208"


def _percent_color(pct: float) -> tuple[int, int, int]:
    """Return a theme-aware color sentinel based on usage percentage."""
    if pct >= 90:
        return THEME_ERROR
    if pct >= 70:
        return THEME_WARNING
    if pct >= 50:
        return THEME_INFO
    return THEME_SUCCESS


class _SystemBars(Component):
    """Renders CPU/RAM/disk/temp as labeled progress bars."""

    def __init__(self, metrics: dict[str, float]) -> None:
        self.metrics = metrics

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        items = list(self.metrics.items())
        if not items:
            Text("No data", font="small", color=THEME_MUTED).render(ctx, x, y, width, height)
            return

        padding = max(4, int(min(width, height) * 0.05))
        inner_w = width - 2 * padding
        inner_h = height - 2 * padding
        n = len(items)
        gap = max(3, int(inner_h * 0.04))
        row_h = max(12, (inner_h - gap * (n - 1)) // n)
        label_w = max(30, int(inner_w * 0.22))
        value_w = max(28, int(inner_w * 0.18))
        bar_w = inner_w - label_w - value_w - 2 * gap

        label_font = ctx.get_font("tiny", bold=False)
        value_font = ctx.get_font("tiny", bold=True)

        cy = y + padding
        for label, pct in items:
            # Label (left)
            ctx.draw_text(
                label.upper(),
                (x + padding, cy + row_h // 2),
                label_font,
                resolve_color(THEME_TEXT_SECONDARY, ctx),
                "lm",
            )
            # Bar (middle)
            bar_x = x + padding + label_w + gap
            bar_y = cy + max(0, (row_h - max(6, int(row_h * 0.45))) // 2)
            bar_h = max(6, int(row_h * 0.45))
            clamped = max(0.0, min(100.0, pct))
            Bar(percent=clamped, color=_percent_color(clamped), height=bar_h).render(
                ctx, bar_x, bar_y, bar_w, bar_h
            )
            # Value (right)
            val_str = f"{pct:.0f}%" if label != "TEMP" else f"{pct:.0f}°"
            ctx.draw_text(
                val_str,
                (x + padding + label_w + gap + bar_w + gap, cy + row_h // 2),
                value_font,
                resolve_color(THEME_TEXT_PRIMARY, ctx),
                "lm",
            )
            cy += row_h + gap


def resolve_color(color: tuple[int, int, int], ctx: RenderContext) -> tuple[int, int, int]:
    """Resolve theme color sentinel via the render context."""
    from .colors import resolve_theme_color

    return resolve_theme_color(color, ctx.theme)


class SystemMonitorWidget(Widget):
    """Widget that displays server health from the Glances REST API.

    Shows CPU, RAM, disk usage, and temperature as colored progress bars.
    Fetches data from the Glances API at the configured URL.
    """

    WIDGET_TYPE: ClassVar[str] = "system_monitor"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "System Monitor",
        "needs_entity": False,
        "options": [
            {
                "key": "glances_url",
                "type": "text",
                "label": "Glances URL",
                "default": _DEFAULT_GLANCES_URL,
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the system monitor widget."""
        super().__init__(config)
        self.glances_url = config.options.get("glances_url", _DEFAULT_GLANCES_URL)
        # Cached metrics from last successful fetch
        self._cached_metrics: dict[str, float] = {}

    def get_entities(self) -> list[str]:
        """System monitor doesn't depend on HA entities."""
        return []

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        """Render the system monitor bars.

        Note: The widget fetches data from Glances synchronously during
        rendering. In a future version this could be moved to the
        coordinator's async update cycle.
        """
        metrics = self._fetch_metrics()
        return _SystemBars(metrics)

    def _fetch_metrics(self) -> dict[str, float]:
        """Fetch system metrics from Glances API.

        Returns cached data on failure to keep the display populated.
        """
        try:
            import httpx  # noqa: PLC0415

            base = self.glances_url.rstrip("/")
            metrics: dict[str, float] = {}

            # Short timeout (2s) to avoid blocking the HA render thread.
            # Each request is wrapped individually so partial data still renders.
            with httpx.Client(timeout=2.0) as client:
                try:
                    resp = client.get(f"{base}/api/4/cpu")
                    if resp.status_code == 200:
                        metrics["CPU"] = resp.json().get("total", 0.0)
                except Exception:
                    pass

                try:
                    resp = client.get(f"{base}/api/4/mem")
                    if resp.status_code == 200:
                        metrics["RAM"] = resp.json().get("percent", 0.0)
                except Exception:
                    pass

                try:
                    resp = client.get(f"{base}/api/4/fs")
                    if resp.status_code == 200:
                        fs_list = resp.json()
                        if fs_list:
                            root = next(
                                (f for f in fs_list if f.get("mnt_point") == "/"),
                                fs_list[0],
                            )
                            metrics["DISK"] = root.get("percent", 0.0)
                except Exception:
                    pass

                try:
                    resp = client.get(f"{base}/api/4/sensors")
                    if resp.status_code == 200:
                        for s in resp.json():
                            if s.get("type") == "temperature_core":
                                metrics["TEMP"] = s.get("value", 0.0)
                                break
                except Exception:
                    pass

            if metrics:
                self._cached_metrics = metrics
            return self._cached_metrics

        except Exception:
            _LOGGER.debug("Failed to connect to Glances, using cached data")
            return self._cached_metrics
