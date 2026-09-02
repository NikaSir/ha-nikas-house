"""Button platform for NikaS House."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from homeassistant.components.button import ButtonEntity
from homeassistant.components.persistent_notification import async_create as async_create_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import GENERATED_DIRECTORY, SNAPSHOT_DIRECTORY, SOURCE_DIRECTORY
from .coordinator import NikasHouseCoordinator
from .house_panel import async_register_house_panel
from .registry_snapshot import capture_registry_snapshot, write_registry_snapshot
from .runtime_dispatch import RuntimeRenderError, render_all_manifests
from .runtime_registration import (
    RuntimeRegistrationError,
    write_lovelace_registration_snippet,
)
from .snapshot_download import SNAPSHOT_DOWNLOAD_URL


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[NikasHouseCoordinator],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up NikaS House buttons."""
    async_add_entities(
        [
            NikasHouseCaptureSnapshotButton(entry),
            NikasHouseDownloadSnapshotButton(entry),
            NikasHouseGenerateDashboardsButton(entry),
        ]
    )


class NikasHouseCaptureSnapshotButton(ButtonEntity):
    """Capture a scrubbed Home Assistant entity-registry snapshot."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_icon = "mdi:camera-outline"
    _attr_translation_key = "capture_registry_snapshot"

    def __init__(
        self,
        entry: ConfigEntry[NikasHouseCoordinator],
    ) -> None:
        """Initialize the snapshot button."""
        self._attr_unique_id = f"{entry.entry_id}_capture_registry_snapshot"

    async def async_press(self) -> None:
        """Capture and atomically rotate the local scrubbed snapshot."""
        document = capture_registry_snapshot(self.hass)
        snapshot_root = Path(
            self.hass.config.path(SOURCE_DIRECTORY, SNAPSHOT_DIRECTORY)
        )
        result = await self.hass.async_add_executor_job(
            write_registry_snapshot,
            snapshot_root,
            document,
        )
        self._attr_extra_state_attributes = {
            "snapshot_id": document["metadata"]["snapshot_id"],
            "entity_count": len(document["spec"]["entities"]),
            "registry_changed": result.changed,
            "current_file": str(
                result.current_path.relative_to(Path(self.hass.config.path()))
            ),
            "previous_available": result.previous_path is not None,
        }
        self.async_write_ha_state()


class NikasHouseDownloadSnapshotButton(ButtonEntity):
    """Expose the current scrubbed registry snapshot through an authenticated URL."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_icon = "mdi:download"
    _attr_translation_key = "download_registry_snapshot"

    def __init__(
        self,
        entry: ConfigEntry[NikasHouseCoordinator],
    ) -> None:
        """Initialize the snapshot download button."""
        self._attr_unique_id = f"{entry.entry_id}_download_registry_snapshot"

    async def async_press(self) -> None:
        """Publish an authenticated download link for current.json."""
        path = Path(
            self.hass.config.path(SOURCE_DIRECTORY, SNAPSHOT_DIRECTORY, "current.json")
        )
        if not path.is_file():
            message = "Сначала нажмите «Снять снимок реестра». Файл current.json ещё не создан."
            self._attr_extra_state_attributes = {
                "download_url": None,
                "current_file": None,
                "last_error": message,
            }
            self.async_write_ha_state()
            raise HomeAssistantError(message)

        self._attr_extra_state_attributes = {
            "download_url": SNAPSHOT_DOWNLOAD_URL,
            "current_file": str(path.relative_to(Path(self.hass.config.path()))),
            "last_error": None,
        }
        self.async_write_ha_state()
        async_create_notification(
            self.hass,
            (
                "Снимок реестра готов к скачиванию.\n\n"
                f"[Скачать current.json]({SNAPSHOT_DOWNLOAD_URL})\n\n"
                "Ссылка доступна только авторизованному пользователю Home Assistant."
            ),
            title="NikaS House · снимок реестра",
            notification_id="nikas_house_registry_snapshot_download",
        )


class NikasHouseGenerateDashboardsButton(ButtonEntity):
    """Generate deterministic Lovelace YAML without applying it to Home Assistant."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_icon = "mdi:view-dashboard-edit-outline"
    _attr_translation_key = "generate_dashboards"

    def __init__(
        self,
        entry: ConfigEntry[NikasHouseCoordinator],
    ) -> None:
        """Initialize the generation button."""
        self._attr_unique_id = f"{entry.entry_id}_generate_dashboards"
        self._coordinator = entry.runtime_data

    async def async_press(self) -> None:
        """Render manifests and export a non-applied YAML registration snippet."""
        await self._coordinator.async_request_refresh()
        if self._coordinator.data.status != "valid":
            message = (
                "NikaS House source tree must be valid before rendering; "
                f"current status is {self._coordinator.data.status!r}"
            )
            self._attr_extra_state_attributes = {"last_error": message}
            self.async_write_ha_state()
            raise HomeAssistantError(message)

        config_root = Path(self.hass.config.path())
        source_root = Path(self.hass.config.path(SOURCE_DIRECTORY))
        generated_root = Path(
            self.hass.config.path(SOURCE_DIRECTORY, GENERATED_DIRECTORY)
        )
        try:
            artifacts = await self.hass.async_add_executor_job(
                render_all_manifests,
                source_root,
                generated_root,
            )
            registration = await self.hass.async_add_executor_job(
                write_lovelace_registration_snippet,
                source_root,
                generated_root,
            )
            await async_register_house_panel(self.hass, source_root)
        except (
            RuntimeRenderError,
            RuntimeRegistrationError,
            OSError,
            ValueError,
            json.JSONDecodeError,
            yaml.YAMLError,
        ) as exc:
            message = str(exc)
            self._attr_extra_state_attributes = {"last_error": message}
            self.async_write_ha_state()
            raise HomeAssistantError(message) from exc

        self._attr_extra_state_attributes = {
            "generated_count": len(artifacts),
            "changed_count": sum(artifact.changed for artifact in artifacts),
            "output_directory": str(generated_root.relative_to(config_root)),
            "files": [
                str(artifact.output_path.relative_to(config_root))
                for artifact in artifacts
            ],
            "traces": [
                str(artifact.trace_path.relative_to(config_root))
                for artifact in artifacts
            ],
            "dashboard_sha256": {
                artifact.manifest_id: artifact.dashboard_sha256
                for artifact in artifacts
            },
            "registration_snippet": str(
                registration.path.relative_to(config_root)
            ),
            "registration_changed": registration.changed,
            "registration_dashboard_count": registration.dashboard_count,
            "last_error": None,
        }
        self.async_write_ha_state()
