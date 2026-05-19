"""Berlin greeting widget for GeekMagic displays.

Time-aware German greeting with weather summary, 3-day forecast, and date.
"Guten Morgen" / "Guten Tag" / "Guten Abend" / "Gute Nacht"
with current temperature, condition icon, forecast row, and German date.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar
from zoneinfo import ZoneInfo

from .base import Widget, WidgetConfig
from .colors import (
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    Color,
)
from .components import Column, Component, Icon, Row, Text
from .weather import WEATHER_ICONS, WEATHER_ROLES, _parse_forecast_day_name

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState

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
    """Time-aware German greeting with weather, 3-day forecast, and date."""

    WIDGET_TYPE: ClassVar[str] = "berlin_greeting"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Berlin Greeting",
        "needs_entity": True,
        "entity_domains": ["weather"],
        "options": [
            {
                "key": "forecast_days",
                "type": "number",
                "label": "Forecast Days",
                "default": 3,
                "min": 0,
                "max": 3,
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        super().__init__(config)
        self.forecast_days = config.options.get("forecast_days", 3)

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        now = state.now or datetime.now(tz=UTC)
        try:
            now = now.astimezone(ZoneInfo("Europe/Berlin"))
        except Exception:
            pass
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

        padding = max(6, int(min(ctx.width, ctx.height) * 0.05))
        icon_size = max(24, int(ctx.height * 0.18))

        children: list[Component] = [
            # Greeting — big and bold
            Text(greeting, font="xlarge", bold=True, color=THEME_TEXT_PRIMARY, auto_fit=True),
            # Temp + icon row — prominent
            Row(
                children=[
                    Icon(icon_name, size=icon_size, color=icon_tint),
                    Text(temp_str, font="huge", bold=True, color=THEME_TEXT_PRIMARY),
                ],
                gap=8,
                justify="center",
                align="center",
            ),
        ]

        # 3-day forecast row
        forecast_items = state.forecast[: self.forecast_days] if state.forecast else []
        if forecast_items:
            fc_icon_size = max(12, int(ctx.height * 0.09))
            cols: list[Component] = []
            for i, day in enumerate(forecast_items):
                day_cond = day.get("condition", "sunny")
                day_icon = WEATHER_ICONS.get(day_cond, "weather-sunny")
                day_tint = WEATHER_ROLES.get(day_cond, THEME_TEXT_PRIMARY)
                day_name = _parse_forecast_day_name(day.get("datetime", ""), f"D{i + 1}")
                try:
                    day_hi = int(round(float(day.get("temperature", 0))))
                except (ValueError, TypeError):
                    day_hi = 0
                day_lo = day.get("templow")
                if day_lo is not None:
                    try:
                        t_str = f"{day_hi}°/{int(round(float(day_lo)))}°"
                    except (ValueError, TypeError):
                        t_str = f"{day_hi}°"
                else:
                    t_str = f"{day_hi}°"
                cols.append(
                    Column(
                        children=[
                            Text(day_name.upper(), font="tiny", color=THEME_TEXT_SECONDARY),
                            Icon(day_icon, size=fc_icon_size, color=day_tint),
                            Text(t_str, font="tiny", bold=True, color=THEME_TEXT_PRIMARY),
                        ],
                        gap=1,
                        align="center",
                        justify="center",
                    )
                )
            children.append(
                Row(children=cols, gap=0, align="center", justify="space-around")
            )

        # Date — German format, bold
        children.append(
            Text(date_str, font="secondary", bold=True, color=THEME_TEXT_SECONDARY),
        )

        return Column(
            gap=max(3, int(ctx.height * 0.02)),
            padding=padding,
            align="center",
            justify="space-evenly",
            children=children,
        )
