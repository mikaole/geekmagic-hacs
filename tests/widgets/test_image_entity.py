"""Tests for the ImageEntityWidget and image.* entity pre-fetch path."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from custom_components.geekmagic.const import (
    CONF_LAYOUT,
    CONF_REFRESH_INTERVAL,
    CONF_SCREENS,
    CONF_WIDGETS,
    LAYOUT_GRID_2X2,
)
from custom_components.geekmagic.coordinator import GeekMagicCoordinator
from custom_components.geekmagic.render_context import RenderContext
from custom_components.geekmagic.renderer import Renderer
from custom_components.geekmagic.widgets import WIDGET_CLASSES, WIDGET_TYPE_SCHEMAS
from custom_components.geekmagic.widgets.base import WidgetConfig
from custom_components.geekmagic.widgets.camera import CameraImage, CameraWidget
from custom_components.geekmagic.widgets.image_entity import ImageEntityWidget
from custom_components.geekmagic.widgets.state import WidgetState


class TestImageEntityWidget:
    """Tests for the ImageEntityWidget class itself."""

    def test_registered_in_widget_classes(self):
        """The new widget type is exposed via WIDGET_CLASSES."""
        assert "image_entity" in WIDGET_CLASSES
        assert WIDGET_CLASSES["image_entity"] is ImageEntityWidget

    def test_schema_targets_image_domain(self):
        """Schema must restrict entity selection to the `image` domain."""
        assert "image_entity" in WIDGET_TYPE_SCHEMAS
        schema = WIDGET_TYPE_SCHEMAS["image_entity"]
        assert schema["needs_entity"] is True
        assert schema["entity_domains"] == ["image"]
        assert schema["name"] == "Image Entity"

    def test_inherits_camera_for_prefetch_dispatch(self):
        """Pre-fetch loop branches on isinstance(CameraWidget); must inherit."""
        assert issubclass(ImageEntityWidget, CameraWidget)

    def test_render_placeholder_when_no_image(self):
        """No pre-fetched image → fall back to camera's placeholder component."""
        renderer = Renderer()
        _img, draw = renderer.create_canvas()
        ctx = RenderContext(draw, (0, 0, 100, 100), renderer)

        widget = ImageEntityWidget(
            WidgetConfig(
                widget_type="image_entity",
                slot=0,
                entity_id="image.front_camera_person",
            )
        )
        state = WidgetState(
            entity=None,
            entities={},
            image=None,
            now=datetime.now(tz=UTC),
        )
        component = widget.render(ctx, state)
        # Camera's placeholder is a Column wrapping an Icon + Text.
        from custom_components.geekmagic.widgets.components import Column

        assert isinstance(component, Column)

    def test_render_returns_camera_image_when_prefetched(self):
        """With a pre-fetched PIL image, render must produce a CameraImage."""
        renderer = Renderer()
        _img, draw = renderer.create_canvas()
        ctx = RenderContext(draw, (0, 0, 100, 100), renderer)

        widget = ImageEntityWidget(
            WidgetConfig(
                widget_type="image_entity",
                slot=0,
                entity_id="image.front_camera_person",
                options={"fit": "cover"},
            )
        )
        sample = Image.new("RGB", (16, 16), (10, 20, 30))
        state = WidgetState(
            entity=None,
            entities={},
            image=sample,
            now=datetime.now(tz=UTC),
        )

        component = widget.render(ctx, state)
        assert isinstance(component, CameraImage)
        assert component.fit == "cover"


class TestCoordinatorImageEntityPrefetch:
    """Tests for the coordinator's image.* pre-fetch branch."""

    @pytest.fixture
    def device(self):
        device = MagicMock()
        device.upload_and_display = AsyncMock()
        device.set_brightness = AsyncMock()
        device.get_brightness = AsyncMock(return_value=50)
        device.get_state = AsyncMock(return_value=None)
        device.get_space = AsyncMock(return_value=None)
        return device

    @pytest.fixture
    def options(self):
        return {
            CONF_REFRESH_INTERVAL: 60,
            CONF_SCREENS: [
                {
                    "name": "Screen 1",
                    CONF_LAYOUT: LAYOUT_GRID_2X2,
                    CONF_WIDGETS: [
                        {
                            "type": "image_entity",
                            "slot": 0,
                            "entity_id": "image.front_camera_person",
                        }
                    ],
                }
            ],
        }

    @pytest.mark.asyncio
    async def test_image_entity_routed_to_url_fetch(self, hass, device, options):
        """image.* widgets must use the entity_picture URL path, not camera.async_get_image."""
        coordinator = GeekMagicCoordinator(hass, device, options)

        hass.states.async_set(
            "image.front_camera_person",
            "2026-05-12T10:00:00+00:00",
            {
                "entity_picture": "/api/image_proxy/image.front_camera_person?token=abc",
                "image_last_updated": "2026-05-12T10:00:00+00:00",
            },
        )

        url_fetch = AsyncMock()
        with (
            patch.object(coordinator, "_async_fetch_url_image_to_cache", url_fetch),
            patch(
                "homeassistant.components.camera.async_get_image",
                new=AsyncMock(),
            ) as cam_fetch,
        ):
            await coordinator._async_fetch_camera_images()

        url_fetch.assert_awaited_once_with("image.front_camera_person")
        cam_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_url_fetch_appends_cache_bust_for_image_entity(self, hass, device, options):
        """`image_last_updated` should be appended to the URL as `_=<ts>`."""
        coordinator = GeekMagicCoordinator(hass, device, options)

        hass.states.async_set(
            "image.front_camera_person",
            "2026-05-12T10:00:00+00:00",
            {
                "entity_picture": "/api/image_proxy/image.front_camera_person?token=abc",
                "image_last_updated": "2026-05-12T10:00:00+00:00",
            },
        )

        captured_url: dict[str, str] = {}

        class _Resp:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def read(self):
                return b"jpegbytes"

        class _Session:
            def get(self, url, timeout=10):
                captured_url["url"] = url
                return _Resp()

        with (
            patch(
                "custom_components.geekmagic.coordinator.get_url",
                return_value="http://homeassistant.local:8123",
            ),
            patch(
                "custom_components.geekmagic.coordinator.async_get_clientsession",
                return_value=_Session(),
            ),
        ):
            await coordinator._async_fetch_url_image_to_cache("image.front_camera_person")

        assert "url" in captured_url
        url = captured_url["url"]
        # Original entity_picture path is preserved
        assert "/api/image_proxy/image.front_camera_person?token=abc" in url
        # Cache-bust query appended via & (entity_picture already had ?token=)
        assert "&_=2026-05-12T10:00:00+00:00" in url
        # Image saved to cache
        assert coordinator._camera_images.get("image.front_camera_person") == b"jpegbytes"

    @pytest.mark.asyncio
    async def test_url_fetch_skips_cache_bust_for_camera_url_sources(self, hass, device, options):
        """Non-image domains shouldn't have the `_=` cache-bust appended."""
        coordinator = GeekMagicCoordinator(hass, device, options)

        hass.states.async_set(
            "media_player.kitchen",
            "playing",
            {
                "entity_picture": "/api/media_player_proxy/kitchen",
                "image_last_updated": "2026-05-12T10:00:00+00:00",
            },
        )

        captured_url: dict[str, str] = {}

        class _Resp:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def read(self):
                return b"png"

        class _Session:
            def get(self, url, timeout=10):
                captured_url["url"] = url
                return _Resp()

        with (
            patch(
                "custom_components.geekmagic.coordinator.get_url",
                return_value="http://homeassistant.local:8123",
            ),
            patch(
                "custom_components.geekmagic.coordinator.async_get_clientsession",
                return_value=_Session(),
            ),
        ):
            await coordinator._async_fetch_url_image_to_cache("media_player.kitchen")

        assert "_=" not in captured_url["url"]

    @pytest.mark.asyncio
    async def test_build_widget_states_loads_prefetched_image(self, hass, device, options):
        """Pre-fetched bytes in _camera_images become a PIL.Image in WidgetState."""
        coordinator = GeekMagicCoordinator(hass, device, options)

        # Make a real JPEG-encoded blob so PIL can actually open it.
        from io import BytesIO

        buf = BytesIO()
        Image.new("RGB", (8, 8), (255, 0, 0)).save(buf, format="JPEG")
        coordinator._camera_images["image.front_camera_person"] = buf.getvalue()

        hass.states.async_set(
            "image.front_camera_person",
            "2026-05-12T10:00:00+00:00",
            {
                "entity_picture": "/api/image_proxy/image.front_camera_person",
                "image_last_updated": "2026-05-12T10:00:00+00:00",
            },
        )

        layout = coordinator._layouts[0]
        states = coordinator._build_widget_states(layout)

        assert 0 in states
        ws = states[0]
        assert ws.image is not None
        assert ws.image.size == (8, 8)
