# Integration-owned dashboard UI standard v1.4

> **SUPERSEDED FOR SHELL/ZOOM/NAVIGATION:** `NIKAS_SPECIALIZED_PANEL_UI_STANDARD.md` v1.7 is normative. Domain guidance below remains valid only where it does not conflict with v1.7.

**Status:** Required
**Applies to:** all integration-owned specialized dashboards in Home Assistant NikaS
**Primary target:** iPhone Pro Max, portrait
**Related standards:** Shell v1.3 · Zoom v1.3 · Frontend Delivery v1.1
**Reference field implementation:** Stark SolarPower UI 0.5.6

## 1. Purpose

Integration-owned dashboards behave as mobile applications inside Home Assistant rather than unrelated Lovelace pages.

The integration keeps ownership of domain data/actions/presentation. Shared NikaS standards define shell behavior, visual semantics and release constraints without creating a runtime dependency on `ha-nikas-house`.

## 2. Application hierarchy

Single-device:

```text
SAFE AREA
↓
HEADER: ☰ | centered title | global action
↓
ONE ZOOMABLE DOMAIN WORK VIEWPORT
↓
BOTTOM TAB BAR
```

Multi-peer-device:

```text
SAFE AREA
↓
HEADER: ☰ | centered title | global action
↓
PERSISTENT DEVICE SELECTOR
↓
ONE ZOOMABLE SELECTED-DEVICE WORK VIEWPORT
↓
BOTTOM TAB BAR
```

There is no permanent zoom toolbar.

## 3. Header

### 3.1 Left side — Home Assistant main-system menu

The permanent left rail is always the Home Assistant system menu.

Frontend implementations dispatch the standard event:

```js
this.dispatchEvent(new CustomEvent("hass-toggle-menu", {
  bubbles: true,
  composed: true,
}));
```

The left rail must not be:

- browser Back;
- parent-route Back;
- an integration-specific menu/drawer;
- a device/domain action.

If the application needs a parent-route action, place it inside the working area as explicit application content.

### 3.2 Center title

- geometrically centered on viewport;
- concise one-line application title on reference iPhone;
- optional short subtitle for model/context/version;
- no duplicated oversized title below Header;
- no decorative device/brand icon beside Header title.

### 3.3 Right side — one global action

At most one primary application-level action such as Refresh/overflow appears in right rail.

Async action rules:

- call an existing Home Assistant entity/API owned by integration;
- no direct vendor API bypass from frontend;
- block repeat activation while busy;
- show progress/success/error feedback where practical;
- feedback must not shift centered title.

Header/menu/right action stay at native scale.

## 4. Safe-area ownership

Safe area is consumed exactly once at application boundary.

Required:

- Header below Dynamic Island/notch;
- Bottom Tab Bar above Home Indicator;
- no blank band from duplicate top inset;
- no per-view device-specific padding hacks;
- Companion App field verification after shell/registration changes.

## 5. Bottom Tab Bar

For 3–5 primary sections use one full-width, edge-attached, fixed Bottom Tab Bar.

Required:

- fixed at viewport bottom;
- full-width on mobile;
- not a floating card/pill;
- safe-area-aware;
- icon + short readable label;
- active item unambiguous;
- comfortable one-hand touch targets;
- final work content scrolls fully above it.

Reference tab sets:

- HO-SC-8W: `Обзор · Зоны · Программы · Диагн.`
- S8 OMNI: `Обзор · Уборка · Станция · Сервис · Диагн.`
- Stark SolarPower: `Обзор · ИБП · История · События · Диагн.`
- Keenetic Hero 4G+: `Обзор · WAN/LTE · Трафик · Диагн.`; separate Failover workflow may justify five tabs.

## 6. Peer Device Selector

If one application serves multiple peer physical devices, Device Selector is a separate persistent context layer.

Required:

- immediately below Header on all primary sections;
- native scale;
- fixed peer order;
- selected peer never reorders to first;
- selected peer survives Bottom Tab changes;
- compact health dot/badge allowed;
- selector is not a telemetry panel;
- primary detail belongs only to selected peer;
- newly discovered peer reuses same template when integration model permits.

Subordinate channels/zones/components are not peer devices by default.

### Stark reference

```text
☰ | Stark SolarPower | Refresh
↓
[ UPS Интернет ] [ UPS Котёл ]
↓
selected UPS work viewport
↓
Обзор | ИБП | История | События | Диагн.
```

Scale may persist separately per UPS.

## 7. Working-area zoom

The standard mobile presentation is **gesture-only**.

Required:

- exactly one zoom viewport;
- two-finger focal-point pinch;
- pan/scroll when enlarged;
- no permanent `− / % / +` controls;
- two-finger double tap resets scale and scroll to 100%/origin;
- pinch ending at 97–103% snaps to exactly 100%;
- reset/snap briefly shows `Масштаб 100%`;
- scale stored locally per panel and peer device where applicable;
- responsive layout selected before zoom;
- repeated HA updates never create nested wrappers/duplicate handlers/progressive shrink.

See `SPECIALIZED_PANEL_ZOOM_STANDARD.md` v1.3.

## 8. First useful viewport

Prioritize:

1. current operating/trust state;
2. primary visual/status summary;
3. important live metrics/actions;
4. essential subsystem state rows;
5. detail below.

Critical state must not be pushed below fixed navigation by oversized chrome or decorative content.

## 9. Visual-state semantics

### Neutral factual values

Normal measurements use neutral typography.

Semantic color is reserved for confirmed meaning:

- green — healthy/normal;
- amber/orange — warning/degraded;
- red — fault/critical;
- grey/neutral — unknown/unavailable/not confirmed.

### Trust before last known state

Source failure/stale/untrusted state overrides a last reported normal mode in overview status.

`unknown`, `unavailable`, stale or untrusted source never mean healthy.

### Backend owns validated thresholds

When integration exposes a validated semantic entity such as `data_stale`, frontend consumes it instead of duplicating backend threshold logic.

### No invented values

Do not fabricate unsupported runtime, watts, alarms, reserve estimates or entity facts merely to fill UI.

## 10. Contextual visual assets

Panel may use rich hero/context artwork when useful.

Rules:

- panel-critical artwork ships locally;
- no external CDN dependency;
- no Base64 image payload when normal local asset is suitable;
- decorative/background art contains no live values/status text;
- product/device art, SVG paths, labels, values and status overlays remain separate runtime layers;
- background may switch with selected peer context;
- assets are optimized and version-cache-busted.

Stark SolarPower is reference: transparent UPS PNG + separate network/boiler WebP context plates + dynamic HTML/SVG live layers.

## 11. Entity/action behavior

- domain commands use stable public Home Assistant APIs/entities of owning integration;
- no raw vendor/API bypasses from frontend;
- Header, Device Selector and Bottom Tab Bar never execute unrelated domain actions;
- long press on factual entity-backed elements should open native Home Assistant more-info where useful;
- native HA history/more-info is preferred over duplicate history UI unless custom history adds material value.

## 12. Render stability/performance

Avoid complete Shadow DOM rebuilds for unrelated HA entity churn when practical.

Any optimization must preserve:

- exactly one shell/work viewport;
- selected peer;
- active Bottom Tab;
- current zoom state;
- gesture/reset handlers exactly once;
- entity/more-info bindings;
- global action feedback.

Nested wrappers, duplicate handlers/controls or progressive shrink are release-blocking defects.

## 13. Frontend delivery

Follow `SPECIALIZED_PANEL_FRONTEND_DELIVERY_STANDARD.md` v1.1:

- one stable production entry;
- historical versioned modules are build-time history, not runtime import chain;
- deterministic build when generated;
- UI-version cache busting;
- local packaged assets;
- panel registration/manifest parity;
- CI syntax/rebuild/asset checks.

## 14. Mobile-first acceptance

Order:

1. iPhone Pro Max portrait in HA Companion App;
2. smaller iPhone portrait;
3. iPad/tablet;
4. desktop.

Field checks:

- no missing/doubled safe-area;
- left `☰` opens native HA menu via `hass-toggle-menu`;
- title/right action geometry;
- Device Selector fit/stability;
- first useful state density;
- Bottom Tab clearance;
- pinch focal point and pan;
- two-finger double-tap reset;
- 97–103% snap;
- transient `Масштаб 100%` confirmation;
- no shell duplication after repeated HA state updates;
- peer switching restores expected context/scale;
- unreliable states remain explicit;
- more-info/global action feedback works.

Desktop render alone is not sufficient acceptance evidence.

## 15. Conceptual panel metadata

```yaml
panel:
  id: subsystem
  path: /dashboard-subsystem
  owner: integration_domain
  shell:
    standard_version: "1.3"
    safe_area_owner: application_once
  header:
    left_control:
      type: home_assistant_system_menu
      event: hass-toggle-menu
    title_alignment: viewport_center
    right_action: refresh
  navigation:
    primary: full_width_fixed_bottom_tab_bar
  zoom:
    pinch: true
    controls: []
    min: 0.75
    max: 2.0
    reset_gesture: two_finger_double_tap
    snap_to_100_percent_range: [97, 103]
    persistence: local_per_panel_and_device
```

## 16. Application-specific guidance

### Stark SolarPower

Use the field-tested 0.5.6 behavior as reference: HA menu left, Refresh right, fixed UPS selector, selected-device-only five-view content, gesture-only zoom/reset/snap, contextual local assets and strict trust semantics.

### S8 OMNI

HA menu left; one robot+station system means no peer selector unless multiple peer systems appear; five primary Bottom Tabs remain domain-owned.

### HO-SC-8W

HA menu left; irrigation zones are subordinate channels, not peer selector entries; keep four primary tabs and integration-owned write safety.

### Keenetic Hero 4G+

HA menu left; first viewport prioritizes active Internet/WAN/LTE/failover state; Ethernet/LTE are channels of one router, not peer devices.

## 17. Acceptance criteria

UI-complete means:

- native HA menu permanently left;
- centered title;
- safe area consumed once;
- Bottom Tab fixed/full-width/safe;
- peer selector correct when applicable;
- exactly one gesture-driven zoom viewport;
- no permanent zoom controls;
- double-tap reset and snap-to-100 work;
- reset feedback appears briefly;
- semantic colors/trust rules are correct;
- no unsupported values invented;
- local assets separate from live state;
- deterministic production frontend checks pass;
- target-device field acceptance passes.

## Project rule

> Integration-owned specialized dashboards are mobile applications inside Home Assistant: native HA system menu, centered Header, optional peer context, exactly one gesture-driven work viewport, fixed Bottom Tab Bar, factual state-first content, local layered assets, strict trust semantics and deterministic frontend delivery.
