"""NikaS House integration for the NikaS House overview."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .coordinator import NikasHouseCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[NikasHouseCoordinator],
) -> bool:
    """Set up the House-only NikaS House integration."""
    from homeassistant.components.frontend import add_extra_js_url
    from homeassistant.components.http import StaticPathConfig
    from homeassistant.const import Platform

    from .const import (
        DOMAIN,
        FRONTEND_DIRECTORY,
        FRONTEND_STATIC_REGISTERED,
        HOUSE_HERO_ASSETS_STATIC_PATH,
        HOUSE_HERO_FILENAME,
        HOUSE_HERO_MODULE_URL,
        HOUSE_HERO_STATIC_PATH,
        HOUSE_PANEL_FILENAME,
        HOUSE_PANEL_STATIC_PATH,
        SOURCE_DIRECTORY,
        UI_BUNDLE_FILENAME,
        UI_BUNDLE_MODULE_URL,
        UI_BUNDLE_STATIC_PATH,
    )
    from .coordinator import NikasHouseCoordinator
    from .house_panel import async_register_house_panel
    from .inventory_migration import (
        LEGACY_SOURCE_DIRECTORY,
        InventoryMigrationError,
        migrate_legacy_house_inventory,
    )
    from .runtime_source_sync import sync_bundled_public_sources
    from .snapshot_download import async_register_snapshot_download_view

    source_root = Path(hass.config.path(SOURCE_DIRECTORY))
    try:
        await hass.async_add_executor_job(sync_bundled_public_sources, source_root)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, yaml.YAMLError) as err:
        _LOGGER.warning("Cannot synchronize NikaS House sources during setup: %s", err)

    legacy_source_root = Path(hass.config.path(LEGACY_SOURCE_DIRECTORY))
    try:
        migration = await hass.async_add_executor_job(
            migrate_legacy_house_inventory,
            source_root,
            legacy_source_root,
        )
        if migration.migrated:
            _LOGGER.info(
                "Imported verified House inventory into %s",
                migration.target_path,
            )
    except (InventoryMigrationError, OSError, json.JSONDecodeError, yaml.YAMLError) as err:
        _LOGGER.warning("Cannot import verified House inventory: %s", err)

    async_register_snapshot_download_view(hass)
    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get(FRONTEND_STATIC_REGISTERED):
        frontend_root = Path(__file__).parent / FRONTEND_DIRECTORY
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    UI_BUNDLE_STATIC_PATH,
                    str(frontend_root / UI_BUNDLE_FILENAME),
                    False,
                ),
                StaticPathConfig(
                    HOUSE_HERO_STATIC_PATH,
                    str(frontend_root / HOUSE_HERO_FILENAME),
                    False,
                ),
                StaticPathConfig(
                    HOUSE_PANEL_STATIC_PATH,
                    str(frontend_root / HOUSE_PANEL_FILENAME),
                    False,
                ),
                StaticPathConfig(
                    HOUSE_HERO_ASSETS_STATIC_PATH,
                    str(frontend_root / "assets"),
                    False,
                ),
            ]
        )
        domain_data[FRONTEND_STATIC_REGISTERED] = True

    # This module supplies only safe HA navigation. It does not inject chrome
    # into, replace, or hide any legacy YAML dashboard.
    add_extra_js_url(hass, UI_BUNDLE_MODULE_URL)
    add_extra_js_url(hass, HOUSE_HERO_MODULE_URL)

    try:
        await async_register_house_panel(hass, source_root)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, yaml.YAMLError) as err:
        _LOGGER.warning("Cannot register specialized NikaS House panel: %s", err)

    coordinator = NikasHouseCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(
        entry,
        (Platform.SENSOR, Platform.BUTTON),
    )
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[NikasHouseCoordinator],
) -> bool:
    """Unload only resources and the House fallback owned by this integration."""
    from homeassistant.components.frontend import remove_extra_js_url
    from homeassistant.const import Platform

    from .const import HOUSE_HERO_MODULE_URL, UI_BUNDLE_MODULE_URL
    from .house_panel import async_unregister_house_panel

    unloaded = await hass.config_entries.async_unload_platforms(
        entry,
        (Platform.SENSOR, Platform.BUTTON),
    )
    if unloaded:
        async_unregister_house_panel(hass)
        for module_url in (UI_BUNDLE_MODULE_URL, HOUSE_HERO_MODULE_URL):
            try:
                remove_extra_js_url(hass, module_url)
            except KeyError:
                pass
    return unloaded
