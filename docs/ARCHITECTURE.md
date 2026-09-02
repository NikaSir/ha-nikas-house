# Architecture

## NIKAS_HOUSE

The project treats Home Assistant dashboards as generated artifacts derived from explicit contracts and verified Home Assistant inventory.

### Stages

1. **Registry snapshot** — collect the factual Home Assistant entity/device/area registry state required by UI generation.
2. **Semantic inventory** — normalize source entities into stable semantic roles without changing their factual state.
3. **UI contracts** — define subsystem behavior, status semantics, actions, navigation, visibility and failure handling.
4. **Panel manifests** — declare which contract modules compose each dashboard/view.
5. **Generation** — render deterministic Lovelace YAML from contracts, inventory and manifests.
6. **Semantic diff** — compare meaning (entities, actions, navigation, visibility, safety behavior), not only YAML formatting.
7. **Validation** — reject unknown entity references, contract/schema violations and unsafe state handling.
8. **Release** — publish only validated generated output with traceable inputs.

## Ownership boundary

The generator is the **main House overview and navigation layer**. It is not the
canonical owner of Rooms, Actions, Infrastructure or any detailed device/domain
workflow.

For complex domains, the custom integration that owns the entities and actions also
owns its specialized dashboard in a dedicated repository. `ha-nikas-house`
may show verified summaries and navigate to that interface, but it does not ship its
implementation.

This rule is formally recorded in [ADR-001: Integration-owned specialized dashboards](ADR-001-INTEGRATION-OWNED-DASHBOARDS.md).

## Non-negotiable rules

- `unknown` / `unavailable` are distinct from normal/healthy states.
- Entity IDs come only from verified inventory.
- Generated dashboard files are not hand-edited in production workflow.
- Controls must preserve subsystem safety constraints defined by their contracts.
- A panel manifest is concise; reusable behavior belongs in contract modules and generator components.
- Input snapshots committed to Git must be scrubbed of secrets and private data.
- Detailed device/domain UX has one canonical owner; the central generator must not silently duplicate a specialized integration's full interaction model.
- Cross-dashboard links must target stable declared routes rather than invented paths.

## Current stage

Contract core v1 is implemented for the main House overview. `UIContract`,
`SemanticInventory`, `PanelManifest` and `NavigationContract` have machine-readable
schemas; repository validation enforces their boundaries and regression tests protect
the safety and repository-ownership invariants. Other panels evolve in their own
repositories and are connected only by declared routes.
