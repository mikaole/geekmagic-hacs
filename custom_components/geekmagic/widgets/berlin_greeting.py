"""Berlin greeting widget for GeekMagic displays.

Time-aware German greeting with weather summary and date.
"Guten Morgen" / "Guten Tag" / "Guten Abend" / "Gute Nacht"
with current temperature, condition icon, and German-formatted date.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from .base import Widget, WidgetConfig
from .colors import (
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    Color,
)
from .components import Column, Component, Icon, Row, Text
from .weather import WEATHER_ICONS, WEATHER_ROLES

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState

# German month names
_MONTHS = [
    "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
    "Jul", "Aug", "Sep", "Okt", "Nov", "Dez",
]
_WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def _greeting(hour: int) -> str:
    """Return time-appropriate German greeting."""
    if hour < 5:
        return "Gute Nacht"
    if hour < 11:
        return "Guten Morgen"
    if hour < 18:
        return "Guten Tag"
    if hour < 22:
        return "Guten Abend"
    return "Gute Nacht"


def _german_date(dt: datetime) -> str:
    """Format date in German style: 'So, 18. Mai'."""
    weekday = _WEEKDAYS[dt.weekday()]
    month = _MONTHS[dt.month - 1]
    return f"{weekday}, {dt.day}. {month}"


class BerlinGreetingWidget(Widget):
    """Time-aware German greeting with weather and date."""

    WIDGET_TYPE: ClassVar[str] = "berlin_greeting"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Berlin Greeting",
        "needs_entity": True,
        "entity_domains": ["weather"],
        "options": [],
    }

    def __init__(self, config: WidgetConfig) -> None:
        super().__init__(config)

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        now = state.now or datetime.now(tz=UTC)
        greeting = _greeting(now.hour)
        date_str = _german_date(now)

        # Weather data
        temp_str = "--°"
        condition = "sunny"
        icon_name = "weather-sunny"
        icon_tint: Color = THEME_TEXT_SECONDARY

        if state.entity:
            try:
                temp_int = int(round(float(state.entity.get("temperature", 0))))
                temp_str = f"{temp_int}°"
            except (ValueError, TypeError):
                pass
            condition = state.entity.state or "sunny"
            icon_name = WEATHER_ICONS.get(condition, "weather-sunny")
            icon_tint = WEATHER_ROLES.get(condition, THEME_TEXT_SECONDARY)

        icon_size = max(20, int(ctx.height * 0.14))

        return Column(
            gap=max(4, int(ctx.height * 0.03)),
            padding=max(8, int(min(ctx.width, ctx.height) * 0.06)),
            align="center",
            justify="space-evenly",
            children=[
                # Greeting — large
                Text(greeting, font="large", bold=True, color=THEME_TEXT_PRIMARY, auto_fit=True),
                # Temp + icon row
                Row(
                    children=[
                        Icon(icon_name, size=icon_size, color=icon_tint),
                        Text(temp_str, font="xlarge", bold=True, color=THEME_TEXT_PRIMARY),
                    ],
                    gap=8,
                    justify="center",
                    align="center",
                ),
                # Date — German format
                Text(date_str, font="small", color=THEME_TEXT_SECONDARY),
            ],
        )
