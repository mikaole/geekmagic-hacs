"""Base widget class and configuration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ..render_context import RenderContext
    from .components import Component
    from .state import EntityState, WidgetState


@dataclass
class WidgetConfig:
    """Configuration for a widget."""

    widget_type: str
    slot: int = 0
    entity_id: str | None = None
    label: str | None = None
    color: tuple[int, int, int] | None = None
    options: dict[str, Any] = field(default_factory=dict)


class Widget(ABC):
    """Base class for all widgets.

    Widgets render by returning a Component tree. All state needed for
    rendering is passed via the WidgetState parameter, enabling pure
    functional rendering.
    """

    WIDGET_TYPE: ClassVar[str] = ""
    SCHEMA: ClassVar[dict[str, Any]] = {}

    def __init__(self, config: WidgetConfig) -> None:
        """Initialize the widget.

        Args:
            config: Widget configuration
        """
        self.config = config
        # Pre-rendered template label (populated by the coordinator on each
        # update cycle when ``config.label`` contains Jinja2 syntax). Falls
        # back to ``config.label`` when unset or when the template fails.
        self._rendered_label: str | None = None
        # Entity IDs the label template depends on, populated at widget
        # construction time. Surfaced via ``get_entities()`` so the
        # coordinator pre-fetches their state for rendering.
        self._template_entities: list[str] = []

    @property
    def entity_id(self) -> str | None:
        """Get the entity ID this widget tracks."""
        return self.config.entity_id

    @property
    def resolved_label(self) -> str | None:
        """Return the rendered template label if available, else config.label.

        Widgets that want the user-configured label (with templates already
        resolved) should read this instead of ``self.config.label``.
        """
        return self._rendered_label or self.config.label

    def set_rendered_label(self, value: str | None) -> None:
        """Set the pre-rendered template label (coordinator only)."""
        self._rendered_label = value

    def set_template_entities(self, entity_ids: list[str]) -> None:
        """Record entity IDs referenced by the label template (coordinator only)."""
        self._template_entities = list(entity_ids)

    def get_entities(self) -> list[str]:
        """Return list of entity IDs this widget depends on.

        Override in subclasses that track entities.
        """
        if self.config.entity_id:
            return [self.config.entity_id]
        return []

    def tracked_entities(self) -> list[str]:
        """Return entities the coordinator should pre-fetch for this widget.

        Union of ``get_entities()`` and any entity IDs referenced by a
        templated ``label`` — so changes to a template's source entities
        propagate on the next refresh cycle.
        """
        entities = list(self.get_entities())
        for eid in self._template_entities:
            if eid not in entities:
                entities.append(eid)
        return entities

    def label_for(self, entity: EntityState | None, *, fallback: str = "") -> str:
        """Resolve display label: rendered label > ``entity.friendly_name`` > ``fallback``.

        The rendered label is either the pre-rendered Jinja2 result (when
        ``config.label`` contains template syntax) or the literal
        ``config.label`` itself. ``EntityState.friendly_name`` already
        falls back to ``entity_id`` when no friendly name attribute is set.
        """
        label = self.resolved_label
        if label:
            return label
        if entity is not None:
            return entity.friendly_name
        return fallback

    @abstractmethod
    def render(
        self,
        ctx: RenderContext,
        state: WidgetState,
    ) -> Component:
        """Render the widget as a Component tree.

        Pure function: given the same ctx and state, returns the same Component.
        All state needed for rendering is provided via the state parameter.

        Args:
            ctx: RenderContext providing local coordinate system and drawing methods.
                 Use ctx.width and ctx.height for container dimensions.
                 All drawing coordinates are relative to widget origin (0, 0).
            state: Pre-fetched state including entity data, history, images, time.

        Returns:
            Component tree to render
        """
