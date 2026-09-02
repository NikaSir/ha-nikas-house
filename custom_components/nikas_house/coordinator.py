"""Data coordinator for NikaS House."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, SCAN_INTERVAL, SOURCE_DIRECTORY
from .validation import ValidationSnapshot, validate_source_tree

_LOGGER = logging.getLogger(__name__)


class NikasHouseCoordinator(DataUpdateCoordinator[ValidationSnapshot]):
    """Coordinate validation of local contract sources."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.source_root = Path(hass.config.path(SOURCE_DIRECTORY))
        self.schema_root = Path(__file__).parent / "schemas"

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=SCAN_INTERVAL,
            always_update=False,
        )

    async def _async_update_data(self) -> ValidationSnapshot:
        """Validate sources outside the Home Assistant event loop."""
        return await self.hass.async_add_executor_job(
            validate_source_tree,
            self.source_root,
            self.schema_root,
        )
