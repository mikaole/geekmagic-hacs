"""Unit tests for the ``DataCard`` declarative widget primitive.

We test the *layout policy* — that ``pick_card_mode`` returns the right
mode for each cell shape, and that ``DataCard`` builds the expected
component tree for each mode. Pixel-rendered behaviour is exercised
through the per-widget sample regressions, not here.
"""

from __future__ import annotations

from typing import cast

import pytest

from custom_components.geekmagic.widgets.colors import (
    THEME_INFO,
    THEME_PRIMARY,
    THEME_TEXT_PRIMARY,
    THEME_TEXT_SECONDARY,
)
from custom_components.geekmagic.widgets.components import (
    Adaptive,
    Bar,
    Column,
    Icon,
    Ring,
    Row,
    Spacer,
    Stack,
    Text,
    VerticalBar,
)
from custom_components.geekmagic.widgets.data_card import (
    Chip,
    DataCard,
    cell_metrics,
    pick_card_mode,
)


class TestPickCardMode:
    """Threshold contract for ``pick_card_mode``.

    Mirrors ``component_helpers._pick_bar_mode`` (already validated
    against the gauges sample images) plus the indicator-aware
    overrides for Ring/Arc/VerticalBar.
    """

    def test_stacked_for_square_roomy_cells(self) -> None:
        # 110×110 is a 2x2 grid cell with default padding.
        assert pick_card_mode(110, 110) == "stacked"
        assert pick_card_mode(150, 150) == "stacked"

    def test_stacked_floor_is_100(self) -> None:
        # Just below the floor → compact, even though aspect is square.
        assert pick_card_mode(99, 99) == "compact"

    def test_compact_for_wide_short_cells(self) -> None:
        assert pick_card_mode(240, 80) == "compact"
        assert pick_card_mode(160, 60) == "compact"

    def test_compact_for_tiny_grids(self) -> None:
        # 3x3 grid cells — neither square enough nor tall enough.
        assert pick_card_mode(70, 70) == "compact"

    def test_vertical_only_with_vertical_bar(self) -> None:
        # 80×240 is height > width × 1.8, but no VerticalBar → compact.
        assert pick_card_mode(80, 240) == "compact"
        # With a VerticalBar indicator, switch to vertical mode.
        bar = VerticalBar(percent=50, color=THEME_PRIMARY)
        assert pick_card_mode(80, 240, bar) == "vertical"

    def test_vertical_threshold_is_strict(self) -> None:
        # height > width × 1.8 — exactly 1.8 is NOT vertical.
        bar = VerticalBar(percent=50, color=THEME_PRIMARY)
        assert pick_card_mode(100, 180, bar) == "compact"
        assert pick_card_mode(100, 181, bar) == "vertical"

    def test_ring_indicator_forces_ring_mode(self) -> None:
        ring = Ring(percent=50, color=THEME_PRIMARY)
        # Ring mode wins over stacked / compact, regardless of cell shape.
        assert pick_card_mode(70, 70, ring) == "ring"
        assert pick_card_mode(150, 150, ring) == "ring"
        assert pick_card_mode(240, 80, ring) == "ring"


class TestCellMetrics:
    """Sizing rules — replaces the scattered ``int(width * 0.0X)`` calls."""

    def test_padding_scales_with_short_side(self) -> None:
        m = cell_metrics(240, 240)
        assert m.padding == 12  # 5% of 240

    def test_padding_floor_is_two(self) -> None:
        # On a 30-px short side, 5% rounds to 1 → clamped to 2.
        m = cell_metrics(30, 30)
        assert m.padding >= 2

    def test_icon_size_clamps_to_48(self) -> None:
        # Big cell — 30% of 240 = 72, clamped down to 48.
        m = cell_metrics(240, 240)
        assert m.icon_size == 48

    def test_icon_size_floor_is_16(self) -> None:
        m = cell_metrics(40, 40)
        assert m.icon_size == 16


class TestDataCardStacked:
    """Stacked mode — three watchOS bands, ``space-evenly``."""

    def _stacked(self, **kwargs: object) -> Column:
        card = DataCard(mode="stacked", **kwargs)  # type: ignore[arg-type]
        return cast("Column", card._build_stacked(cell_metrics(120, 120), 6))

    def test_outer_is_space_evenly_column(self) -> None:
        col = self._stacked(caption="CPU", hero="73%")
        assert isinstance(col, Column)
        assert col.justify == "space-evenly"
        assert col.align == "stretch"

    def test_caption_band_uses_secondary_text(self) -> None:
        col = self._stacked(caption="CPU", hero="73%")
        # First band is the caption row.
        caption_row = col.children[0]
        assert isinstance(caption_row, Row)
        text = caption_row.children[0]
        assert isinstance(text, Text)
        assert text.text == "CPU"
        assert text.color == THEME_TEXT_SECONDARY

    def test_caption_band_drops_when_no_caption_or_icon(self) -> None:
        col = self._stacked(hero="73%")
        # No caption band — first band should be the hero.
        assert isinstance(col.children[0], Row)
        text = col.children[0].children[0]
        assert isinstance(text, Text)
        assert text.text == "73%"

    def test_caption_band_includes_icon_when_set(self) -> None:
        col = self._stacked(caption="CPU", icon="mdi:cpu", hero="73%")
        caption_row = col.children[0]
        assert isinstance(caption_row, Row)
        # Two children: icon + caption text.
        assert isinstance(caption_row.children[0], Icon)
        assert isinstance(caption_row.children[1], Text)

    def test_hero_uses_text_primary_by_default(self) -> None:
        col = self._stacked(caption="CPU", hero="73%")
        hero_row = col.children[1]
        assert isinstance(hero_row, Row)
        assert hero_row.children[0].color == THEME_TEXT_PRIMARY  # type: ignore[union-attr]

    def test_supporting_strip_present_when_chips_given(self) -> None:
        chips = [Chip("22°", icon="mdi:target")]
        col = self._stacked(caption="HEATING", hero="21°", supporting=chips)
        # Bands: caption, hero, supporting → 3.
        assert len(col.children) == 3
        support = col.children[2]
        assert isinstance(support, Row)
        assert support.justify == "space-around"

    def test_indicator_appended_at_the_end(self) -> None:
        bar = Bar(percent=73, color=THEME_PRIMARY)
        col = self._stacked(caption="CPU", hero="73%", indicator=bar)
        assert col.children[-1] is bar


class TestDataCardCompact:
    """Compact mode — header pinned top via Adaptive, indicator pinned bottom."""

    def _compact(self, **kwargs: object) -> Column:
        card = DataCard(mode="compact", **kwargs)  # type: ignore[arg-type]
        return cast("Column", card._build_compact(cell_metrics(240, 80), 6))

    def test_outer_is_space_evenly_column(self) -> None:
        col = self._compact(caption="CPU", hero="73%")
        assert isinstance(col, Column)
        assert col.justify == "space-evenly"

    def test_header_uses_adaptive(self) -> None:
        col = self._compact(caption="CPU", hero="73%")
        header = col.children[0]
        assert isinstance(header, Adaptive)

    def test_compact_header_has_spacer_between_caption_and_hero(self) -> None:
        col = self._compact(caption="CPU", hero="73%")
        header = cast("Adaptive", col.children[0])
        # Children: caption text, Spacer, hero text.
        assert isinstance(header.children[0], Text)
        assert isinstance(header.children[1], Spacer)
        assert isinstance(header.children[2], Text)

    def test_compact_no_spacer_when_only_hero(self) -> None:
        col = self._compact(hero="73%")
        header = cast("Adaptive", col.children[0])
        # Just the hero text — no leading caption, no spacer.
        assert len(header.children) == 1
        assert isinstance(header.children[0], Text)

    def test_compact_indicator_appended(self) -> None:
        bar = Bar(percent=73, color=THEME_PRIMARY)
        col = self._compact(caption="CPU", hero="73%", indicator=bar)
        assert col.children[-1] is bar


class TestDataCardRing:
    """Ring mode — hero centred inside the indicator ring."""

    def test_roomy_cell_keeps_caption_above(self) -> None:
        ring = Ring(percent=70, color=THEME_PRIMARY)
        card = DataCard(mode="ring", caption="CPU", hero="70%", indicator=ring)
        col = cast("Column", card._build_ring(cell_metrics(150, 150), 6, 150, 150))
        # Bands: caption row, Flex(Stack).
        assert len(col.children) == 2
        assert isinstance(col.children[0], Row)
        # Hero is wrapped inside the Stack.
        flex = col.children[1]
        stack = flex.child  # type: ignore[attr-defined]
        assert isinstance(stack, Stack)

    def test_tight_cell_drops_caption(self) -> None:
        ring = Ring(percent=70, color=THEME_PRIMARY)
        card = DataCard(mode="ring", caption="CPU", hero="70%", indicator=ring)
        col = cast("Column", card._build_ring(cell_metrics(80, 80), 6, 80, 80))
        # Caption dropped — only the Flex(Stack).
        assert len(col.children) == 1


class TestChip:
    """Chip — small icon+text supporting metric."""

    def test_no_icon_renders_text_only(self) -> None:
        chip = Chip("22°")
        row = cast("Row", chip._build(20))
        assert isinstance(row, Row)
        assert len(row.children) == 1
        assert isinstance(row.children[0], Text)

    def test_with_icon_renders_two_children(self) -> None:
        chip = Chip("58%", icon="mdi:water-percent", color=THEME_INFO)
        row = cast("Row", chip._build(20))
        assert len(row.children) == 2
        assert isinstance(row.children[0], Icon)
        assert isinstance(row.children[1], Text)

    def test_chip_color_propagates_to_text_and_icon(self) -> None:
        chip = Chip("58%", icon="mdi:water-percent", color=THEME_INFO)
        row = cast("Row", chip._build(20))
        icon, text = row.children[0], row.children[1]
        assert isinstance(icon, Icon)
        assert isinstance(text, Text)
        assert icon.color == THEME_INFO
        assert text.color == THEME_INFO


class TestDataCardAutoMode:
    """Auto mode resolves through ``pick_card_mode`` at render time."""

    @pytest.mark.parametrize(
        ("width", "height", "indicator", "expected"),
        [
            (110, 110, None, "stacked"),
            (240, 80, None, "compact"),
            (70, 70, None, "compact"),
            (80, 240, None, "compact"),  # No vertical bar → compact, not vertical
            (80, 240, VerticalBar(percent=50, color=THEME_PRIMARY), "vertical"),
            (110, 110, Ring(percent=50, color=THEME_PRIMARY), "ring"),
        ],
    )
    def test_resolves_expected_mode(
        self, width: int, height: int, indicator: object, expected: str
    ) -> None:
        assert pick_card_mode(width, height, indicator) == expected  # type: ignore[arg-type]
