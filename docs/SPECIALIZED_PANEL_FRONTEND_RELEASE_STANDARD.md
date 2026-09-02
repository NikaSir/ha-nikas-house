# NikaS Specialized Panel Frontend Delivery Standard v1.7

**Status:** required for every integration-owned Home Assistant specialized panel
**UI authority:** [`NIKAS_SPECIALIZED_PANEL_UI_STANDARD.md`](NIKAS_SPECIALIZED_PANEL_UI_STANDARD.md) v1.7

## Production artifact

One registered panel module equals one autonomous, integration-owned JavaScript bundle. The `module_url` target contains all project code needed to register and run the current panel. Runtime imports of previous panel versions or another NikaS repository are prohibited.

Modular development is allowed, but the build must produce one deterministic artifact with cache busting tied to the declared UI version. History belongs in reviewed Git commits and merged pull requests, not in browser import chains.

## Fixed shell acceptance

The production bundle must implement the v1.7 application shell:

- fixed Home Assistant menu Header, optional fixed peer-device selector, exactly one work viewport/canvas and fixed safe-area-aware Bottom Tab Bar;
- permanent left `mdi:menu` action dispatching bubbling/composed `hass-toggle-menu`; no permanent Header Back;
- centered two-line semantic title button with panel name plus version-only `UI vX.Y.Z`, visible focus/pressed states and validated return to the originating NikaS base panel;
- native vertical scrolling with `x = y = 0` at 100%, focal pinch at 75–200%, bounded one-finger pan only above 100%, 97–103% snap and stationary two-finger reset;
- shell mounted once, telemetry point-patched, visited views lazily cached and no full-screen flash;
- meaningful text at 12–25px and Bottom Tab Bar MDI icons/labels at 28px and 12px/700;
- optional connection/freshness indicator only when explicitly requested, using the canonical v1.7 vocabulary and status-tinted plaque;
- packaged repository/integration identity including `custom_components/<domain>/brand/icon.png`, minimum 256×256 RGBA.

## Required verification

Before merge, verify:

1. local-network and Home Assistant Cloud/Nabu Casa cold loads;
2. full Home Assistant restart followed by repeated panel opens;
3. no `Unable to load custom panel` or `Configuration error`;
4. no historical/runtime bundle chain;
5. Header menu, Refresh plaque, safe areas and fixed bottom navigation;
6. long native scrolling at 100% without horizontal or transform drift;
7. focal pinch, axis-bounded pan, snap/reset and native long-press/more-info behavior;
8. live telemetry, indicator transitions, tab/device changes and scroll without white frames or remount flicker;
9. JavaScript syntax, deterministic build, version/cache-busting consistency and repository CI;
10. real iPhone portrait acceptance.

## Publication workflow

Changes receive an explicit UI/integration version where applicable, a changelog entry and automated checks. NikaS work is published through commits, branches, pull requests and the accepted `main` state. GitHub Releases and automatic release tags are not created.
