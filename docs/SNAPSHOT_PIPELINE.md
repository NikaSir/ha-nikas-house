# Snapshot pipeline

`ha-nikas-house` uses a factual registry-snapshot stage before semantic inventory.

## Home Assistant capture

Press **Capture registry snapshot** in the integration. Home Assistant writes `nikas_house/snapshots/current.json` and rotates the prior changed snapshot to `previous.json`.

The snapshot excludes Home Assistant unique IDs and device identifiers. Its `snapshot_id` is derived from canonical scrubbed entity facts, so capture time or registry iteration order alone does not create drift.

## Semantic namespace

Semantic inventory keys use at least three dot-separated segments, for example:

- `access.garden.door`
- `power.main.voltage`
- `infrastructure.router.status`

A Home Assistant entity ID has the shape `domain.object_id` and therefore cannot satisfy the semantic-key grammar. This prevents a manifest semantic binding from silently becoming a direct entity binding.

## CLI

Validate a snapshot:

```bash
ha-contract-ui snapshot validate snapshots/current.json
```

Build inventory only from explicit verified bindings:

```bash
ha-contract-ui inventory build \
  snapshots/current.json \
  inventory/home.yaml \
  --bind access.garden.door=binary_sensor.example_door \
  --bind power.main.voltage=sensor.example_voltage
```

Every requested entity must exist in the supplied snapshot and must not be disabled. The resulting inventory records `verification: verified` and the source `snapshot_id`.

Compare registry facts:

```bash
ha-contract-ui diff snapshot snapshots/previous.json snapshots/current.json
```

Compare semantic bindings:

```bash
ha-contract-ui diff inventory inventory/before.yaml inventory/after.yaml
```

`--json` emits machine-readable changes. `--check` returns exit code 2 when valid inputs contain semantic changes.
