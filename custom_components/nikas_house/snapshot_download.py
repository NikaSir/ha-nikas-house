"""Authenticated download endpoint for the current registry snapshot."""

from __future__ import annotations

from pathlib import Path

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import SNAPSHOT_DIRECTORY, SOURCE_DIRECTORY

SNAPSHOT_DOWNLOAD_URL = "/api/nikas_house/registry_snapshot"


class RegistrySnapshotDownloadView(HomeAssistantView):
    """Serve the current scrubbed registry snapshot to authenticated HA users."""

    url = SNAPSHOT_DOWNLOAD_URL
    name = "api:nikas_house:registry_snapshot"
    requires_auth = True

    async def get(self, request: web.Request) -> web.StreamResponse:
        """Download current.json as an attachment."""
        hass: HomeAssistant = request.app["hass"]
        path = Path(
            hass.config.path(SOURCE_DIRECTORY, SNAPSHOT_DIRECTORY, "current.json")
        )
        if not path.is_file():
            raise web.HTTPNotFound(text="Registry snapshot has not been captured yet.")
        return web.FileResponse(
            path,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Content-Disposition": 'attachment; filename="nikas-house-registry-current.json"',
                "Cache-Control": "no-store",
            },
        )


def async_register_snapshot_download_view(hass: HomeAssistant) -> None:
    """Register the authenticated snapshot download endpoint once."""
    key = "nikas_house_snapshot_download_view_registered"
    if hass.data.get(key):
        return
    hass.http.register_view(RegistrySnapshotDownloadView())
    hass.data[key] = True
