"""Tests for Jinja2 template rendering in widget labels and helpers."""

from __future__ import annotations

import logging

import pytest

from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.clock import ClockWidget
from custom_components.geekmagic.widgets.entity import EntityWidget
from custom_components.geekmagic.widgets.helpers import (
    has_template_syntax,
    render_template,
    template_entity_ids,
)
from custom_components.geekmagic.widgets.state import EntityState


class TestHasTemplateSyntax:
    """Detection of Jinja2 syntax in label strings."""

    def test_plain_text(self):
        assert has_template_syntax("Temperature") is False

    def test_empty_string(self):
        assert has_template_syntax("") is False

    def test_none(self):
        assert has_template_syntax(None) is False

    def test_non_string(self):
        assert has_template_syntax(42) is False

    def test_expression(self):
        assert has_template_syntax("{{ states('sensor.x') }}") is True

    def test_statement(self):
        assert has_template_syntax("{% if x %}A{% endif %}") is True


class TestRenderTemplate:
    """Render template values against Home Assistant state."""

    def test_literal_passes_through(self, hass):
        assert render_template(hass, "Living Room") == "Living Room"

    def test_none_passes_through(self, hass):
        assert render_template(hass, None) is None

    def test_non_string_passes_through(self, hass):
        # Numbers, lists, dicts etc. aren't templated.
        assert render_template(hass, 42) == 42
        assert render_template(hass, [1, 2]) == [1, 2]

    def test_no_hass_returns_literal(self):
        # render_template needs hass to evaluate; without it, return the literal.
        assert render_template(None, "{{ 1 + 1 }}") == "{{ 1 + 1 }}"

    def test_simple_expression(self, hass):
        assert render_template(hass, "{{ 1 + 2 }}") == "3"

    def test_renders_entity_state(self, hass):
        hass.states.async_set("sensor.living_room", "21.5", {"friendly_name": "Living Room"})
        result = render_template(hass, "Room: {{ states('sensor.living_room') }}")
        assert result == "Room: 21.5"

    def test_bad_template_logs_warning_and_falls_back(self, hass, caplog):
        bad = "{{ states('sensor.x') | float / 0 }}"  # ZeroDivisionError inside Jinja
        with caplog.at_level(logging.WARNING, logger="custom_components.geekmagic.widgets.helpers"):
            result = render_template(hass, bad)
        assert result == bad
        assert any("Template error" in rec.getMessage() for rec in caplog.records)

    def test_syntax_error_logs_warning_and_falls_back(self, hass, caplog):
        bad = "{{ unterminated "
        with caplog.at_level(logging.WARNING, logger="custom_components.geekmagic.widgets.helpers"):
            result = render_template(hass, bad)
        assert result == bad
        assert any("Template error" in rec.getMessage() for rec in caplog.records)


class TestTemplateEntityIds:
    """Discover entity dependencies from a template."""

    def test_literal_returns_empty(self, hass):
        assert template_entity_ids(hass, "Living Room") == []

    def test_no_hass_returns_empty(self):
        assert template_entity_ids(None, "{{ states('sensor.x') }}") == []

    def test_finds_entity_in_states_call(self, hass):
        hass.states.async_set("sensor.x", "1")
        deps = template_entity_ids(hass, "{{ states('sensor.x') }}")
        assert "sensor.x" in deps

    def test_bad_template_returns_empty(self, hass):
        # Jinja syntax errors produce no dependencies, gracefully.
        assert template_entity_ids(hass, "{{ unterminated ") == []


class TestLabelForUsesRenderedLabel:
    """``Widget.label_for()`` should prefer the pre-rendered template label."""

    def test_label_for_uses_rendered_label(self):
        widget = ClockWidget(WidgetConfig(widget_type="clock", slot=0, label="{{ 'Hi' }}"))
        widget._rendered_label = "Hi"
        assert widget.label_for(None) == "Hi"

    def test_label_for_falls_back_to_config_label(self):
        # No _rendered_label set: legacy literal label still works.
        widget = ClockWidget(WidgetConfig(widget_type="clock", slot=0, label="Office"))
        assert widget.label_for(None) == "Office"

    def test_label_for_falls_back_to_friendly_name(self):
        widget = EntityWidget(WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.x"))
        entity = EntityState(entity_id="sensor.x", state="1", attributes={"friendly_name": "X"})
        assert widget.label_for(entity) == "X"

    def test_resolved_label_returns_none_for_no_label(self):
        widget = ClockWidget(WidgetConfig(widget_type="clock", slot=0))
        assert widget.resolved_label is None


class TestTrackedEntitiesIncludesTemplateDeps:
    """Template entities should surface through ``tracked_entities()``."""

    def test_template_entities_added(self):
        widget = ClockWidget(
            WidgetConfig(widget_type="clock", slot=0, label="{{ states('sensor.x') }}")
        )
        widget._template_entities = ["sensor.x"]
        # Clock overrides get_entities() to [] — tracked_entities still
        # surfaces template deps for coordinator pre-fetch.
        assert widget.get_entities() == []
        assert "sensor.x" in widget.tracked_entities()

    def test_primary_entity_and_template_entities_merged(self):
        widget = EntityWidget(
            WidgetConfig(
                widget_type="entity",
                slot=0,
                entity_id="sensor.primary",
                label="{{ states('sensor.template_dep') }}",
            )
        )
        widget._template_entities = ["sensor.template_dep"]
        entities = widget.tracked_entities()
        assert "sensor.primary" in entities
        assert "sensor.template_dep" in entities

    def test_no_duplicate_when_primary_is_template_dep(self):
        widget = EntityWidget(WidgetConfig(widget_type="entity", slot=0, entity_id="sensor.x"))
        widget._template_entities = ["sensor.x"]
        entities = widget.tracked_entities()
        assert entities.count("sensor.x") == 1


class TestCoordinatorResolvesTemplateLabels:
    """End-to-end: coordinator renders templates before widget rendering."""

    @pytest.fixture
    def coordinator(self, hass):
        from unittest.mock import AsyncMock, MagicMock

        from custom_components.geekmagic.const import (
            CONF_LAYOUT,
            CONF_REFRESH_INTERVAL,
            CONF_SCREENS,
            CONF_WIDGETS,
            LAYOUT_GRID_2X2,
        )
        from custom_components.geekmagic.coordinator import GeekMagicCoordinator

        device = MagicMock()
        device.upload_and_display = AsyncMock()
        options = {
            CONF_REFRESH_INTERVAL: 60,
            CONF_SCREENS: [
                {
                    "name": "Screen",
                    CONF_LAYOUT: LAYOUT_GRID_2X2,
                    CONF_WIDGETS: [
                        {
                            "type": "clock",
                            "slot": 0,
                            "label": "Now: {{ states('sensor.demo') }}",
                        },
                        {"type": "clock", "slot": 1, "label": "Static"},
                    ],
                }
            ],
        }
        return GeekMagicCoordinator(hass, device, options)

    def test_template_label_renders(self, hass, coordinator):
        hass.states.async_set("sensor.demo", "ready")
        coordinator._resolve_template_labels()

        widget = coordinator._layouts[0].slots[0].widget
        assert widget._rendered_label == "Now: ready"
        assert widget.resolved_label == "Now: ready"

    def test_static_label_passes_through(self, coordinator):
        coordinator._resolve_template_labels()

        widget = coordinator._layouts[0].slots[1].widget
        # Static labels don't need rendering — _rendered_label stays None.
        assert widget._rendered_label is None
        assert widget.resolved_label == "Static"

    def test_template_entities_recorded_at_construction(self, hass, coordinator):
        widget = coordinator._layouts[0].slots[0].widget
        assert "sensor.demo" in widget._template_entities
        assert "sensor.demo" in widget.tracked_entities()

    def test_bad_template_falls_back_to_literal(self, hass, coordinator, caplog):
        # Inject a widget with a runtime-failing template.
        widget = coordinator._layouts[0].slots[0].widget
        widget.config.label = "{{ states('sensor.demo') | float / 0 }}"
        with caplog.at_level(logging.WARNING, logger="custom_components.geekmagic.widgets.helpers"):
            coordinator._resolve_template_labels()
        # Literal fallback preserved.
        assert widget.resolved_label == "{{ states('sensor.demo') | float / 0 }}"


class TestNotifyRendersTemplates:
    """Notify service should resolve templates in message/image/icon."""

    @pytest.mark.asyncio
    async def test_notify_renders_message_template(self, hass):
        """The notify handler renders Jinja2 in the message field before
        forwarding the call to the coordinator."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from custom_components.geekmagic import async_setup
        from custom_components.geekmagic.const import DOMAIN

        hass.states.async_set("sensor.alert", "Smoke detected")

        with (
            patch(
                "custom_components.geekmagic.async_register_panel",
                AsyncMock(),
            ),
            patch(
                "custom_components.geekmagic.async_register_websocket_commands",
                MagicMock(),
            ),
        ):
            await async_setup(hass, {})

        coordinator = MagicMock()
        coordinator.trigger_notification = AsyncMock()
        # Make the registered handler dispatch to this coordinator regardless
        # of device_id resolution.
        captured: dict[str, dict] = {}

        async def fake_trigger(data):
            captured["data"] = dict(data)

        coordinator.trigger_notification = fake_trigger

        # Patch device registry lookup so dispatch reaches our coordinator.
        fake_device = MagicMock()
        fake_device.config_entries = {"entry-1"}
        with patch("homeassistant.helpers.device_registry.async_get") as mock_dr_get:
            mock_dr_get.return_value.async_get.return_value = fake_device
            hass.data[DOMAIN]["entry-1"] = coordinator

            with patch("custom_components.geekmagic.GeekMagicCoordinator", new=type(coordinator)):
                await hass.services.async_call(
                    DOMAIN,
                    "notify",
                    {
                        "device_id": "device-1",
                        "message": "Alert: {{ states('sensor.alert') }}",
                        "icon": "mdi:bell",
                        "image": "camera.front",
                    },
                    blocking=True,
                )

        data = captured.get("data")
        assert data is not None
        assert data["message"] == "Alert: Smoke detected"
        # Plain (non-template) fields pass through unchanged.
        assert data["icon"] == "mdi:bell"
        assert data["image"] == "camera.front"
