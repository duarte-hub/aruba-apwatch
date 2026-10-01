"""Polling coordinator for Aruba APWatch."""
from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ArubaApiError, ArubaAuthError, ArubaInstantClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class ArubaData:
    wireless_clients: int


type ArubaConfigEntry = ConfigEntry[ArubaCoordinator]


class ArubaCoordinator(DataUpdateCoordinator[ArubaData]):
    """Fetch client data from an Aruba Instant virtual controller."""

    config_entry: ArubaConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ArubaConfigEntry, client: ArubaInstantClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> ArubaData:
        try:
            count = await self.client.get_client_count()
        except ArubaAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ArubaApiError as err:
            raise UpdateFailed(str(err)) from err
        return ArubaData(wireless_clients=count)
