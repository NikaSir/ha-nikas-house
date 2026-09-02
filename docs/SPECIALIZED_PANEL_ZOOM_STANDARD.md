# Specialized Panel Zoom Standard v1.3

> **SUPERSEDED:** `NIKAS_SPECIALIZED_PANEL_UI_STANDARD.md` v1.7 is the only normative zoom/scroll source. Transform panning at 100% is retired; 100% uses native vertical scrolling with `x = y = 0`.

**Status:** Required
**Applies to:** all specialized Home Assistant panels in Home Assistant NikaS
**Architecture:** shared specialized-panel shell
**Reference field implementation:** Stark SolarPower UI 0.5.6

## 1. Purpose

Specialized panels must allow the user to enlarge their working content without scaling or disturbing Home Assistant chrome, persistent device context or fixed navigation.

The field-tested baseline is now **gesture-only zoom**. Permanent on-screen zoom buttons are not used in the standard shell.

## 2. Zoom scope

Only the panel work area scales.

The following remain at native scale:

- Home Assistant chrome/sidebar;
- specialized Header;
- permanent Home Assistant main-menu button;
- right Header action;
- persistent peer-device selector;
- fixed Bottom Tab Bar;
- safe-area surfaces;
- transient zoom-reset confirmation.

Canonical hierarchy:

```text
HEADER / HA MENU                 native
DEVICE SELECTOR (optional)      native
ONE ZOOMABLE WORK VIEWPORT      scaled content
BOTTOM TAB BAR                  native
```

Browser/page zoom is not a conforming implementation.

## 3. Required touch interaction

Every touch-capable specialized panel MUST support:

- two-finger pinch-to-zoom;
- focal-point preservation around the midpoint between the fingers;
- one-finger pan/scroll of enlarged content;
- two-finger double tap to reset zoom and scroll position;
- automatic snap to exactly 100% when a pinch ends between 97% and 103%;
- local persistence of the selected scale.

Permanent `− / percentage / +` controls are **not part of the standard shell**.

## 4. Exactly one zoom viewport

A specialized-panel instance must contain exactly one active zoom viewport.

Shell installation/reconciliation MUST be idempotent across:

- full renders;
- optimized/partial renders;
- unrelated Home Assistant state changes;
- selected-device changes;
- Bottom Tab changes;
- reconnect/reload cycles.

It must never create:

- nested zoom wrappers;
- duplicate gesture handlers;
- duplicate reset notifications;
- abandoned wrappers with blank space;
- progressive content shrink/growth caused by repeatedly scaling an already scaled wrapper.

When migrating a legacy implementation, old wrappers may be normalized/unwrapped before one clean canonical viewport is installed. In steady state the shell topology remains stable.

## 5. Pinch behavior

At the start of a two-finger pinch capture:

- initial touch distance;
- initial effective scale;
- content coordinate under the touch midpoint.

While the gesture changes:

```text
new scale = initial scale × current distance / initial distance
```

After scale changes, adjust scroll offsets so the same content coordinate remains under the current midpoint as closely as the browser permits.

Required:

- pinch affects only work content;
- normal one-finger scroll remains available;
- enlarged content pans horizontally and vertically when necessary;
- pinch must not accidentally execute domain actions;
- tap/long-press/more-info behavior remains valid after scaling.

## 6. Scale limits and snap-to-100

Default limits:

- minimum: **75%**;
- maximum: **200%**;
- default: **100%**.

When pinch finishes and the resulting scale is within:

```text
97% ≤ scale ≤ 103%
```

the shell fixes the scale to **exactly 100%**.

The snap uses the normal reset path so the viewport returns to the canonical 100% origin rather than preserving an almost-zero residual offset.

A different snap band is non-conforming unless a future standard revision changes it.

## 7. Two-finger double-tap reset

Two quick two-finger taps on the work viewport reset:

```text
scale = 100%
scrollLeft = 0
scrollTop = 0
```

The gesture recognizer must distinguish a tap from pinch/pan by using a short duration and movement tolerance so normal pinch gestures are not misclassified.

The reset gesture is presentation-only and must not execute any domain command.

## 8. Reset confirmation

After an explicit two-finger double-tap reset or automatic 97–103% snap, show a short non-interactive confirmation:

```text
Масштаб 100%
```

Requirements:

- transient, approximately one second;
- does not reserve permanent layout space;
- does not block pointer/touch interaction;
- remains native-sized rather than scaling with domain content;
- exposed as polite status feedback where practical (`role=status`, `aria-live=polite`).

## 9. Persistence scope

Zoom is local UI preference, never Home Assistant entity state.

### Single-device panel

```text
panel-id + client
```

### Multi-peer-device panel

Use separate preference for each peer when the panel supports multiple peer devices:

```text
panel-id + peer-device-id + client
```

Switching peer device restores that peer's stored scale. Changing Bottom Tab within the same peer preserves scale.

If local storage is unavailable, zoom continues to work for the current session.

## 10. Responsive layout interaction

Order is fixed:

```text
actual viewport
→ mobile/tablet/desktop composition
→ selected peer/domain content
→ user zoom
```

Zoom must not change responsive breakpoint selection or trigger repeated mobile/desktop switching.

## 11. Rerender behavior

Home Assistant may deliver frequent unrelated state updates. A conforming implementation preserves one viewport and the current scale across those updates.

Preferred implementation:

- shell DOM remains stable;
- domain content is updated/replaced inside the existing viewport;
- or one known viewport is reconciled by a stable identity.

Repeated blind wrapping after every render is prohibited.

## 12. Interaction with Device Selector

Persistent peer-device selector remains outside the zoom viewport and at native scale.

When peer selection changes:

- selector geometry/order remains unchanged;
- current Bottom Tab remains selected;
- work content switches in place;
- peer-scoped scale is restored.

## 13. Safety and semantics

Zoom must not change:

- entity selection;
- semantic inventory;
- health/stale thresholds;
- `unknown` / `unavailable` handling;
- routes;
- confirmations;
- domain commands;
- source-trust semantics.

## 14. Acceptance criteria

A specialized panel conforms when:

1. two-finger pinch works on phone/tablet;
2. pinch preserves the gesture midpoint;
3. enlarged content pans/scrolls to all regions;
4. no permanent on-screen zoom controls are rendered;
5. two-finger double tap resets scale and scroll to 100%/origin;
6. pinch ending at 97–103% snaps to exactly 100%;
7. reset/snap briefly shows `Масштаб 100%`;
8. exactly one work viewport exists after repeated HA state updates;
9. no nested wrappers, duplicate handlers or progressive shrinking occurs;
10. Header, HA menu, Device Selector and Bottom Tab Bar remain native scale;
11. scale persists per panel/client and per peer device where applicable;
12. responsive composition is selected before zoom;
13. tap/long-press/more-info behavior remains valid.

## 15. Default contract

```yaml
shell:
  zoom:
    enabled: true
    min: 0.75
    max: 2.00
    default: 1.00
    pinch: true
    focal_point: gesture_center
    pan_when_zoomed: true
    controls: none
    reset_gesture: two_finger_double_tap
    reset_scroll: origin
    snap_to_100_percent_range: [97, 103]
    reset_feedback: "Масштаб 100%"
    persist: per_panel_per_client
    peer_device_scope: per_device_when_present
    viewport_count: 1
    install: idempotent
```

## Project rule

> Exactly one zoomable work viewport. Two-finger focal-point pinch is the normal zoom interaction. Permanent zoom buttons are not used. Two-finger double tap resets zoom and scroll to 100%, 97–103% snaps to 100%, reset is briefly confirmed, and scale persists locally per panel/device.
