# House Overview Specialized Panel v2

> This file describes the current implementation snapshot. Compliance requirements are in `NIKAS_SPECIALIZED_PANEL_UI_STANDARD.md` v1.9.

NikaS House `0.1.0` transfers the accepted House visual state scene, titled `Дом сейчас`, into an autonomous integration-owned Home Assistant panel. The visible composition and state semantics come from `ha-contract-generated-ui` `0.38.2` at `f5bff81`.

## Route and ownership

The parallel acceptance route is:

```text
/dashboard-house-v13/home
```

If that route is already owned, the integration leaves it untouched and does not
register an alternative. The preserved `/dashboard-house-v12/home` owner is never
replaced. The sidebar title is `Дом · новая`. The v13 panel uses Home Assistant
`panel_custom` and the self-contained `nikas-house-panel` web component. The House
panel is no longer exported under `lovelace.dashboards:` and does not depend on a
Sections view or `custom:nikas-house-main-hero` being constructed by Lovelace after a cold
refresh.

The deterministic House YAML and RenderTrace remain available as review evidence, but they are not the runtime host of the overview.

## Native shell

The specialized shell owns three native-scale layers:

1. Header below the effective top safe area;
2. one fixed work viewport;
3. the global `Дом / Помещения / Действия / Инфра` Bottom Tab Bar above the effective bottom safe area.

The permanent left Header control is only the Home Assistant menu button `☰`. It dispatches the standard composed and bubbling `hass-toggle-menu` event. It is never Back, an integration drawer or a device command.

## Hybrid native-scroll / transform canvas

The work viewport contains exactly one transform target. Its complete durable presentation state is:

```text
{ scale, x, y }
transform: translate3d(x, y, 0) scale(scale)
```

The implementation never uses CSS `zoom`, `scrollLeft` or horizontal native scrolling as a canvas position engine. At 100% the work viewport deliberately owns ordinary native vertical scrolling; transform panning is enabled only above 100%.

Interaction contract:

- at 100%, one finger performs ordinary vertical scrolling and `x = y = 0` remain fixed;
- above 100%, one finger pans only along axes where scaled content exceeds the viewport;
- two fingers scale around their midpoint;
- coordinates are clamped to measured scaled-content bounds;
- the final transform persists locally per panel/client;
- two-finger double tap resets to `{scale:1,x:0,y:0}`;
- a completed pinch at 97–103% snaps to exact 100%;
- reset/snap briefly shows `Масштаб 100%` outside the transform;
- the second finger cancels pending hold interaction;
- post-gesture clicks are briefly suppressed;
- ordinary taps and stationary holds remain available when no gesture is recognized.

The shell and live scene DOM are created once. Home Assistant state updates patch only existing text, attributes and classes inside the live House content, so telemetry cannot recreate the background, fixed chrome, viewport or transform target. The optional two-level connection/freshness indicator is intentionally absent from `Дом сейчас`.

## Visual and semantic layers

1. **Decorative asset** — `frontend/assets/house-hero-photo-day-v3.webp` is local, portrait-oriented and contains no entity ids or live readings.
2. **Live scene** — `frontend/nikas-house-hero.js` renders current values and semantic state colors.
3. **Specialized shell** — `frontend/nikas-house-overview.js` owns Header, transform canvas, gestures and Bottom Tab Bar.
4. **Semantic source** — the backend resolves only verified private `SemanticInventory` roles and sends a data-only panel config.
5. **Navigation** — all detail routes come from `PanelManifest + NavigationContract`; the frontend invents no subsystem paths.

## Truthfulness rules

- `unknown` and `unavailable` never become green/normal.
- The three House phase sensors are upstream of the LIDER PS7500W-30 stabilizers. Their status follows the stabilizer passport: normal in the nominal `150–265 V` range, warning in the extended working `125–275 V` range, emergency outside it. Downstream sensors, once verified, use the separate ГОСТ `198–242 V` policy and are never inferred from upstream phases.
- Sectional-gate and entrance-door outlines use only their physical access sensors.
- The window outline remains a conservative aggregate cue, not a fabricated mapping to a pictured physical window.
- Unsupported runtime, power, alarm or reserve values are never invented.

## Release acceptance

- the selected unowned House route opens after a cold app refresh without a Lovelace configuration error;
- `☰` opens the native Home Assistant menu;
- Header and Bottom Tab Bar remain at fixed screen coordinates and native-sized while only the work viewport scrolls;
- exactly one viewport and one transform target survive repeated telemetry updates;
- native vertical scroll at 100%, bounded enlarged pan, pinch, two-finger reset, 97–103% snap and local persistence work in the iOS Companion App;
- all four lower utility cards remain visible and reachable;
- gestures do not activate detail navigation or Home Assistant interactions accidentally.
- telemetry, clock updates and upward/downward scrolling do not flash or recreate the scene.
