# Repository scope: main House only

## Decision

`NikaSir/ha-nikas-house` owns only the new main **Дом** overview. It must not implement or register Rooms, Actions, Infrastructure or any detailed control panel.

The existing configured YAML dashboards remain the working baseline in Home Assistant. The split does not rename, overwrite, unload or delete them.

## Ownership matrix

| Route | Status | Rule |
|---|---|---|
| `/dashboard-house` | Existing YAML | Preserve unchanged |
| `/dashboard-house-v13/home` | Parallel NikaS House route | Register only when free |
| `/dashboard-house-v12/home` | Existing `contract_generated_ui` route | Preserve unchanged |
| `/dashboard-rooms-v11/rooms` | Autonomous Rooms route | External verified link |
| `/dashboard-actions/home` | Existing YAML | External link until a separate Actions repository is accepted |
| `/dashboard-infrastructure/overview` | Existing YAML | External link until a separate Infrastructure repository is accepted |
| Device-specific routes | Separate integrations | Always externally owned |

## Preservation

The exact source state for this split is `ha-contract-generated-ui` `0.38.2`, commit
`f5bff8145eef20475cf3e3f9f470e94d564b72fc`.

This repository may clean only its own packaged contracts, manifests, frontend bundles and fallback registrations. It must never clean private inventory, snapshots, generated history or Home Assistant YAML dashboard files.

## New detailed-panel workflow

1. Create a dedicated repository when work on a detailed panel starts.
2. Give it a unique preview route that does not collide with the existing YAML route.
3. Keep its contracts, manifest, frontend, assets and tests inside that repository.
4. Test the preview on the target phone while the YAML dashboard remains available.
5. Change the House navigation URL only after the new panel is accepted.
6. Retain the YAML panel as a rollback path until its retirement is explicitly approved.

The House migration follows the same rule: the autonomous panel appears as
`Дом · новая` only on the dedicated v13 route. An occupied v13 route blocks
registration instead of causing another route to be selected.

## Cross-repository boundary

- Navigation by explicit URL is allowed.
- Copying an approved UI pattern at development time is allowed.
- Importing JavaScript, Python, assets or manifests from another panel repository at runtime is forbidden.
- One repository must never unload or replace a route owned by another repository or by Lovelace YAML.
