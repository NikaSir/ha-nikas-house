# Semantic inventory

Normalized, scrubbed inventory derived from verified Home Assistant registry/state snapshots.

The inventory maps factual Home Assistant entities/devices/areas to stable semantic roles consumed by contracts and manifests. It must preserve `unknown` and `unavailable` states as distinct reliability conditions and must not contain secrets or private `.storage` exports.
