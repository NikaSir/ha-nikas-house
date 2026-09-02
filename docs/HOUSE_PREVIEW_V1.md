# House preview v1

## Purpose

`house_home_v1` is the first staged renderer for migrating the Home Assistant NikaS `Дом` start page into NikaS House without replacing the current production dashboard before visual acceptance.

The primary target is **iPhone Pro Max in portrait orientation**. Tablet and desktop layouts are secondary adaptations.

## Safety boundary

Release `0.8.0` adds renderer capability only.

It does **not** automatically install a House contract, House panel manifest or private House SemanticInventory into `/config/nikas_house`, and therefore does not replace `/dashboard-house`.

The first live rendering is intentionally generated as a separate preview dashboard:

```text
/dashboard-house-preview/home
```

The current production `/dashboard-house` remains the rollback baseline until the preview is explicitly accepted.

## Protected start-page order

The preview preserves the approved start-page sequence:

1. `Дом сейчас`
2. `Активные события`
3. `Ресурсы`
4. `Отопление и ГВС`
5. `Автомобили`
6. `Ключевые точки доступа`

A renderer change must not reorder this prefix accidentally.

## Mobile composition

The House preview uses Home Assistant Sections with a two-column maximum and dense placement. Mobile cards are composed for fast portrait scanning rather than desktop information density.

The start page deliberately separates:

- **Дом сейчас** — immediate house state and top-level navigation;
- **Активные события** — abnormal/current events only;
- **Ресурсы** — household resource summaries, not engineering detail;
- **Отопление и ГВС** — operational heating summary;
- **Автомобили** — concise factual car state;
- **Ключевые точки доступа** — the approved 2×3 access set.

## Semantic binding rule

`house_home_v1` contains no production Home Assistant entity IDs.

The renderer consumes entity IDs only after the base renderer resolves semantic roles from verified private SemanticInventory. Missing required roles fail generation.

Aggregate chips such as open contacts, motion, lights, climate and cameras are built from resolved semantic role lists; the renderer does not discover production entities by guessing IDs.

The stale historical `zone.home` dependency is intentionally not restored or replaced by a guessed zone. Until a new presence contract is explicitly verified, the Family card is navigation-only.

## Reliability

`unknown` and `unavailable` are not healthy states.

The preview distinguishes unavailable/unknown data from factual normal state in its status templates. Loss of router, meter or other telemetry is not converted into a false normal condition.

## Domain ownership

ADR-001 applies to the House page.

The central page may show concise summaries and selected quick entry points, but detailed domain UX remains with its canonical owner:

- irrigation → `ha-ho-sc-8w` specialized dashboard;
- vacuum/station → `ha-s8-omni` specialized dashboard;
- router/WAN/LTE → `ha-keenetic-hero-4g` specialized dashboard;
- UPS → Stark SolarPower specialized dashboard.

Until those stable routes are released, House preview navigation may temporarily point to an existing house-wide summary route. No specialized route is invented.

## Activation sequence

1. Update NikaS House to `0.8.0` and restart Home Assistant.
2. Prepare the House activation sources outside the public repository:
   - public House UI contract;
   - public House preview panel manifest;
   - private verified `inventory/house.yaml` built from the current scrubbed registry snapshot.
3. Validate every House binding against the current registry snapshot and reject missing/disabled entities.
4. Copy the activation sources into `/config/nikas_house/` without modifying the existing infrastructure sources or private inventory files.
5. Press **Сгенерировать панели**.
6. Register/open the preview route separately from `/dashboard-house`.
7. Review the full page on iPhone Pro Max portrait.
8. Iterate on layout and semantics while the production House dashboard remains unchanged.
9. Only after explicit acceptance, plan the route migration from preview to `/dashboard-house`.

## Acceptance gate

The preview is not considered ready to replace the production Home start page until:

- protected section order is preserved;
- iPhone Pro Max portrait is readable without horizontal scrolling;
- normal state is compact and active events are visually dominant only when present;
- every displayed factual entity comes from verified inventory;
- `unknown` / `unavailable` are not shown as normal;
- no deprecated entity is silently replaced by a similar-looking entity;
- deep device/domain functions are not duplicated from integration-owned dashboards;
- the user explicitly accepts the live preview.

## Rollback

Before route migration, rollback is trivial: stop using `/dashboard-house-preview`; the existing `/dashboard-house` was never replaced.

After a future accepted migration, the last approved production House YAML remains the rollback baseline under the normal release process.
