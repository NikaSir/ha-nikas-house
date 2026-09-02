# Specialized Panel Frontend Delivery Standard v1.1

**Status:** Required for integration-owned specialized panels with custom frontend
**Canonical owner:** `NikaSir/ha-nikas-house`
**Reference implementation:** Stark SolarPower UI 0.5.6

## 1. Purpose

A specialized panel can be visually correct and still fail in the field because of stale modules, broken runtime imports, missing assets, duplicated shell installation or non-deterministic packaging.

This standard defines packaging, registration, cache identity, panel metadata and release gating. It does not own domain UI.

## 2. Ownership boundary

The integration owns:

- production frontend entry module;
- build-time source modules;
- local assets;
- panel registration;
- machine-readable panel manifest;
- frontend release CI.

CGUI owns the canonical shell/UI/delivery contracts. Conformance does not require a runtime dependency on CGUI.

## 3. One stable production entry

Each integration-owned specialized panel exposes exactly one production frontend entry to Home Assistant.

Examples:

```text
frontend/panel.js
frontend/panel-bundle.js
```

Historical/versioned source files may remain build-time history, but the browser must not depend on a runtime chain such as:

```text
v020.js → v021.js → v030.js → ...
```

## 4. Deterministic build

If the production entry is generated from multiple source files:

- build is reproducible from clean checkout;
- rebuilding without source changes produces no diff;
- source order is explicit;
- generated artifact is clearly marked;
- production self-contained bundle contains no runtime historical `import`/`export` chain;
- generated artifact is not manually edited.

## 5. Home Assistant registration

The integration registers one stable panel route and one production module URL.

Required:

- stable route;
- stable web-component name;
- module URL points to production entry;
- UI/build version participates in cache busting;
- static-path registration is deterministic across restart/reload;
- safe-area ownership agrees with Shell Standard v1.3;
- custom panel registration must not cause the frontend to consume the same safe-area inset twice.

## 6. Cache busting

Frontend UI release changes production module URL identity, preferably:

```text
/local-panel/panel-bundle.js?v=<ui-version>
```

Changed local assets should also use deterministic version/build query cache busting.

## 7. Local static assets

Panel-critical assets ship inside the integration package.

Recommended layout:

```text
custom_components/<domain>/
└── frontend/
    ├── panel-bundle.js
    └── assets/
        ├── device.png
        └── context.webp
```

Required:

- no external CDN dependency for critical art;
- no Base64 image payload when normal local asset is suitable;
- assets reachable through local integration static route;
- HACS packaging includes them;
- dimensions/quality optimized;
- cache invalidation is predictable.

## 8. Layered visual assets

Decorative/context art is not state storage.

Background images must not bake in current HA measurements, alarms, labels, power-flow state or availability.

Dynamic device art, SVG paths, badges, labels and values remain runtime layers whenever they encode current state.

## 9. Panel manifest

Integration-owned specialized panels should ship machine-readable metadata.

Reference fields:

```yaml
api_version: nikas.home-assistant/integration-panel/v1
id: subsystem
path: /dashboard-subsystem
owner: integration_domain
ui_version: 1.2.3
shell:
  standard_version: "1.3"
  safe_area_owner: application_once
header:
  left_control:
    type: home_assistant_system_menu
    event: hass-toggle-menu
  title_alignment: viewport_center
device_context:
  selector: optional
navigation:
  primary_navigation: full_width_fixed_bottom_tab_bar
zoom:
  scope: work_viewport
  pinch: true
  controls: []
  minimum_percent: 75
  maximum_percent: 200
  reset_gesture: two_finger_double_tap
  snap_to_100_percent_range: [97, 103]
  persistence: local_per_panel_and_device
frontend_delivery:
  mode: self_contained_bundle
  module: panel-bundle.js
  assets: []
  cache_busting: query_ui_version
  runtime_previous_version_imports: false
targets:
  primary: iPhone Pro Max portrait
```

Fields that do not apply may be omitted, but manifest and runtime registration/behavior must not contradict each other.

## 10. Manifest / registration parity

CI verifies agreement across:

- panel registration code;
- panel manifest;
- production entry filename;
- UI version/cache-busting value;
- declared static assets;
- permanent HA-menu event contract where encoded;
- declared zoom policy (`controls: []`, reset gesture, snap range) where encoded.

Mismatch is release-blocking.

## 11. Asset existence guard

Every declared asset must exist in shipped integration tree.

CI should fail for missing/unshipped/renamed assets or stale local URLs.

## 12. JavaScript validation

At minimum:

- production entry passes `node --check` or equivalent;
- source JS is syntax-checked when practical;
- self-contained bundle rejects prohibited runtime historical imports;
- deterministic rebuild parity passes when applicable.

HACS/Hassfest/repository validation remains required in addition to frontend checks.

## 13. Runtime shell stability guard

Production frontend release should include a smoke/regression check for shell topology when practical.

Critical invariants:

- exactly one zoom viewport;
- no permanent zoom toolbar;
- no duplicate gesture/reset listeners caused by rerender;
- permanent left Header control dispatches `hass-toggle-menu`;
- repeated relevant/unrelated state updates do not progressively shrink or duplicate content.

A static syntax check alone cannot prove these lifecycle properties.

## 14. Runtime dependency policy

Prefer standard Web Components/HTML/CSS/SVG and resources shipped by integration. Extra frontend dependencies require concrete benefit and compatibility/release plan.

## 15. Safe-area registration interaction

Panel registration options may alter effective viewport/safe area. Therefore registration and shell CSS must document one effective owner and field-check Companion App result.

Double top inset is a delivery defect as well as CSS defect.

## 16. Versioning

Integration version and Panel UI version may differ, but frontend release has unambiguous UI/build identity.

When UI behavior/assets change:

- bump UI/build cache identity;
- rebuild deterministic bundle;
- update panel manifest/registration parity;
- record user-visible changes in changelog/release notes.

## 17. Field release gate

Green CI is necessary but not sufficient.

Verify on target HA client:

- new production module loaded;
- expected asset version loaded;
- no stale prior UI;
- HA menu event works;
- safe areas correct;
- Bottom Tab correct;
- selector context correct;
- pinch/reset/snap behavior survives repeated state updates;
- exactly one viewport remains;
- no missing assets/CORS/network dependency.

## 18. Stark SolarPower reference

Stark demonstrates:

- local static route;
- stable `/dashboard-ups` route;
- one self-contained production bundle;
- UI-version query cache busting;
- historical UI modules as build-time inputs only;
- deterministic build script and CI guards;
- local PNG/WebP assets;
- machine-readable manifest including `hass-toggle-menu`, gesture-only zoom, double-tap reset and 97–103% snap.

## 19. Acceptance criteria

Delivery-complete means:

1. exactly one stable production entry;
2. version cache busting changes with release;
3. historical modules are not runtime chain;
4. deterministic rebuild passes when applicable;
5. JS syntax passes;
6. registration/manifest agree;
7. declared assets exist;
8. critical art is local;
9. live state remains outside decorative pixels;
10. safe-area ownership is not doubled;
11. manifest reflects gesture-only zoom/reset/snap and HA menu event;
12. shell lifecycle regression checks exist where practical;
13. HACS/Hassfest/repository checks pass;
14. target-device field check confirms intended frontend behavior.

## Project rule

> One integration-owned specialized panel = one stable production frontend entry, deterministic release identity, local packaged assets, manifest/registration parity and CI-enforced reproducibility/lifecycle invariants. Historical UI evolution is source history, not runtime architecture.
