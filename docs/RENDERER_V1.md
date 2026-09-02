# Lovelace renderer v1

Renderer v1 turns validated contracts, verified semantic inventory and a panel manifest into deterministic Home Assistant Lovelace YAML.

## Binding model

A manifest never contains a concrete Home Assistant `entity_id`. Each module explicitly maps a contract role to a semantic inventory key:

```yaml
bindings:
  status: infrastructure.router.status
  traffic: infrastructure.router.traffic
```

The renderer resolves those keys through verified inventory and rejects missing keys, missing required roles and domain mismatches.

## Contract presentation

A renderable v1 contract declares:

- a user-facing `label` for every role;
- at least one allowed Home Assistant domain for every role;
- exactly one explicit primary action per role;
- `presentation.renderer: tiles_v1`;
- an explicit tile `columns` count;
- `role_order` containing every contract role exactly once.

## Interaction safety

Renderer v1 uses Home Assistant core Heading, Grid and Tile cards only.

For every generated Tile card it writes all interactive actions explicitly:

- `tap_action` — derived from the role's contract action;
- `hold_action` — always `more-info`;
- `double_tap_action` — always `none`;
- `icon_tap_action` — explicitly mirrors the primary contract action;
- `icon_hold_action` — always `more-info`;
- `icon_double_tap_action` — always `none`.

This prevents Home Assistant card defaults from silently introducing controls that were not declared by the contract.

`toggle` is fail-closed in v1 and is allowed only for `light`, `switch` and `input_boolean` domains. Service actions are not rendered by v1. Navigation targets must be absolute paths.

## Deterministic output

From the repository root:

```bash
ha-contract-ui render manifests/example.yaml .generated/example.yaml
```

The command writes:

- deterministic Lovelace YAML;
- a sibling `.meta.json` RenderTrace containing manifest and contract versions, source snapshot IDs, resolved semantic bindings and the SHA-256 of canonical dashboard content.

The trace contains no generation timestamp, so identical validated inputs produce identical output bytes.

## Scope boundary

Renderer v1 is a structural and interaction-safe renderer. It does not yet deploy dashboards into Home Assistant and it does not translate contract state rules into conditional styling. In particular, it never converts `unknown` or `unavailable` into a healthy state.
