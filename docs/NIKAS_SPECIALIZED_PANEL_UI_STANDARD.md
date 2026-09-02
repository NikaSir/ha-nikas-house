# NikaS Specialized Panel UI Standard v1.9

**Status:** REQUIRED
**Canonical source:** `NikaSir/ha-nikas-house`
**Applies to:** every integration-owned specialized Home Assistant panel
**Primary acceptance viewport:** iPhone Pro Max, portrait
**Reference shell implementation:** Stark SolarPower / UPS
**Reference Header surface and controls:** S8 OMNI
**Reference connection/freshness plaque:** S8 OMNI
**Reference typography and domain status treatment:** LIDER
**Required navigation companion:** `docs/NIKAS_PANEL_NAVIGATION_CONTRACT.md`

This document supersedes every earlier shell, Header, zoom, scrolling and Bottom Tab Bar rule. Historical documents remain useful only where they do not conflict with this standard.

## 1. Ownership and topology

```text
HEADER                                      native scale
DEVICE SELECTOR (peer devices only)         native scale
ONE WORK VIEWPORT                           scroll/zoom owner
BOTTOM TAB BAR                              native scale
```

- Only the work area scales.
- Header, peer selector and Bottom Tab Bar never scale or move with content.
- Exactly one zoom viewport may exist per panel instance; nested wrappers are prohibited.
- Shell reconciliation is idempotent across redraws and Home Assistant state updates.
- The effective iOS safe area is consumed exactly once.
- On phones the panel owns a height-locked application shell. The outer Home Assistant page must not become the scrolling surface: only the work viewport scrolls, so Header and Bottom Tab Bar stay at fixed screen coordinates.
- Prevent scroll chaining from the work viewport into Home Assistant's outer document. A sticky element inside the scrolling/transformed subtree does not satisfy the fixed-chrome requirement.
- Short views fill the available work row rather than shrinking the application shell and pulling either menu toward their content.

## 2. Header — S8 OMNI reference surface and geometry

The complete upper application menu copies the S8 OMNI Header, not merely its title typography. The Header surface, menu plaque, center return plaque and optional right action are one visual system.

- Grid: `52px minmax(0,1fr) 52px`; on very narrow screens: `48px minmax(0,1fr) 48px`.
- Minimum height: `62px`; phone target: `60px`, plus the effective top safe area.
- Header side padding is at least `12px` and consumes the effective left/right safe area once. The top inset is consumed by the Header once; no child plaque adds a second safe-area offset.
- The Header strip uses the S8 OMNI surface: background `color-mix(in srgb,var(--primary-background-color) 97%,transparent)`, bottom border `1px solid color-mix(in srgb,var(--divider-color) 70%,transparent)`, and `backdrop-filter:blur(18px) saturate(130%)`. The iOS-prefixed equivalent may be added.
- The Header strip remains a persistent mounted layer. Blur, border and background must not be toggled or remounted during scroll, pinch, telemetry changes or tab switches.
- A solid integration-brand color, a transparent strip that exposes moving work content, or a card-white strip disconnected from `var(--primary-background-color)` is non-conforming.
- Title remains geometrically centered regardless of side actions.
- Primary title: `23px`, weight `800`, one line; `21px` on very narrow phones.
- Secondary/version line: `14px`, weight approximately `560`, `var(--secondary-text-color)`; `13px` on very narrow phones.
- The permanent left action is only Home Assistant system menu `mdi:menu`; it dispatches bubbling/composed `hass-toggle-menu`.
- At most one panel-global action occupies the right rail. Refresh uses `mdi:refresh`.
- Menu and refresh copy the S8 OMNI side plaques exactly: `44px × 44px`, `16px` radius, `1px solid color-mix(in srgb,var(--divider-color) 72%,transparent)` border, `var(--card-background-color)` background, `0 7px 20px rgba(23,45,76,.08)` shadow and a `25px` `ha-icon` glyph.
- Menu glyph uses `var(--primary-text-color)`; refresh uses `var(--primary-color)`.
- Disabled global action may reduce opacity, but its plaque geometry and reserved rail remain unchanged so title centering never moves.
- A transparent refresh rail, a borderless side action, a locally selected integration color or mismatched menu/refresh geometry is non-conforming.
- Back, an integration drawer, a device command or a decorative brand icon is prohibited in the permanent left rail.

### Center title plaque — return to the source NikaS base panel

- The geometrically centered two-line title is a persistent clickable plaque and the sole standard return control from a specialized panel to the NikaS base interface.
- The first line is the current specialized-panel name. The second line is the interface version in the exact form `UI vX.Y.Z`.
- The whole plaque is one semantic `button` and copies the S8 OMNI reference geometry and tone exactly; it retains geometric centering between the side rails.
- Default geometry: `justify-self:center`, `min-width:min(290px,100%)`, `max-width:100%`, `min-height:44px`, `padding:5px 14px`. On narrow phones it uses `min-width:0; width:100%; padding-inline:8px` so the plaque fills the available center grid column without moving the side rails.
- Reference surface: `1px` border `color-mix(in srgb,var(--primary-color,#03a9d9) 24%,var(--divider-color,#dfe3e8))`, `16px` radius, background `color-mix(in srgb,var(--primary-color,#03a9d9) 5%,var(--card-background-color,#fff))`, and shadow `0 5px 16px rgba(23,45,76,.06)`.
- Pressed state: background primary mix `13%`, border primary mix `42%`, shadow `0 2px 7px rgba(23,45,76,.05)`; an optional subtle `scale(.985)` response is allowed. Focus-visible uses a `2px` primary-color outline with `2px` offset.
- The focus state and pressed response are mandatory and remain visibly distinct from the default state.
- A transparent title, a plain text label without the S8 OMNI surface, a white-only card surface, a wider `460px` desktop plaque forced into the phone Header, or a locally chosen integration color is non-conforming.
- An arrow, chevron, a separate `Назад` label and `history.back()` are prohibited.
- When a specialized panel is opened from `/dashboard-house-v13/home`, `/dashboard-actions/home` or `/dashboard-infrastructure/overview`, it returns to that same base panel. Permitted sub-routes are normalized according to the required navigation contract.
- The base shell records the source route in the same click/keyboard handler, immediately before changing location to the specialized panel. Ambient shell synchronization and telemetry updates must not refresh the hand-off timestamp. The common one-shot hand-off key is `sessionStorage["nikas.specialized.source_route.v1"]`; `return_to` or `from` query parameters may be used as an explicit hand-off.
- The specialized panel captures and validates the route once, persists its accepted route for that panel/client, and does not recalculate it during telemetry updates. Only same-origin routes rooted at `/dashboard-house-v13`, `/dashboard-actions` and `/dashboard-infrastructure` are accepted.
- Capture precedence is: explicit `return_to`/`from`, one-shot session hand-off, saved route for that specialized panel, safe same-origin referrer, configured `parent_route`, then the repository-defined safe base-panel fallback.
- Navigation is explicit Home Assistant navigation: `history.pushState()` followed by a `location-changed` event. Browser history is never the routing contract.
- The title plaque, its accepted route and its click handler are mounted with the fixed Header and survive tab switches, polling, loss/recovery and every state-only patch.

## 3. Peer-device selector

- Use a selector only for peer physical devices of the same integration, for example `UPS Интернет / UPS Котёл`; a zone, channel or functional subsection is not automatically a peer device.
- It remains directly below Header, outside the work viewport and at native scale.
- Selected peer persists across tabs and owns its own locally persisted scale/position state.
- Hiding a selector on an aggregate view is allowed when all peers are already visible, but the same selector subtree is retained for single-peer views.

## 4. Work viewport at 100%

At exactly `scale = 1`:

- `x = 0` and `y = 0` are invariant;
- one-finger transform panning is disabled;
- normal native vertical scrolling is enabled;
- horizontal scrolling is disabled;
- the canvas cannot be pulled sideways, below the top origin or beyond its real lower edge;
- clicks, hold-to-more-info and vertical scrolling start without a gesture delay;
- stored transforms are normalized to `{scale:1,x:0,y:0}` before display.

The former rule that one-finger transform panning also provides vertical movement at 100% is retired.

## 5. Zoom and enlarged pan

- Pinch uses two fingers and preserves the focal midpoint.
- Range is `75–200%`.
- Permanent zoom buttons are prohibited.
- Pinch ending within `97–103%` snaps to exactly 100% and origin.
- Two-finger double tap resets scale, transform and native scroll to 100%/origin and briefly shows `Масштаб 100%`.
- Every route to 100% — explicit two-finger reset, automatic `97–103%` snap, invalid stored-state normalization or programmatic reset — uses one canonical reset operation: `scale=1`, `x=0`, `y=0`, `scrollLeft=0`, `scrollTop=0`, then persists the normalized 100% state.
- Scale persists locally per panel/client and per selected peer device where applicable.
- One-finger transform panning is enabled only when `scale > 1`.
- Each axis is enabled only when scaled content exceeds the viewport on that axis.
- Translation is clamped to factual content edges; exposing empty canvas is prohibited.
- Resize, orientation change, content reflow, peer switch and tab change re-run bounds clamping.
- A tab change returns native scroll to the top and removes invalid translation; stored scale may remain.
- A second finger cancels pending more-info; post-gesture synthetic clicks are briefly suppressed, while intentional stationary hold still opens native more-info.
- Pinch and two-finger reset must not open history, a graph or more-info.

## 6. Bottom Tab Bar — UPS reference geometry

- One fixed, edge-attached, full-width bar; never a floating card or pill.
- It remains outside the work viewport and above the Home Indicator.
- Background: `var(--card-background-color)`; top divider and a subtle upward shadow.
- Insets: approximately `6px` top and `calc(6px + env(safe-area-inset-bottom))` bottom, with safe left/right padding.
- All destinations have equal-width columns; 3–5 primary tabs are supported.
- Tab touch target minimum height: `52px`.
- Tab radius: approximately `16px`; compact internal padding and approximately `3px` icon/label gap.
- Icons are MDI through `ha-icon`, never text characters; canonical glyph size is `28px`.
- Labels are one line, approximately `12px`, weight `700`, readable and ellipsized only when necessary.
- Inactive content uses `var(--secondary-text-color)`.
- Active icon/label use `var(--primary-color)` and an approximately 11% primary-color background, without a second shadow.
- Navigating between tabs restores the work area to the page start before interaction resumes.
- A short view must not move the bar. A long view must scroll its final control/card fully clear of the bar and Home Indicator.

## 7. Typography envelope

- Meaningful user-facing text stays within `12–25px` inclusive.
- `12px` is the minimum for captions, state freshness, navigation labels, chips and compact secondary values.
- `25px` is the maximum for a prominent live value or compact hero heading. Larger display typography is not part of the phone form baseline.
- The Header is governed by its explicit `23/14px` wide and `21/13px` narrow pairs above.
- `9–10px` is allowed only for redundant, non-interactive schematic annotations whose meaning is already conveyed elsewhere. It is prohibited for statuses, controls, navigation, entity names, measurements and required explanations.
- A layout that needs meaningful text below `12px` must be recomposed instead of shrinking the type.

## 8. Optional connection and freshness indicator — S8 OMNI reference

The two-level indicator is introduced only by an explicit product request. It is not a mandatory shell element. In particular, it is absent from `Дом сейчас` and StarLine until separately requested.

### Semantics

- The first line describes the actual data path: `Локально`, `Облако`, `Резерв`, `Нет связи` or `Нет данных`.
- `Онлайн` is not used: it duplicates `Локально`/`Облако` and hides the transport path.
- Tuya Local and Zigbee delivered through local MQTT are `Локально`; Tuya cloud and other remote cloud APIs are `Облако`.
- Local transport also includes a local LAN/API, local MQTT, Modbus and SNMP path that does not require an external vendor service.
- `Резерв` means a known fallback path is actively supplying data, not merely that fallback capability exists.
- The second line describes freshness only: `Данные актуальны`, `Данные устарели` or `Нет данных`.
- Transport and freshness are independent. For example, `Облако · Данные устарели` is valid; stale data must not be relabelled as a transport outage without evidence.
- A failed current poll makes preserved telemetry `Данные устарели`. Unless a domain documents another justified threshold, a sample also becomes stale after three normal polling intervals; it becomes current again only after a new successful sample is accepted.

### Placement and geometry

- The canonical placement copies S8 OMNI: upper-right of the first operational Hero/card, in the same heading row as the current-state title. The plaque belongs to the work viewport, not the fixed Header, and therefore scales with work content.
- Use a two-column heading row with the state/title in `minmax(0,1fr)` and the plaque in an intrinsic right column. On normal phone widths the plaque receives enough room for its longest label; the S8 OMNI reference reserves approximately `minmax(168px,44%)`.
- At extremely narrow widths where the title and plaque cannot remain readable, stack the row and align the plaque to the start. Shrinking required text below the typography envelope or allowing overlap is non-conforming.
- Surface layout: `display:grid`, columns `10px minmax(0,1fr)`, vertically centered, `11px` column gap.
- Minimum height: `58px`; padding: `12px 14px`; radius: `18px`; `white-space:nowrap`; `max-width:100%`.
- Default surface before state coloring: `var(--card-background-color)` background, `1px solid color-mix(in srgb,var(--divider-color) 72%,transparent)` border and `0 4px 14px rgba(0,0,0,.055)` shadow.
- Status lamp: `10px × 10px`, fully inside the plaque, circular, never moved outside the rounded surface.
- Text block is a stable vertical flex column with `3px` gap. Main line: `16px/700`, line-height approximately `1.05`. Freshness line: `13px/600`, line-height approximately `1.05`.
- The plaque is sized from the longest permitted transport/freshness pair. It must not change width, height or alignment when state changes.

### State surfaces and colors

- `Локально` and `Облако`: lamp and main line use `var(--success-color,#43a047)`; background is an `11%` success-color mix with `var(--card-background-color)`; border is a `30%` success-color mix with `var(--divider-color)`.
- `Резерв`: lamp and main line use `var(--warning-color,#f6a623)`; background is a `10%` warning-color mix with `var(--card-background-color)`; border is a `30%` warning-color mix with `var(--divider-color)`.
- `Нет связи`: lamp and main line use `var(--error-color,#db4437)`; background is a `10%` error-color mix with `var(--card-background-color)`; border is a `30%` error-color mix with `var(--divider-color)`.
- `Нет данных`: lamp and main line use `var(--disabled-text-color,var(--secondary-text-color))`; background is an `8%` secondary-text-color mix with `var(--card-background-color)`; border is a `28%` secondary-text-color mix with `var(--divider-color)`.
- A current freshness line uses `var(--secondary-text-color)`. `Данные устарели` uses `var(--warning-color,#f6a623)` at weight `600`. `Нет данных` uses `var(--secondary-text-color)`.
- Color is always accompanied by text. Saturated full fills, arbitrary product colors and a green surface for `unknown`, `unavailable`, stale or untrusted data are prohibited.

### Rendering behavior

- Flashing, pulsing, saturated full fills and repeated entrance animations are prohibited.
- The indicator is a stable DOM subtree. State updates patch only text, classes, ARIA label and state color variables; they never remount the plaque, Hero, panel or fixed shell and never animate layout geometry.
- The plaque remains structurally present when changing among local/cloud/reserve/offline/no-data states so that telemetry changes cannot make the page flash or shift.

## 9. Stable rendering and flicker prevention

- Header, peer selector, one viewport, one work canvas, persistent background and Bottom Tab Bar are mounted once per panel instance.
- A `hass` setter or telemetry timer must patch existing text, attributes, classes and CSS variables. Reassigning the panel or card `shadowRoot.innerHTML` for routine telemetry is prohibited.
- Tabs and peer-device views use lazy DOM caching. Returning to a visited view reattaches the same view subtree; it must not rebuild the application shell.
- A structural configuration change may replace only the affected work-view subtree. It must not create a second viewport or discard the fixed chrome.
- The stored transform is applied before a newly selected work view becomes visible. Background images and large compositor layers are not recreated during scroll, telemetry refresh or indicator updates.
- Rendering is coalesced to at most one animation frame, and unchanged values do not write the DOM.
- Wrapping a full redraw in `requestAnimationFrame`, or delaying it until after scrolling, is still a full redraw and is non-conforming.
- Keys, element order and child topology remain stable for state-only changes. Conditional status copy uses stable placeholders or targeted insertion rather than whole-tree replacement.
- Exact changing telemetry age is not a structural key. An unchanged image does not receive the same `src` again.
- `backdrop-filter`, masks, `will-change` and containment may be used only on persistent layers; toggling or remounting them during scroll is prohibited because it can flash in iOS WebView.
- No polling loop may rebuild the active tab. Time-only displays patch their own text nodes.
- A full-screen loading frame is allowed only during initial mount. Later loss, staleness and recovery patch the mounted content in place.

## 10. Data truth and command safety

- A panel renders facts only from Home Assistant state objects, integration-owned APIs/coordinators or the Home Assistant entity/device registries. Frontend code must not invent entity IDs, raw device datapoints, capabilities, samples or success states.
- Entity mapping is supplied by the integration, panel configuration or registry discovery. A hard-coded entity ID is allowed only when it is an explicit, tested part of that integration's public contract.
- Missing, malformed, `unknown` and `unavailable` data are rendered explicitly and never receive a healthy tone. A preserved last-known sample remains visibly stale until a newer successful sample is accepted.
- Derived values identify their factual inputs and fail closed when those inputs are absent. The UI must not replace an unknown value with zero, an optimistic default or fabricated history.
- Read-only panels remain read-only. A refresh action may request new telemetry but must not masquerade as a device command.
- A write action is allowed only through a registered integration service or a discovered Home Assistant entity capability. It is disabled when its target or capability is unavailable, prevents duplicate submission, awaits completion and exposes busy/error feedback without inventing success.
- Secrets, raw credentials and vendor tokens never enter panel configuration, DOM attributes, logs or frontend bundles.
- Every repository declares its data source and command policy in `.nikas-ui-standard.json` and verifies the product-specific mapping in tests.

## 11. Production bundle and version coherence

- Every specialized panel has exactly one shipped JavaScript `production_entrypoint`. `module_url` points only to that entrypoint with deterministic cache busting tied to the current UI version.
- The production entrypoint is autonomous: it contains no runtime `import`, dynamic `import()` or `export`, and it does not load a previous UI module, remote script, stylesheet or CDN dependency. Local versioned artwork may remain a separately packaged asset.
- Historical source layers may be composed at build time only when the generated entrypoint contains one active shell, one active Header-return implementation and no superseded zoom or navigation engine.
- `runtime_files` lists only files executed by Home Assistant. Build inputs are declared separately as `build_source_files`; documentation and test fixtures are never presented as runtime.
- Generated bundles are deterministic. CI regenerates them and fails on a diff, or invokes an equivalent `--check` mode that fails when the tracked bundle is stale.
- The visible `UI vX.Y.Z`, configured `ui_version`, panel manifest, panel contract, registration/cache key and current web-component name describe the same release. A runtime change that affects behavior increments the UI version and cache key.
- The production bundle is syntax-checked directly. Tests reject runtime imports, duplicate current component registration and more than one active shell/viewport.
- Styles required for the shell are bundled or shipped locally with the same deterministic version policy. Runtime network failure must not remove Header, navigation or core state presentation.

## 12. Brand and repository identity

- Every integration repository ships a recognizable integration brand asset.
- A packaged `custom_components/<domain>/brand/icon.png` is mandatory; it is the minimum HACS brand asset and must not be an empty placeholder.
- `brand/logo.png`, `brand/dark_icon.png` and `brand/dark_logo.png` are required when the mark or wordmark is not legible in both themes.
- Brand files use the integration package layout expected by Home Assistant/HACS and are included in distribution checks.
- README starts with the same recognizable project/integration identity; repository and installed integration must not present unrelated marks.
- Header does not display the brand icon; it is for repository/HACS/HA identity, sidebar/launcher and suitable domain cards.
- Changed raster assets use deterministic cache/version handling where served by the panel.

## 13. Required automated guards

Repository tests or static checks must verify:

1. exactly one work/zoom viewport;
2. no permanent scale controls;
3. `hass-toggle-menu` and `mdi:menu` in the left rail;
4. the Header strip and both side actions use the S8 OMNI reference surface, border, blur, dimensions and shadow;
5. Bottom Tab icons use `ha-icon` and canonical size;
6. no horizontal movement and no transform pan at 100%;
7. axis-aware overflow bounds above 100%;
8. clamp after resize/tab/peer changes;
9. brand `icon.png` exists in the shipped integration package;
10. meaningful typography stays within `12–25px`, subject only to the documented schematic exception;
11. routine telemetry cannot replace the shell, viewport, canvas, background or Bottom Tab Bar;
12. an optional connection indicator, when requested, uses the canonical transport/freshness vocabulary, S8 OMNI geometry and exact state-tinted surface percentages;
13. the center title is a two-line `44px`+ semantic button, contains no arrow or separate Back label and retains geometric centering;
14. every reset path normalizes and persists `{scale:1,x:0,y:0}` and native scroll origin;
15. source-route capture follows `NIKAS_PANEL_NAVIGATION_CONTRACT.md`, uses the three canonical base entry routes, writes the common session hand-off at outbound click/keyboard time, consumes it once, performs explicit HA navigation and contains no `history.back()`;
16. the hand-off route and timestamp are a required pair, reject missing, invalid, expired and future timestamps, and are both removed before candidate selection;
17. the production entrypoint is the only runtime file, is autonomous and is reproducible from its declared build inputs;
18. UI version, manifest/contract, component registration and cache key stay coherent;
19. unknown/unavailable data and product command policy are explicit and fail closed;
20. JavaScript syntax, package validation, HACS and Hassfest pass.

Each repository also maintains `docs/NIKAS_SPECIALIZED_PANEL_COMPLIANCE.md` (or an equivalent explicit record). Unimplemented runtime behavior is recorded as `GAP`, never assumed to pass from documentation alone.

## 14. Mandatory phone acceptance

- long diagnostics pages scroll vertically at 100%;
- 100% cannot move horizontally or be pulled away from the top origin;
- enlarged content pans only on necessary axes and never exposes empty field;
- release preserves clamped position without rebound;
- pinch never causes content snap-back;
- card activation does not become accidental pan;
- Header, selector and Bottom Tab Bar remain stationary at every scale;
- the upper menu visually matches S8 OMNI: persistent 97% primary-background strip, divider, blur and three aligned plaques below Dynamic Island;
- both Header side buttons are visible matching `44px × 44px` plaques;
- the centered title plaque shows the panel name and exact `UI vX.Y.Z`, returns to each of the three originating NikaS base panels and uses the configured safe fallback after a direct open;
- Bottom icons and labels match the Stark SolarPower visual scale;
- integration/repository icon is present and recognizable in installed/distribution surfaces.
- a requested connection indicator visually matches S8 OMNI: `58px` minimum height, `18px` radius, internal `10px` lamp, stable two-line text and state-specific surface without geometry movement;
- repeated telemetry, indicator transitions, tab changes and upward/downward scroll produce no full-screen flash or white frame;
- scrolling the work area never moves Header, peer selector or Bottom Tab Bar;
- short views do not pull either menu inward, and long views expose their last control above the Bottom Tab Bar;
- at least ten consecutive tab switches produce no blank frame, lost map/image or duplicated viewport;
- loss/recovery changes telemetry and any enabled indicator in place; preserved samples are visibly stale;
- `Дом сейчас` and StarLine contain no unrequested two-level connection indicator.
- repeated telemetry and tab changes do not change the captured Header return destination or replace its click handler.
- an unavailable target cannot be commanded and never flashes an optimistic success state;
- a missing or stale hand-off timestamp falls back safely instead of reusing an old source route.

## 15. Publication

- NikaS panel and integration work is published through traceable commits, branches and pull requests.
- GitHub Releases are not used.
- Automatic release tags are not used as a publication gate or update channel. An internal integration/UI version does not require a Git tag.
- A pull request remains draft until automated checks pass and the real-phone acceptance items above are ready for user verification.
