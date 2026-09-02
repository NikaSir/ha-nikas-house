# ADR-001: Repository-owned specialized dashboards

**Status:** Accepted
**Updated:** 2026-08-31

## Context

The main House overview needs concise cross-domain state and stable links. Detailed
control panels need their own entity semantics, actions, assets, release cadence and
device-specific testing. Keeping both responsibilities in one repository increases
the chance that a change for one panel damages another.

Existing Lovelace YAML dashboards are already the operational fallback and must remain
untouched while replacements are evaluated.

## Decision

`ha-nikas-house` owns only the new main House overview at
`/dashboard-house-v13/home`. When that route already has an owner, registration is
blocked. The existing `/dashboard-house-v12/home` route remains owned by
`ha-contract-generated-ui` throughout acceptance.

Every new detailed panel is owned by a dedicated repository and integration. Its owner
is responsible for:

- route registration and non-destructive unload;
- information hierarchy and interaction semantics;
- entity/action mapping and failure handling;
- frontend bundle, assets, tests and releases;
- mobile acceptance on the target device.

This House repository may display verified summaries and explicit links to external
routes. A link is not ownership: it must not import, register, remove or patch the
destination panel.

## Route safety

- Existing Home Assistant YAML routes always win.
- A preview panel uses a unique route until accepted.
- Registration is allowed only when the intended route is unowned.
- Unload removes only a route recorded as registered by that integration.
- Browser history is not a navigation contract; routes are explicit.

## Repository boundary

Runtime JavaScript, Python, assets, contracts and manifests are never shared across
panel repositories. Approved visual rules may be copied at development time, but each
repository must be independently installable and releasable.

## Migration

The extraction baseline is preserved in `ha-contract-generated-ui` at commit
`f5bff8145eef20475cf3e3f9f470e94d564b72fc`. Existing YAML dashboards stay
available as rollback paths.
A House link changes to a new detailed panel only after that panel passes its own
acceptance checks.

## Consequences

The House codebase becomes smaller and safer to change. Detailed panels can evolve
independently, at the cost of maintaining explicit route contracts and separate
release pipelines.
