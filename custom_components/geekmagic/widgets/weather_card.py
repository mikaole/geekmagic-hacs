"""Beautiful weather card widget for GeekMagic displays.

Clean weather display with large rounded temperatures (no decimals),
prominent condition icon, and a tidy 3-day forecast row.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from .base import Widget, WidgetConfig
from .colors import (
    THEME_INFO,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
)
from .components import Column, Component, Icon, Row, Text
from .weather import WEATHER_ICONS, WEATHER_ROLES, _parse_forecast_day_name

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .state import WidgetState


class _WeatherCardDisplay(Component):
    """Renders the beautiful weather card."""

    def __init__(
        self,
        temperature: Any,
        humidity: Any,
        condition: str,
        forecast: list[dict],
        forecast_days: int,
    ) -> None:
        self.temperature = temperature
        self.humidity = humidity
        self.condition = condition
        self.forecast = forecast
        self.forecast_days = forecast_days

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        icon_name = WEATHER_ICONS.get(self.condition, "weather-sunny")
        icon_tint = WEATHER_ROLES.get(self.condition, THEME_TEXT_PRIMARY)

        padding = max(6, int(width * 0.05))

        # Round temperature to integer — no decimals
        try:
            temp_int = int(round(float(self.temperature)))
            temp_str = f"{temp_int}°"
        except (ValueError, TypeError):
            temp_str = "--°"

        # Condition text, clean
        cond_text = self.condition.replace("-", " ").replace("_", " ").title()

        icon_size = max(32, int(height * 0.25))

        # Hero block: icon + temp + condition
        hero = Column(
            children=[
                Icon(icon_name, size=icon_size, color=icon_tint),
                Text(temp_str, font="huge", bold=True, color=THEME_TEXT_PRIMARY),
                Text(cond_text, font="small", color=THEME_TEXT_SECONDARY),
            ],
            gap=max(2, int(height * 0.015)),
            align="center",
            justify="start",
            padding=padding,
        )

        # Forecast row
        forecast_component = None
        forecast_items = self.forecast[: self.forecast_days]
        if forecast_items:
            forecast_icon_size = max(16, int(height * 0.12))
            cols = []
            for i, day in enumerate(forecast_items):
                day_cond = day.get("condition", "sunny")
                day_icon = WEATHER_ICONS.get(day_cond, "weather-sunny")
                day_tint = WEATHER_ROLES.get(day_cond, THEME_TEXT_PRIMARY)
                day_name = _parse_forecast_day_name(day.get("datetime", ""), f"D{i + 1}")

                # Integer temps — no decimals
                try:
                    day_hi = int(round(float(day.get("temperature", 0))))
                except (ValueError, TypeError):
                    day_hi = 0
                day_lo = day.get("templow")
                if day_lo is not None:
                    try:
                        day_lo_int = int(round(float(day_lo)))
                        t_str = f"{day_hi}°/{day_lo_int}°"
                    except (ValueError, TypeError):
                        t_str = f"{day_hi}°"
                else:
                    t_str = f"{day_hi}°"

                cols.append(
                    Column(
                        children=[
                            Text(day_name.upper(), font="small", color=THEME_TEXT_SECONDARY),
                            Icon(day_icon, size=forecast_icon_size, color=day_tint),
                            Text(t_str, font="small", bold=True, color=THEME_TEXT_PRIMARY),
                        ],
                        gap=max(1, int(height * 0.015)),
                        align="center",
                        justify="center",
                    )
                )

            forecast_component = Row(
                children=cols,
                gap=0,
                align="center",
                justify="space-around",
                padding=padding,
            )

        # Layout
        children: list[Component] = [hero]
        if forecast_component:
            children.append(forecast_component)

        Column(
            children=children,
            gap=max(2, int(height * 0.03)),
            align="stretch",
            justify="space-evenly",
        ).render(ctx, x, y, width, height)


class WeatherCardWidget(Widget):
    """Beautiful weather — clean integers, large icon, tidy forecast."""

    WIDGET_TYPE: ClassVar[str] = "weather_card"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Weather Card",
        "needs_entity": True,
        "entity_domains": ["weather"],
        "options": [
            {"key": "show_forecast", "type": "boolean", "label": "Show Forecast", "default": True},
            {
                "key": "forecast_days",
                "type": "number",
                "label": "Forecast Days",
                "default": 3,
                "min": 1,
                "max": 5,
            },
        ],
    }

    def __init__(self, config: WidgetConfig) -> None:
        super().__init__(config)
        self.show_forecast = config.options.get("show_forecast", True)
        self.forecast_days = config.options.get("forecast_days", 3)

    def render(self, ctx: RenderContext, state: WidgetState) -> Component:
        entity = state.entity
        if entity is None:
            return Column(
                children=[Text("No Weather", font="small", color=THEME_TEXT_SECONDARY)],
                align="center",
                justify="center",
            )

        return _WeatherCardDisplay(
            temperature=entity.get("temperature", "--"),
            humidity=entity.get("humidity", "--"),
            condition=entity.state,
            forecast=state.forecast if self.show_forecast else [],
            forecast_days=self.forecast_days,
        )
