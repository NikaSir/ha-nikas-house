"""Sensor platform for NikaS House."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CONTRACTS,
    ATTR_DOCUMENT_COUNT,
    ATTR_INVENTORY,
    ATTR_ISSUE_COUNT,
    ATTR_ISSUES,
    ATTR_MANIFESTS,
    ATTR_NAVIGATION,
    ATTR_SOURCE_DIRECTORY,
    ATTR_VALIDATION_LEVEL,
    MAX_ISSUES_IN_ATTRIBUTES,
    SOURCE_DIRECTORY,
    SOURCE_STATUSES,
    VALIDATION_LEVEL,
)
from .coordinator import NikasHouseCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[NikasHouseCoordinator],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up NikaS House sensors."""
    async_add_entities([NikasHouseSourceStatusSensor(entry)])


class NikasHouseSourceStatusSensor(
    CoordinatorEntity[NikasHouseCoordinator],
    SensorEntity,
):
    """Expose the validation status of the contract source tree."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_icon = "mdi:file-tree"
    _attr_options = list(SOURCE_STATUSES)
    _attr_translation_key = "source_status"

    def __init__(
        self,
        entry: ConfigEntry[NikasHouseCoordinator],
    ) -> None:
        """Initialize the source status sensor."""
        super().__init__(entry.runtime_data)
        self._attr_unique_id = f"{entry.entry_id}_source_status"

    @property
    def native_value(self) -> str:
        """Return the source validation status."""
        return self.coordinator.data.status

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return compact, scrubbed validation details."""
        data = self.coordinator.data
        return {
            ATTR_SOURCE_DIRECTORY: SOURCE_DIRECTORY,
            ATTR_VALIDATION_LEVEL: VALIDATION_LEVEL,
            ATTR_CONTRACTS: data.counts[ATTR_CONTRACTS],
            ATTR_INVENTORY: data.counts[ATTR_INVENTORY],
            ATTR_MANIFESTS: data.counts[ATTR_MANIFESTS],
            ATTR_NAVIGATION: data.counts[ATTR_NAVIGATION],
            ATTR_DOCUMENT_COUNT: data.document_count,
            ATTR_ISSUE_COUNT: len(data.issues),
            ATTR_ISSUES: [
                issue.as_dict()
                for issue in data.issues[:MAX_ISSUES_IN_ATTRIBUTES]
            ],
        }
