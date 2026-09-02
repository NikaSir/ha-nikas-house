# Contract core v1

The contract layer of `ha-nikas-house` separates UI semantics from concrete Home Assistant registry bindings.

## Data flow

`RegistrySnapshot → SemanticInventory + UIContract + PanelManifest → renderer`

The input document kinds are independently schema-validated before generation and are cross-checked again by the renderer.

## UIContract

API version: `nikas.home-assistant/ui-contract/v1`

A contract defines semantic roles, normal/event/unreliable state classes, explicit actions, renderer-facing requirements and safety invariants. It must not contain concrete Home Assistant registry identifiers.

Required safety invariants:

- `unknown_is_unreliable: true`
- `unavailable_is_unreliable: true`
- `invent_entity_ids: false`

Concrete `entity_id`, `device_id` and `area_id` keys are rejected recursively in contracts.

Renderable v1 contracts also define a user-facing label and allowed Home Assistant domains for every role, exactly one explicit action per role, and an explicit presentation order.

## SemanticInventory

API version: `nikas.home-assistant/semantic-inventory/v1`

The inventory is the only v1 input layer allowed to bind semantic keys to concrete Home Assistant entity IDs. Every binding must be marked `verification: verified`, and inventory metadata must state that the source was scrubbed before being committed.

Semantic keys use at least three dot-separated segments, for example `infrastructure.router.status`. This namespace cannot be confused with a Home Assistant `domain.object_id` entity ID.

The inventory is factual input. It does not convert `unknown` or `unavailable` into healthy states.

## PanelManifest

API version: `nikas.home-assistant/panel-manifest/v1`

A manifest declares dashboard paths, views, ordering and references to contract modules. A module binds contract roles to semantic inventory keys only:

```yaml
bindings:
  status: infrastructure.router.status
```

The semantic-key grammar requires at least three dot-separated segments, so a direct Home Assistant `domain.entity` value cannot satisfy the manifest schema.

Concrete `entity_id`, `device_id` and `area_id` keys are also rejected recursively in manifests.

## Validation

From the repository root:

```bash
python -m pip install -e '.[test]'
python -m generator validate .
python -m pytest -q
```

The installed console entry point is equivalent:

```bash
ha-contract-ui validate .
```

## Related executable layers

- `docs/SNAPSHOT_PIPELINE.md` — scrubbed Home Assistant registry capture, verified inventory build and semantic diff.
- `docs/RENDERER_V1.md` — deterministic Lovelace rendering and interaction-safety rules.
