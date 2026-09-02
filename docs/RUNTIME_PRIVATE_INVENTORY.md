# Private runtime inventory

Production Home Assistant bindings are intentionally separated from the public repository.

## Public repository

The public repository may contain:

- UI contracts;
- panel manifests;
- schemas;
- generator and validation code;
- synthetic examples and tests.

Contracts and manifests must not contain concrete `entity_id`, `device_id` or `area_id` values.

## Home Assistant runtime

Real bindings live under:

`/config/nikas_house/inventory/`

On the first parallel installation only, when this directory is empty, the integration
may copy the complete verified `house.home.*` subset from the existing private
`/config/contract_generated_ui/inventory/` tree. This is a non-destructive data
migration: no legacy JavaScript, Python module, asset or manifest is loaded at runtime,
and an existing NikaS House inventory is never overwritten.

A production `SemanticInventory` is generated only from a captured `RegistrySnapshot` and explicit verified bindings. It may contain real Home Assistant `entity_id` values and therefore is treated as private runtime configuration.

Do not publish production inventory files to the public GitHub repository.

The public House manifest references semantic keys only, for example:

`house.home.power_a`

The private inventory resolves that semantic key to the actual Home Assistant entity.

## House production scope

The runtime inventory for this repository binds only semantic roles consumed by the
main House overview, including safety, openings, motion, lighting, climate, cameras,
weather, utilities, heating, vehicles and access.

Detailed-panel bindings are owned by their separate repositories and must not be copied
into this source tree.

## Three-phase power policy

The House roles `house.home.power_a/b/c` must be bound to the three verified incoming
phase-voltage entities. If a separate Infrastructure inventory exposes the trusted
source as `infrastructure.power.voltage_a/b/c`, that fact may guide the private rebind,
but it does not create a runtime dependency between repositories.

Concrete Home Assistant entity ids remain exclusively in private inventory. They are
not recorded in the public contract, manifest, documentation or tests.
