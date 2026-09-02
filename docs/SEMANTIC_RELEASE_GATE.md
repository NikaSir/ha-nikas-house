# Semantic release gate

The semantic release gate prevents a generated Lovelace dashboard from being released merely because its YAML is syntactically valid.

A release candidate is compared using its deterministic `RenderTrace v1`, not raw YAML formatting.

## Reviewable semantics

RenderTrace records:

- manifest ID, version and dashboard path;
- contract IDs and versions;
- source inventory snapshot IDs;
- renderer-engine SHA-256;
- views: title, path and order;
- modules: instance, contract, order, title, renderer and columns;
- rendered roles: label, semantic key, entity ID, domain and primary action;
- canonical dashboard SHA-256.

This allows changes to be classified independently of YAML whitespace or key formatting.

## Semantic diff

```bash
ha-contract-ui diff render \
  release/baseline.meta.json \
  .generated/candidate.meta.json
```

Use `--json` to emit `RenderDiff v1`. Use `--check` to return exit code `2` when a valid semantic change exists.

Typical classifications include:

- `binding:rebound` — a role resolves to a different Home Assistant entity;
- `action:action_changed` — the primary interaction changed;
- `view:path_changed` — navigation changed;
- `module:columns_changed` — visible layout changed;
- `renderer:engine_changed` — rendering-engine source changed;
- `renderer:unclassified_render_drift` — canonical dashboard output changed without a corresponding view/module/binding/action or engine change.

The last case is always critical because the trace cannot explain the rendered change.

## Fail-closed gate

```bash
ha-contract-ui gate render \
  release/baseline.meta.json \
  .generated/candidate.meta.json
```

Exit codes:

- `0` — no semantic changes, or an exact approval matches them;
- `1` — invalid input, schema or approval document;
- `3` — valid semantic changes are present but not approved.

Any semantic change blocks by default regardless of severity.

## Exact approval

The gate never creates or silently updates approvals. After reviewing the semantic diff, a reviewer may create a `RenderApproval v1` document:

```json
{
  "api_version": "nikas.home-assistant/render-approval/v1",
  "baseline_dashboard_sha256": "<64 hex characters>",
  "candidate_dashboard_sha256": "<64 hex characters>",
  "semantic_diff_sha256": "<64 hex characters>",
  "reviewed_by": "reviewer",
  "rationale": "Reviewed and accepted the intended semantic changes."
}
```

Then run:

```bash
ha-contract-ui gate render \
  release/baseline.meta.json \
  .generated/candidate.meta.json \
  --approval approvals/candidate.json
```

The approval is accepted only when all three hashes exactly match the current baseline, candidate and semantic diff. Any later candidate, renderer or semantic change makes the approval stale and the gate blocks again.

## Release rule

A green schema/test run is necessary but not sufficient for a production dashboard release. The semantic gate must also allow the candidate, and the reviewed baseline must remain available for rollback.
