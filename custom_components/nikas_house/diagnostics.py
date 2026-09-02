"""Diagnostics support for NikaS House."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .registry_snapshot import capture_registry_snapshot


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return a fresh scrubbed registry snapshot as native HA diagnostics."""
    del entry
    return capture_registry_snapshot(hass)
