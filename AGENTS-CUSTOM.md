# Custom Widgets — AGENTS Guide

This fork of [adrienbrault/geekmagic-hacs](https://github.com/adrienbrault/geekmagic-hacs) adds custom widgets for the GeekMagic SmallTV Ultra display.

## Custom Widgets

| Widget | File | Type String | Needs Entity | Description |
| --- | --- | --- | --- | --- |
| Word Clock | `widgets/word_clock.py` | `word_clock` | No | Time as illuminated words on a letter grid |
| Pixel Clock | `widgets/pixel_clock.py` | `pixel_clock` | No | Retro pixel-art digits (green/amber/white) |
| System Monitor | `widgets/system_monitor.py` | `system_monitor` | No | CPU/RAM/disk/temp bars from Glances API |
| Analog Clock | `widgets/analog_clock.py` | `analog_clock` | No | Minimalist analog clock face with thin hands |
| Pi-hole Dashboard | `widgets/pihole_dashboard.py` | `pihole_dashboard` | Yes | Arc gauge with blocked % + query counts |
| Weather Card | `widgets/weather_card.py` | `weather_card` | Yes (weather) | Clean weather, integer temps, 3-day forecast |
| Niu Road | `widgets/niu_road.py` | `niu_road` | Yes (sensor) | Battery as road bar with scooter icon |
| Energy Graph | `widgets/energy_graph.py` | `energy_graph` | Yes (sensor) | Green energy sparkline with Grün/Gelb/Rot label |
| Berlin Greeting | `widgets/berlin_greeting.py` | `berlin_greeting` | Yes (weather) | German time-greeting + temp + date |

## Widget Pattern

Every widget follows the same pattern:

1. Extend `Widget` from `widgets/base.py`
2. Set `WIDGET_TYPE` (string identifier) and `SCHEMA` (UI config options)
3. Implement `render(ctx, state) -> Component`
4. Register in `widgets/__init__.py` (import + add to `_ALL_WIDGETS`)

See `widgets/clock.py` for the simplest upstream reference.

## Adding a New Widget

1. Create `custom_components/geekmagic/widgets/my_widget.py`
2. Add import + class to `_ALL_WIDGETS` in `widgets/__init__.py`
3. Commit, push, update via HACS, restart HA
4. The widget appears automatically in the GeekMagic UI dropdown

No frontend changes needed — the dropdown is populated dynamically from Python.

## Syncing with Upstream

```bash
git remote add upstream https://github.com/adrienbrault/geekmagic-hacs.git
git fetch upstream
git merge upstream/main
git push
```

Custom widget files won't conflict (they're new). Only `__init__.py` may need a simple merge.

## Reverting to Original

In HACS: remove the integration → re-add with URL `https://github.com/adrienbrault/geekmagic-hacs` → restart HA.
