"""Declarative widget-layout primitive: ``DataCard``.

Most "complication"-style widgets (status, entity, text, progress,
climate, gauges, clock, ...) display the same conceptual three-band
shape:

  caption   ← caps-tracked tertiary label, top
  hero      ← primary big number/text, middle (auto-fit)
  support   ← optional row of small label/value chips
  indicator ← optional Bar / VerticalBar / Sparkline / Ring / Arc

Before this primitive existed, every widget hand-rolled its own
``int(width * 0.05)`` padding, ``current_y +=`` cursor, and
``is_narrow / is_compact / is_expanded`` cell-shape branching. Same
shape, seven slightly different implementations.

``DataCard`` lets a widget *list its data* in a single dataclass and
delegates layout to one shared policy:

  - **vertical** (``height > width x 1.8`` AND indicator is a
    ``VerticalBar``): stacked text column on the left, vertical bar on
    the right (or value-over-bar in very narrow cells).
  - **ring** (indicator is a ``Ring`` or ``Arc``): caption above, ring
    fills the rest, hero centred inside the ring.
  - **stacked** (``0.7 ≤ aspect ≤ 1.5`` AND ``min(w,h) ≥ 100``): three
    watchOS bands — caption row, hero row (auto-fit), supporting strip
    above the indicator. Justified ``space-evenly`` so the bands breathe.
  - **compact** (everything else — wide+short, tiny grids): an
    ``Adaptive([icon, caption, hero])`` header pinned to the top, the
    indicator pinned to the bottom.

The thresholds match ``component_helpers._pick_bar_mode`` (already
validated against the gauges samples). ``BarGauge`` / ``RingGauge`` /
``ArcGauge`` will be re-expressed as thin wrappers around ``DataCard``
in a later commit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from .colors import (
    THEME_PRIMARY,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
    Color,
)
from .components import (
    Adaptive,
    Arc,
    Column,
    Component,
    Flex,
    Icon,
    Ring,
    Row,
    Spacer,
    Stack,
    Text,
    VerticalBar,
)

if TYPE_CHECKING:
    from ..render_context import RenderContext


CardMode = Literal["auto", "stacked", "compact", "vertical", "ring"]


# =============================================================================
# Cell metrics — replaces the 12+ scattered ``int(width * 0.0X)`` calls.
# =============================================================================


@dataclass(frozen=True)
class CellMetrics:
    """Shared sizing rules derived from a cell's ``(width, height)``.

    Internal to ``data_card.py`` for now — kept here so a single tweak
    rebalances every card-style widget.
    """

    padding: int
    gap: int
    icon_size: int
    chip_icon_size: int
    bar_height: int


def cell_metrics(width: int, height: int) -> CellMetrics:
    """Return the sizing rules for a cell of the given dimensions."""
    short = min(width, height)
    return CellMetrics(
        padding=max(2, int(short * 0.05)),
        gap=max(2, int(height * 0.04)),
        # Lifted verbatim from IconValueDisplay's proven formula.
        icon_size=max(16, min(48, int(short * 0.30))),
        chip_icon_size=max(10, min(18, int(height * 0.08))),
        bar_height=max(4, int(height * 0.08)),
    )


# =============================================================================
# Mode picker — reuses BarGauge's validated thresholds.
# =============================================================================


def pick_card_mode(width: int, height: int, indicator: Component | None = None) -> CardMode:
    """Pick a layout mode for the given cell shape and indicator.

    Thresholds match ``component_helpers._pick_bar_mode`` (already
    validated against the gauges dashboard samples) plus two
    indicator-aware overrides:
      - ``Ring`` / ``Arc`` indicator → ``ring`` mode (label above,
        value inside the ring).
      - ``VerticalBar`` indicator on a tall+narrow cell → ``vertical``
        mode (thermometer / level-meter look).
    """
    if isinstance(indicator, (Ring, Arc)):
        return "ring"
    if isinstance(indicator, VerticalBar) and height > width * 1.8:
        return "vertical"
    aspect = width / max(height, 1)
    if 0.7 <= aspect <= 1.5 and min(width, height) >= 100:
        return "stacked"
    return "compact"


# =============================================================================
# Chip — structured supporting metric.
# =============================================================================


@dataclass
class Chip(Component):
    """A small icon+text supporting metric (target temp, humidity, ...).

    Renders as a tight ``Row[Icon?, Text]``. Used inside
    ``DataCard.supporting=[Chip(...), Chip(...)]`` to populate the
    third watchOS band — the supporting strip below the hero value.
    """

    text: str
    icon: str | None = None
    color: Color = THEME_TEXT_SECONDARY  # text colour; icon shares it

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return self._build(max_height).measure(ctx, max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        self._build(height).render(ctx, x, y, width, height)

    def _build(self, height: int) -> Component:
        """Return the underlying Row tree, sized for the row height."""
        # Icon size scales off the row height — chips usually live in
        # a strip ~12-18 px tall, so the icon stays inline with the
        # text glyphs.
        icon_px = max(10, min(18, int(height * 0.85)))
        children: list[Component] = []
        if self.icon:
            children.append(Icon(self.icon, size=icon_px, color=self.color))
        children.append(
            Text(self.text, font="tiny", color=self.color, truncate=True, auto_fit=True)
        )
        return Row(children=children, gap=4, justify="center", align="center")


# =============================================================================
# DataCard — the primitive.
# =============================================================================


@dataclass
class DataCard(Component):
    """Declarative complication-card layout.

    See module docstring for the layout policy. Any band may be ``None``
    or empty; missing bands collapse out of the flex tree without
    leaving zero-height spacers.
    """

    caption: str | None = None
    icon: str | None = None
    icon_color: Color = THEME_PRIMARY
    # ``"chip"`` keeps the icon inline beside the caption (small,
    # decorative). ``"feature"`` promotes it to its own band above
    # the caption — bigger, the way ``IconValueDisplay`` rendered
    # entity icons. Pick "feature" when the icon is the widget's
    # main visual identifier (entity, gauge), "chip" otherwise.
    icon_role: Literal["chip", "feature"] = "chip"
    hero: str = ""
    hero_color: Color = THEME_TEXT_PRIMARY
    supporting: list[Chip] = field(default_factory=list)
    indicator: Component | None = None
    mode: CardMode = "auto"
    # Optional override; ``None`` means "use cell_metrics(width, height)".
    padding: int | None = None

    def measure(self, ctx: RenderContext, max_width: int, max_height: int) -> tuple[int, int]:
        return (max_width, max_height)

    def render(self, ctx: RenderContext, x: int, y: int, width: int, height: int) -> None:
        chosen = self.mode if self.mode != "auto" else pick_card_mode(width, height, self.indicator)
        metrics = cell_metrics(width, height)
        pad = self.padding if self.padding is not None else metrics.padding

        if chosen == "ring":
            tree = self._build_ring(metrics, pad, width, height)
        elif chosen == "vertical":
            tree = self._build_vertical(metrics, pad, width)
        elif chosen == "stacked":
            tree = self._build_stacked(metrics, pad)
        else:
            tree = self._build_compact(metrics, pad)
        tree.render(ctx, x, y, width, height)

    # ------------------------------------------------------------------
    # Mode builders
    # ------------------------------------------------------------------

    def _hero_text(self, font: str = "huge") -> Component:
        return Text(
            self.hero,
            font=font,
            bold=True,
            color=self.hero_color,
            auto_fit=True,
        )

    def _caption_text(self) -> Text:
        return Text(
            (self.caption or "").upper(),
            font="tiny",
            color=THEME_TEXT_SECONDARY,
            truncate=True,
            auto_fit=True,
        )

    def _supporting_row(self) -> Component | None:
        """Build the supporting strip, or ``None`` if no chips."""
        if not self.supporting:
            return None
        # space-around gives every chip a half-gap on each side, which
        # reads as a tidy strip even with one chip.
        return Row(
            children=list(self.supporting),
            gap=8,
            justify="space-around",
            align="center",
        )

    def _build_stacked(self, metrics: CellMetrics, pad: int) -> Component:
        """Three watchOS bands — caption / hero / (supporting + indicator).

        With ``icon_role="feature"`` and an icon set, the icon gets
        its own band on top — the ``IconValueDisplay`` look that
        entity / gauge widgets relied on.
        """
        bands: list[Component] = []
        feature_icon = self.icon_role == "feature" and self.icon is not None
        if feature_icon:
            assert self.icon is not None  # ty narrow
            bands.append(
                Row(
                    children=[Icon(self.icon, size=metrics.icon_size, color=self.icon_color)],
                    justify="center",
                    align="center",
                )
            )
            if self.caption:
                bands.append(Row(children=[self._caption_text()], justify="center", align="center"))
        elif self.caption or self.icon:
            # chip role: icon and caption share one row.
            caption_children: list[Component] = []
            if self.icon:
                caption_children.append(
                    Icon(self.icon, size=metrics.chip_icon_size, color=self.icon_color)
                )
            if self.caption:
                caption_children.append(self._caption_text())
            bands.append(Row(children=caption_children, gap=4, justify="center", align="center"))
        # Hero band — the big value.
        if self.hero:
            bands.append(Row(children=[self._hero_text()], justify="center", align="center"))
        # Supporting strip.
        support = self._supporting_row()
        if support is not None:
            bands.append(support)
        # Indicator (bar / sparkline) at the bottom.
        if self.indicator is not None:
            bands.append(self.indicator)
        return Column(
            gap=metrics.gap,
            padding=pad,
            align="stretch",
            justify="space-evenly",
            children=bands,
        )

    def _build_compact(self, metrics: CellMetrics, pad: int) -> Component:
        """Header row pinned to top (icon + caption + hero); indicator at the
        bottom. The header uses ``Adaptive`` so it stacks vertically when too
        narrow to lay out horizontally.
        """
        icon_px = metrics.icon_size if self.icon_role == "feature" else metrics.chip_icon_size
        header_children: list[Component] = []
        if self.icon:
            header_children.append(Icon(self.icon, size=icon_px, color=self.icon_color))
        if self.caption:
            header_children.append(self._caption_text())
        if self.hero:
            # Push the hero to the right edge when there's a caption to
            # its left (label-left / value-right is the common compact
            # idiom). ``Spacer`` only makes sense when there are
            # left-hand siblings — otherwise ``Adaptive`` would push the
            # lone hero off-axis.
            if header_children:
                header_children.append(Spacer())
            header_children.append(
                Text(
                    self.hero,
                    font="medium",
                    bold=True,
                    color=self.hero_color,
                    auto_fit=True,
                )
            )

        rows: list[Component] = []
        if header_children:
            rows.append(Adaptive(children=header_children, gap=metrics.gap))
        support = self._supporting_row()
        if support is not None:
            rows.append(support)
        if self.indicator is not None:
            rows.append(self.indicator)
        return Column(
            gap=metrics.gap,
            padding=pad,
            align="stretch",
            justify="space-evenly",
            children=rows,
        )

    def _build_vertical(self, metrics: CellMetrics, pad: int, width: int) -> Component:
        """Tall+narrow cells with a ``VerticalBar`` indicator.

        Mirrors ``BarGauge._build_vertical``: very narrow cells stack
        everything (value, caption, then the bar fills the rest);
        wider verticals show value+caption on the left and the bar on
        the right.
        """
        text_column = Column(
            gap=2,
            padding=2,
            align="center",
            justify="center",
            children=[
                self._hero_text(font="medium"),
                self._caption_text(),
            ],
        )
        if width < 90:
            # Stack everything vertically; bar swallows the remaining
            # height at full cell width.
            return Column(
                gap=metrics.gap,
                padding=pad,
                align="stretch",
                justify="start",
                children=[
                    Row(
                        children=[self._hero_text(font="medium")], justify="center", align="center"
                    ),
                    Row(children=[self._caption_text()], justify="center", align="center"),
                    Flex(self.indicator) if self.indicator is not None else Spacer(),
                ],
            )
        children: list[Component] = [text_column]
        if self.indicator is not None:
            children.append(self.indicator)
        return Row(
            gap=metrics.gap,
            padding=pad,
            align="stretch",
            justify="start",
            children=children,
        )

    def _build_ring(self, metrics: CellMetrics, pad: int, width: int, height: int) -> Component:
        """Ring/Arc indicator: hero centred inside the ring.

        On roomy cells (``width ≥ 100`` AND ``height ≥ 100``) the
        caption sits on its own band above the ring; otherwise the
        caption is dropped to keep the ring readable.
        """
        # ring mode is only entered when self.indicator is a Ring/Arc
        # (pick_card_mode guarantees this). Build a Stack[ring/arc,
        # hero centred inside] — same shape RingGauge / ArcGauge use.
        assert self.indicator is not None
        inner = Stack(
            children=[
                self.indicator,
                Column(
                    align="center",
                    justify="center",
                    children=[self._hero_text(font="xlarge")],
                ),
            ]
        )
        roomy = width >= 100 and height >= 100
        if roomy and self.caption:
            return Column(
                gap=metrics.gap,
                padding=pad,
                align="stretch",
                justify="space-evenly",
                children=[
                    Row(children=[self._caption_text()], justify="center", align="center"),
                    Flex(inner),
                ],
            )
        # Tight cell: drop the caption, ring gets the whole cell.
        return Column(
            gap=metrics.gap,
            padding=pad,
            align="stretch",
            justify="space-evenly",
            children=[Flex(inner)],
        )


__all__ = [
    "CardMode",
    "CellMetrics",
    "Chip",
    "DataCard",
    "cell_metrics",
    "pick_card_mode",
]
