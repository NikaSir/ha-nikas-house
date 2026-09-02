from generator.snapshot import (
    ParsedBinding,
    SnapshotBindingError,
    build_inventory,
    canonical_snapshot_id,
)


def test_disabled_entity_cannot_become_verified_inventory_binding() -> None:
    entities = [
        {
            "entity_id": "sensor.disabled_source",
            "domain": "sensor",
            "platform": "synthetic",
            "disabled": True,
            "hidden": False,
        }
    ]
    snapshot = {
        "api_version": "nikas.home-assistant/registry-snapshot/v1",
        "kind": "RegistrySnapshot",
        "metadata": {
            "captured_at": "2026-08-21T10:00:00Z",
            "source": "home_assistant",
            "scrubbed": True,
            "snapshot_id": canonical_snapshot_id(entities),
        },
        "spec": {"entities": entities},
    }

    try:
        build_inventory(
            snapshot,
            [ParsedBinding("diagnostic.source.disabled", "sensor.disabled_source")],
        )
    except SnapshotBindingError as exc:
        assert "is disabled in snapshot" in str(exc)
    else:
        raise AssertionError("disabled entity must be rejected")
