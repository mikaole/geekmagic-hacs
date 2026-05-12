"""Image entity widget for GeekMagic displays.

Renders Home Assistant `image.*` entities (e.g. Frigate snapshots like
`image.front_camera_person`). The widget reuses the Camera widget's
rendering path — only the entity-resolution and pre-fetch source differs
(image entities expose `entity_picture` + `image_last_updated`, not the
camera component's `async_get_image`).
"""

from __future__ import annotations

from typing import Any, ClassVar

from .camera import CameraWidget


class ImageEntityWidget(CameraWidget):
    """Widget that displays a Home Assistant `image.*` entity.

    Inherits CameraWidget's rendering so that the `WidgetState.image` slot
    populated by the coordinator's pre-fetch shows up identically. The
    only thing that differs is the schema's `entity_domains` — this widget
    targets `image` entities, the parent targets `camera` entities.
    """

    WIDGET_TYPE: ClassVar[str] = "image_entity"
    SCHEMA: ClassVar[dict[str, Any]] = {
        "name": "Image Entity",
        "needs_entity": True,
        "entity_domains": ["image"],
        "options": [
            {
                "key": "fit",
                "type": "select",
                "label": "Fit Mode",
                "options": ["cover", "contain"],
                "default": "contain",
            },
            {"key": "show_label", "type": "boolean", "label": "Show Label", "default": False},
        ],
    }
