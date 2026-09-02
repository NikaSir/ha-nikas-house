# Specialized Panel Shell Standard v1.3

> **SUPERSEDED:** use `NIKAS_SPECIALIZED_PANEL_UI_STANDARD.md` v1.7 for Header plaques, source-aware return, safe-area ownership, stable rendering, optional indicators, typography, viewport behavior, Bottom Tab Bar geometry and brand requirements.

**Status:** Required
**Applies to:** all specialized Home Assistant panels in Home Assistant NikaS
**Primary acceptance viewport:** iPhone Pro Max, portrait
**Reference field implementation:** Stark SolarPower UI 0.5.6

## 1. Purpose

All specialized panels use one application-shell contract while keeping domain UI in the owning integration/project.

Canonical hierarchy:

```text
HOME ASSISTANT / DEVICE SAFE AREA
↓
SPECIALIZED PANEL HEADER                     native scale
  └── ☰ HA menu | centered title | action
↓
DEVICE SELECTOR (peer devices only)          native scale
↓
EXACTLY ONE ZOOMABLE WORK VIEWPORT           user scale
  └── domain / selected-device content
↓
BOTTOM TAB BAR                               native scale
↓
DEVICE BOTTOM SAFE AREA / HOME INDICATOR
```

There is no permanent zoom toolbar in the standard shell.

## 2. Ownership invariant

The shared shell owns:

- effective safe-area handling;
- Header geometry and menu behavior;
- persistent peer-device selector placement;
- exactly one zoom viewport;
- zoom gesture lifecycle and reset feedback;
- fixed Bottom Tab Bar geometry;
- shell clearances.

The domain/integration owns:

- entities, telemetry and status semantics;
- commands exposed through Home Assistant APIs/entities;
- content cards and visualizations;
- peer-device labels/data;
- contextual artwork;
- secondary parent/drill-down navigation inside the work area.

**Migration rule:** do not combine shell migration with unrelated domain redesign.

## 3. Safe-area contract — consume exactly once

The effective safe-area inset must have one owner.

Use Home Assistant/browser safe-area values:

```css
env(safe-area-inset-top, 0px)
env(safe-area-inset-right, 0px)
env(safe-area-inset-bottom, 0px)
env(safe-area-inset-left, 0px)
```

If Home Assistant or custom-panel registration already supplies/consumes the effective inset, the panel must not add the same inset again.

Required:

- Header below Dynamic Island/notch;
- Bottom Tab Bar above Home Indicator;
- no duplicate blank top band;
- no device-model constants such as `top: 47px`;
- no independent safe-area padding inside views/cards.

## 4. Header

Canonical mobile Header:

```text
┌─────────────────────────────────────┐
│  ☰           PANEL TITLE          ⟳ │
│              subtitle               │
└─────────────────────────────────────┘
```

### 4.1 Permanent left control

The left control is always the **Home Assistant main-system menu**.

The canonical frontend action is dispatching:

```js
new CustomEvent("hass-toggle-menu", {
  bubbles: true,
  composed: true,
})
```

The control MUST NOT be:

- browser Back;
- a hard-coded parent-route Back;
- an integration-specific drawer/menu;
- a device/domain action.

If a panel needs navigation to its logical parent, place that navigation **inside the work area** as domain/application content.

### 4.2 Title and right rail

Required:

- title geometrically centered relative to viewport;
- at most one primary global/shell action on right;
- symmetric rail geometry when practical;
- touch targets approximately 44×44 pt or larger;
- concise one-line primary title on reference iPhone;
- optional subtitle for model/context/version;
- no decorative device/brand icon beside Header title;
- no oversized duplicate title immediately below Header.

Header, menu button and right action remain at native scale.

### 4.3 Async global action

For an action such as Refresh:

- call only stable Home Assistant integration APIs/entities;
- do not call vendor API directly from frontend;
- suppress repeat activation while busy;
- expose progress/result feedback when practical;
- feedback must not shift title centering.

## 5. Persistent peer-device selector

When one application owns multiple peer physical devices, Device Selector sits directly below Header and remains at native scale.

Required:

- fixed peer order;
- selection never reorders peers;
- selected peer persists across Bottom Tab changes;
- compact health indication for non-selected peers is allowed;
- detailed primary content belongs only to selected peer;
- do not append full duplicate content for all peers;
- newly discovered peers should reuse the same application template where possible.

Subordinate zones/channels/components are not peer devices merely because they are selectable.

## 6. Exactly one zoomable work viewport

There is exactly one work viewport per specialized-panel instance.

Native-scale layers outside it:

- Home Assistant chrome;
- Header / HA menu / right action;
- persistent peer-device selector;
- Bottom Tab Bar;
- safe-area surfaces;
- transient `Масштаб 100%` reset confirmation.

Responsive layout is selected before zoom:

```text
actual viewport
→ mobile/tablet/desktop composition
→ selected peer/domain context
→ user zoom
```

### 6.1 Idempotent shell lifecycle

Shell installation/reconciliation MUST be idempotent across full renders, optimized renders and unrelated Home Assistant state updates.

It must never create:

- nested zoom viewports;
- duplicate gesture handlers;
- duplicate reset confirmation elements;
- abandoned wrappers/blank space;
- progressive content shrinking;
- duplicate Header/selector/navigation layers.

Preferred architecture keeps shell topology stable and updates domain content inside the existing viewport.

## 7. Zoom interaction

Zoom behavior is defined by `SPECIALIZED_PANEL_ZOOM_STANDARD.md` v1.3.

Shell requirements:

- normal method is two-finger focal-point pinch;
- permanent `− / % / +` controls are not rendered;
- two-finger double tap resets zoom and scroll to 100%/origin;
- pinch ending in 97–103% snaps to exactly 100%;
- reset/snap briefly shows `Масштаб 100%`;
- stored scale is isolated per panel and peer device when applicable.

## 8. Bottom Tab Bar

Primary in-app navigation with 3–5 destinations uses one full-width fixed Bottom Tab Bar.

Required:

- edge-attached to viewport bottom;
- full-width on mobile;
- fixed while work content scrolls;
- not a floating card/pill;
- respects effective bottom safe area;
- common geometry across specialized applications;
- icon + short readable label;
- active tab unambiguous;
- comfortable touch targets;
- final content scrolls fully above the bar.

If more than five destinations are needed, use secondary hierarchy rather than shrinking labels/touch targets.

Bottom reserve belongs to shell:

```text
Bottom Tab Bar content height
+ effective bottom safe area
```

Bottom Tab Bar remains at native scale.

## 9. Visual/state semantics inside work area

Cross-panel rules proven in Stark field review:

- first useful viewport prioritizes current operating state;
- normal factual measurements use neutral typography;
- green/amber/red are reserved for confirmed semantic state;
- `unknown`, `unavailable`, stale or untrusted source never appear healthy;
- decorative/context artwork remains separate from live values/state layers;
- do not invent unsupported runtime, watts, alarms or reserve estimates;
- native Home Assistant more-info/history is reused when it provides required factual detail.

## 10. Render performance

Integration-owned panels should avoid rebuilding the complete Shadow DOM for unrelated Home Assistant entity churn when practical.

Any optimization must preserve:

- exactly one shell/work viewport;
- selected peer;
- active Bottom Tab;
- current zoom state;
- entity/more-info bindings;
- global action feedback.

## 11. Field acceptance

Acceptance order:

1. iPhone Pro Max portrait in Home Assistant Companion App;
2. smaller iPhone portrait;
3. tablet;
4. desktop.

Verify at minimum:

- safe area not missing or doubled;
- `☰` triggers the standard HA menu;
- title/right action geometry;
- selector fit where applicable;
- first useful domain state density;
- Bottom Tab clearance;
- focal-point pinch/pan;
- double two-finger reset;
- 97–103% snap;
- `Масштаб 100%` feedback;
- no shell duplication after repeated HA updates;
- peer switching preserves context/scale;
- explicit unreliable states;
- native more-info/global-action behavior.

## 12. Non-conforming patterns

Prohibited:

- Header under notch/Dynamic Island;
- double safe-area consumption;
- Back or integration drawer in permanent left Header rail;
- menu icon that does not trigger `hass-toggle-menu`;
- permanent on-screen zoom controls;
- nested zoom wrappers or repeated gesture installation;
- zooming Header/selector/Bottom Bar with content;
- whole-page/browser zoom;
- floating primary Bottom Tab Bar;
- hard-coded device safe-area constants;
- live state baked into decorative images;
- unrelated domain refactor during shell migration.

## 13. Acceptance criteria

A specialized panel shell is accepted only when:

1. safe area is consumed exactly once;
2. Header stays below cutout;
3. left rail is HA menu and dispatches `hass-toggle-menu`;
4. title remains geometrically centered;
5. persistent peer selector, when present, is native-scale/fixed-order/selected-device-only;
6. exactly one zoom viewport exists;
7. repeated HA updates do not duplicate shell topology;
8. pinch affects only work content;
9. no permanent zoom buttons are shown;
10. double two-finger tap resets scale/scroll;
11. 97–103% pinch snaps to 100%;
12. reset confirmation is shown briefly;
13. Bottom Tab Bar is fixed/full-width/safe-area-aware/native-sized;
14. final content clears Bottom Tab Bar;
15. responsive layout is selected before zoom;
16. target-device field acceptance passes.

## Project rule

> Specialized panels own domain content, not application chrome. The shell owns safe areas, permanent Home Assistant `☰` menu, peer context placement, exactly one gesture-driven zoom viewport and the fixed Bottom Tab Bar. No permanent zoom toolbar is used.
