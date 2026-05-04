# Product Opportunity Analysis — GeekMagic HACS

> A product-lens look at the integration: who it's for, what jobs it does, where it's weak,
> and a wide creative ideation space (Opportunity Solution Tree) for what to explore next.
> Sources: codebase, README, sample renders, panel screenshot, GitHub issues #1–#112.

---

## 1. What is the product, really?

**Concept in one line:** a server-side renderer in Home Assistant that turns a $20–$30
GeekMagic clock into a glanceable, fully customizable smart-home display — *no flashing
required*.

**The clever wedge.** Most "ESPHome-on-display" projects fight the device's bootloader,
stock firmware, and fonts. This integration sidesteps all of that by treating the device
as a dumb 240×240 frame buffer reachable over HTTP. Pillow does the rendering on the HA
host. That single architectural decision is the product's superpower:

- It works on **stock firmware** (key for non-tinkerers).
- It can do **anything Pillow can draw** — gauges, candlesticks, camera snapshots,
  themed typography — far beyond what stock ESP UIs can do.
- It can ship new widgets and themes without a single device-side update.
- It naturally extends to **non-GeekMagic targets** (other 240×240 HTTP-uploadable
  displays, e-paper, browser, Kindle, etc.) with the same render core.

**The cost of the wedge.** A render-and-push architecture also defines the product's
dominant pain points:

- It's polling-based, not event-driven → freshness vs. flash wear vs. battery tradeoffs.
- The device is "headless" from HA's perspective → device buttons, native modes, and
  stock screens are second-class.
- Every render goes through HA → HA breakage = display breakage (#111, #112).
- Every firmware variant is a new compatibility surface (Ultra vs. Pro vs. ESP32 vs.
  bvweerd's open firmware) → a long tail of "doesn't quite work" issues.

---

## 2. Users & Jobs-To-Be-Done

### Primary segments

| Segment | Description | Tells |
|---|---|---|
| **Tinkerer** | HA power user who buys cheap displays for fun. Comfortable with YAML, custom firmware, debugging. | Authors most issues. Writes detailed traces. Wants templating, attributes, conditional widgets. |
| **Aesthete** | Cares about the *look* of the home. Picks devices that decorate a desk/shelf/nightstand. | Asks for themes, fonts, photo mode, album art, larger text, hero layouts. |
| **Glanceable-info user** | Wants 1 piece of info: time, weather, energy, doorbell. Doesn't care how. | Asks "how do I make text bigger" (#10, #31), "doors open/closed" (#18). |
| **HA newbie / gift-recipient** | Got the device, doesn't know HA deeply. | Setup errors, IP confusion, "it's offline" frustration (#2, #25, #77). |

### Top JTBDs

1. **Ambient awareness** — *"While I walk past, tell me one important thing about my home."*
2. **Live status board** — *"Show me the few sensors I check often, without unlocking my phone."*
3. **Reactive surface** — *"When the doorbell rings or motion is detected, surface that here."*
4. **Decoration-with-utility** — *"Make my desk/nightstand look cool, with useful info."*
5. **Cheap signage** — *"Display a useful image (camera, schedule, score) on a small cheap screen."*

---

## 3. Value vs. Problems

### Where the product *delivers* today

- **Catalog breadth:** 16 widgets × 19 layouts × 10 themes is a lot of expressive surface
  for 240×240 px. Hero/sidebar/corner layouts especially differentiate it from other
  HA-display projects.
- **Visual configuration with live preview** — the panel is the right primitive, and the
  preview-as-you-edit experience is genuinely good (see `docs/panel-editor.png`).
- **No flashing** — this remains the strongest distribution lever vs. ESPHome forks.
- **Notify service** — temporary alerts with image, icon, theme. A real interruption
  primitive.
- **Multi-device + global views** — create once, assign anywhere, auto-cycle.
- **Themes that touch typography/spacing**, not just colors. Underrated.

### Where it hurts (clusters from issues)

| # | Cluster | Representative issues | Why it matters |
|---|---|---|---|
| P1 | **Device/firmware fragmentation** | #2, #8, #11, #13, #37, #59, #63, #64, #76, #77, #89, #93, #108, #109 | Pro vs. Ultra mis-detection, ESP32 buttons, two devices showing up, "image not found", connection refused. Sets a low ceiling on first-run delight. |
| P2 | **Reliability under HA upgrades & device offline** | #25, #26, #36, #111, #112 | Log spam → 500 errors, setup error states, breaking changes from HA core. The integration is fragile to its environment. |
| P3 | **Limited expressiveness** | #10, #15, #18, #31, #60, #65, #73, #91, #92, #94 | Bigger text, dynamic icons, markdown, decimals, templates in labels, attributes on entity widget. Users want a thin programming model. |
| P4 | **Configuration UX gaps** | #4, #21, #22, #61, #65, #79, #81, #97 | "No add view button", iPhone trap with no hamburger, color picker broken in Safari, dropdowns inactive on mobile, layout icons inaccurate, preview entity stale. |
| P5 | **Theme/render polish bugs** | #20, #48, #75, #79, #85, #95, #98 | Off-screen text, color crash, theme only changes background, light theme white-on-white notifications, weather day shifted. The polish gap between "looks great in samples" and "works in my house". |
| P6 | **Native firmware integration** | #11, #46(closed), #56, #57, #64, #87, #90 | Mode selector doesn't hold, native views can't be in rotation, no static image/gif widget, no HACS releases, image entity (Frigate) not supported. The product treats native firmware as a competitor instead of a partner. |
| P7 | **Discoverability of capability** | #21, #30, #31, #38, #65, #91 | "Is there a way to display X?" — the answer is usually "yes, but..." Users don't know what the product can already do. |

### The single biggest underserved outcome

Across these clusters, the deepest unmet need is:

> **"I want to compose exactly the screen I imagine, with the data I have, and trust it
> won't break."**

That's two things: **expressiveness** (a thin templating/composition model) and
**reliability** (it survives HA upgrades, device reboots, and edge firmwares).

---

## 4. Opportunity Solution Tree

```
                 ┌─────────────────────────────────────────────────┐
                 │  OUTCOME                                        │
                 │  More users keep a GeekMagic display running    │
                 │  daily as a useful, beloved part of their home. │
                 └────────────────────────┬────────────────────────┘
                                          │
        ┌─────────────────┬───────────────┼────────────────┬─────────────────┐
        │                 │               │                │                 │
   ┌────▼────┐       ┌────▼────┐     ┌────▼─────┐     ┌────▼────┐      ┌─────▼─────┐
   │  O1     │       │  O2     │     │   O3     │     │  O4     │      │   O5      │
   │ Set up  │       │ Build a │     │ Stays    │     │ Reacts  │      │ Extend,   │
   │ in <5m, │       │ view I  │     │ accurate │     │ to      │      │ share,    │
   │ it just │       │ love,   │     │ & beauti-│     │ context │      │ show off  │
   │ works   │       │ fast    │     │ ful, no  │     │ &       │      │ my dis-   │
   │         │       │         │     │ breakage │     │ events  │      │ play      │
   └────┬────┘       └────┬────┘     └────┬─────┘     └────┬────┘      └─────┬─────┘
        │                 │               │                │                 │
  (opportunities below for each outcome — solutions are leaves)
```

### O1 — *"Set it up in 5 min and it just works"*

| Opportunity | Possible solutions |
|---|---|
| **OP1.1 Right device, first try** | mDNS/SSDP autodiscovery; firmware fingerprinting (Pro vs. Ultra vs. ESP32 vs. bvweerd) using `/app.json` shape; one device entry per *physical* unit (fix #89); diagnostic test page in config flow ("we detected: model X, fw Y, here's what works"). |
| **OP1.2 Survive bad inputs** | Accept hostname/domain/URL and auto-add port (fix #35, #77); validate firmware compatibility with a known matrix; show helpful error: "your firmware returns malformed HTTP, try v2.x of bvweerd FW" (fix #8). |
| **OP1.3 Friendly empty state** | First-run wizard: "pick what you want to see" → Energy / Family / Bedside / Weather → generates 3 starter views; prebuilt template gallery in the panel. |
| **OP1.4 Discoverable panel** | Add hamburger / back button on panel for mobile (fix #22); persistent help drawer; "what can each widget do?" inline examples. |

### O2 — *"Build the view I imagine, fast"*

| Opportunity | Possible solutions |
|---|---|
| **OP2.1 Templating everywhere** | Jinja2 in widget labels, prefixes, suffixes, colors, icons (#73, #92); a `template` widget that takes a Jinja string + size; entity attribute on every widget type that supports an entity (#91). |
| **OP2.2 Conditional widgets** | "Show only when entity == X / state changed in last N min / between hours"; alternate widgets per slot, like a tiny `if/elif/else`. |
| **OP2.3 Dynamic icons & states** | On/off icon pairs (#15, #18); domain-aware icon resolution (already partly there); "icon from template" string; per-state colors for status widgets (#48 root cause: color parsing). |
| **OP2.4 Bigger / smarter typography** | Auto-fit text widget for any entity (#10, #31); per-widget font scale slider; "text shrink to fit" toggle; markdown subset in text widget (#60: bold/color/icon inline). |
| **OP2.5 Lovelace import** | "Mirror this Lovelace card" — render an existing entities/glance/sensor card as a view (#38). Massive shortcut to value. |
| **OP2.6 LLM design assistant** | "Describe the view you want" → generates a layout + widget config draft. Lowers the activation cost dramatically; uses HA's exposed entities as context. |
| **OP2.7 In-panel duplication / version history** | Duplicate exists; add undo/version history per view; "test on device" button vs. "save"; A/B preview between two themes side-by-side. |
| **OP2.8 Preview parity** | Album art / camera snapshot in preview (#21); preview entity refreshes on coordinator tick, not just on button (#81); accurate layout icons (#79). |

### O3 — *"Stays accurate, beautiful, no breakage"*

| Opportunity | Possible solutions |
|---|---|
| **OP3.1 Resilient to HA upgrades** | Pin & vendor `stretchable` (#112) or replace with pure-python layout; CI matrix against HA `dev` / `beta`; add a smoke-test config entry that catches setup-time regressions. |
| **OP3.2 Graceful offline behavior** | Exponential backoff with capped retries (closes #36 spam); device state = `unavailable` not `error`; auto-recover on reconnect (fix #25, #26); suppress traceback for connection refused. |
| **OP3.3 Theme integrity** | Audit theme tokens — every drawable should pull color from theme (#85: charts/icons hardcoded); contrast tester for light themes (#95: white-on-white); per-theme palette test in CI snapshot. |
| **OP3.4 Render correctness** | Snapshot tests for every widget × layout combo (already partly via `samples/`); regression image diff in CI; weather day-of-week timezone fix (#75); media paused centering (#20). |
| **OP3.5 Reduce flash wear** | (#96) JPEG diffing — only upload if image changed; delta uploads or display-side image cache; longer default refresh + "fast mode" toggle; only rerender if entity state changed since last frame. |
| **OP3.6 HACS releases** | Tagged releases + changelogs (#57); semantic versioning; "breaking change" banner in the panel after major upgrades. |

### O4 — *"Reacts to events & context"*

| Opportunity | Possible solutions |
|---|---|
| **OP4.1 Event-driven views** | Rule engine: "when `binary_sensor.front_door` → show camera.front_door for 30s"; codify the notify pattern as first-class triggers; support image entities like Frigate's last-detection (#87). |
| **OP4.2 Time-of-day rotations** | "Morning view: weather & calendar; daytime: dashboard; evening: media; night: dim clock"; sunrise/sunset triggers; bedside-friendly auto-dim. |
| **OP4.3 Native firmware coexistence** | Re-add native screens to the rotation (#90); "passthrough" mode that yields control to native firmware on a schedule; respect mode-switch persistence (#11). |
| **OP4.4 Display as an input** | Pro has buttons (#37, #64) — wire `next/prev/enter` into HA events; tap → fire a scene; long-press → show "control" view; gesture → wake. |
| **OP4.5 Notifications you can iterate on** | Templated message body (#92); queueing multiple notifications; priority levels; sticky vs. transient; dismiss action via button. |

### O5 — *"Extend, share, show off"*

| Opportunity | Possible solutions |
|---|---|
| **OP5.1 View marketplace** | Export view as YAML/JSON; import from URL/gist; a community "view gallery" (similar to Lovelace examples). Drives discovery (#65, #21, "how do I do X"). |
| **OP5.2 Lovelace-side card** | A Lovelace card that shows the device's current render (already an `image` entity exists); plus a "control" card to switch views. |
| **OP5.3 Beyond GeekMagic** | Same renderer → e-paper (Inkplate/TRMNL), Kindle, browser kiosk, Wyze/ESP32 generic 240×240. Reframes the project from "GeekMagic integration" to "HA glance-display kit". |
| **OP5.4 Public display API** | Expose a stable websocket API (already partly there) that other frontends can target — e.g., a wall-mounted iPad showing 4 GeekMagic-style tiles. |
| **OP5.5 Templates for common roles** | Curated bundles: "Bedside clock", "Kitchen weather", "Server rack", "EV charging", "Family status", "Nursery". Each is one-tap install. |
| **OP5.6 ESPHome/native firmware co-marketing** | First-class link to bvweerd's firmware; "want better support? flash this" path. Turn fragmentation into a tier system (Tier 1: bvweerd FW + Ultra; Tier 2: stock; Tier 3: best-effort). |

---

## 5. Creative ideation — beyond the issue tracker

Not gated on plausibility. The point is to widen the search, not converge.

### A. Make the display *alive*

- **Breathing widgets** — subtle pulse when a value changes (animated GIF upload, since
  device supports it).
- **Transition frames** — when switching views, render 5–10 interpolated frames so the
  display fades/slides instead of jump-cuts.
- **Ambient mode** — particles, slow gradient, or pixel-rain background that reacts to
  weather (rain → falling pixels, snow → flakes, sun → warm gradient).
- **"Now playing" visualizer** — render a tiny waveform/spectrum from media volume + BPM
  metadata.
- **Time-driven theme drift** — themes auto-warm at sunset, cool at sunrise; "forest" by
  day, "neon" at night.

### B. Treat the display as a *surface*, not a screen

- **Multi-device mosaic** — three displays side-by-side become a 720×240 panorama (one
  weather forecast spanning all three).
- **Stereo display** — left clock, right calendar, automatically grouped.
- **Wall mosaic mode** — N displays show one big render tiled.
- **"Frame" mode** — daytime show photos from `media_source`, switch to dashboard on
  motion; basically a HomeKit-style smart photo frame.

### C. Reactive, situational UI

- **Context views** — declarative rule: *if* listening to music → show media view; *if*
  someone at the door → camera view; *if* nobody home → away view.
- **Calendar-aware** — 5 minutes before a meeting, switch to a "join now" view with the
  link as a QR code.
- **Cooking mode** — recipe steps + timer triggered by `input_boolean.cooking`.
- **Sleep mode** — between 22:00–07:00, view becomes a dim clock + only "alarm-worthy"
  notifications.

### D. Bigger expressive primitives

- **Card widget** — render an arbitrary Lovelace card (entities, glance, sensor) at
  240px (#38).
- **QR widget** — Wi-Fi guest password, calendar link, recipe URL.
- **Mini-map widget** — draw a coordinate (zone.home + person.tracker) on a static map
  background.
- **Sparkline + value** — already there as chart, but combined inline ("CPU 42% ▁▂▄▆█").
- **Stack/group widget** — a slot that hosts multiple widgets and rotates them on a
  sub-cycle (sub-views inside a slot).
- **Comparison widget** — today vs. yesterday energy, this week vs. last.

### E. Authoring & onboarding

- **"Describe-it" assistant** — natural-language → view config (LLM with the user's
  exposed entities as context).
- **Template gallery** — pre-built JSON views with images, "install this" button.
- **Widget playground** — sandbox in the panel where users tinker with one widget on
  fake data before committing.
- **Inline tooltips & "what changed?" diff** when a user edits a slot.
- **Smart defaults** — if user picks `sensor.cpu_percent`, default to gauge_ring with
  primary value; if `sensor.electricity_price`, default to chart.

### F. Reach beyond GeekMagic

- **Render-to-browser** — same engine outputs `image.*` entity; users can put it in
  Lovelace as a 240×240 card (already partial, formalize it).
- **Render-to-e-paper** — TRMNL, Inkplate, Kindle integrations sharing the renderer.
- **Render-to-MQTT** — publish PNGs to an MQTT topic so anything can subscribe.
- **Web preview public link** (signed URL) — share a "hey look at my display" link.
- **Companion ESPHome firmware reference** — co-developed open firmware that exposes
  buttons/sensors/touch for richer interactivity.

### G. Reliability & ops

- **Health widget** — show coordinator state, last-render time, last-upload latency.
  When it fails, the display itself reports the failure (rather than going stale and
  silent).
- **Per-device throttling** — auto-detect Pro vs. Ultra and tune defaults (Pro can take
  faster pushes, ESP8266 needs caution; addresses #96 wear concern).
- **CI image-diff** — every PR renders the full sample matrix and posts a visual diff;
  prevents regressions like #20, #48, #75, #85, #95.
- **"Heartbeat"** — tiny 1-pixel checksum corner so you can verify the latest frame is
  the latest frame.

### H. Surprising / unconventional

- **Voice-triggered view** — HA voice assistant: "Claude, show me the kitchen" →
  switches view on the closest GeekMagic.
- **Presence-aware brightness** — auto-dim when the room is empty; auto-brighten when
  motion detected.
- **NFC tag → view** — tap a phone on a sticker to swap the device's view.
- **"Boredom mode"** — every N minutes, randomly pick a delightful but useful view from
  a curated set, so the display always feels fresh.
- **Display-as-a-service in HA Cloud** — render-in-cloud so RPi 3 owners aren't bound by
  Pillow CPU.
- **Timer/Pomodoro widget** with audible alert via media player.
- **Achievement notifications** — "you've saved 12 kWh today" pulled from Energy
  dashboard.
- **Secondary "second-screen"** — when watching media on a TV, the GeekMagic shows
  show/episode/duration (Plex, Jellyfin, Sonos).

---

## 6. Suggested priorities to discuss next

Not a roadmap — a starting point for "where would you bet first?":

1. **P1 + O3** — kill the long tail of fragmentation/reliability (#37, #59, #89, #108,
   #112, #25, #36) before adding more features. Bad first-runs cap growth.
2. **OP2.1 Templates everywhere + OP2.4 typography** — single biggest expressiveness
   unlock; closes a dozen feature requests at once (#10, #31, #60, #73, #91, #92, #94).
3. **OP4.1/OP4.2/OP4.3 reactive views & native-FW coexistence** — turns the device from
   passive ambient → contextual surface. The differentiator vs. ESPHome forks.
4. **OP5.1 view marketplace** — flywheel: more visible community → more retention →
   more contributions.
5. **OP1.3 prebuilt templates / starter packs** — collapses time-to-first-delight.

---

## 7. Open questions worth answering with users

- Do users actually want **interactive control** (display-as-input via Pro buttons) or
  is glanceable-only enough?
- Is the **240×240 constraint** something to lean into (specialty design language) or
  something to abstract away (works on anything)?
- How much of the userbase is on **stock** vs. **bvweerd's firmware** vs. **ESPHome**?
  (Drives Tier-1 vs. Tier-2 platform decisions.)
- Are recurrent reliability complaints (#26, #36, #111) caused by HA, by GeekMagic
  hardware, or by the integration's polling pattern? Field telemetry would settle this.
- Is **multi-device** actually used much, or is the average deployment one display?
  (Affects the value of mosaic/group features.)
