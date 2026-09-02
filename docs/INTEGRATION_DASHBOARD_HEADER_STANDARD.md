# Integration dashboard header standard — superseded

**Status:** Superseded
**Superseded by:** `docs/INTEGRATION_DASHBOARD_UI_STANDARD.md` v1.4 and `docs/SPECIALIZED_PANEL_SHELL_STANDARD.md` v1.3

The former header-only standard is no longer normative by itself.

Current specialized-panel rules include:

- permanent Home Assistant main-system menu on the left;
- left control dispatches `hass-toggle-menu` with bubbling/composed event semantics;
- no permanent Back or integration-specific drawer in the left rail;
- parent navigation, if required, lives inside the work area;
- geometrically centered title and at most one global right action;
- effective safe area consumed exactly once;
- persistent peer-device selector below Header when applicable;
- exactly one gesture-driven zoom viewport;
- no permanent `− / % / +` zoom controls;
- two-finger double tap resets scale/scroll;
- 97–103% pinch snaps to 100% with brief `Масштаб 100%` confirmation;
- full-width fixed Bottom Tab Bar;
- strict `unknown` / `unavailable` / stale/source-trust semantics;
- stable deterministic production frontend delivery with local assets.

See:

- `docs/SPECIALIZED_PANEL_SHELL_STANDARD.md`;
- `docs/SPECIALIZED_PANEL_ZOOM_STANDARD.md`;
- `docs/INTEGRATION_DASHBOARD_UI_STANDARD.md`;
- `docs/SPECIALIZED_PANEL_FRONTEND_DELIVERY_STANDARD.md`;
- `docs/NIKAS_SPECIALIZED_PANEL_UI_STANDARD.md`.
