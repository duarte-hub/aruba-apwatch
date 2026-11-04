"""Polling coordinator for Aruba APWatch."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ApInfo, ArubaApiError, ArubaAuthError, ArubaInstantClient, ClientInfo
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class ArubaData:
    clients: list[ClientInfo]
    aps: dict[str, ApInfo] = field(default_factory=dict)


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
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client

    async def _async_update_data(self) -> ArubaData:
        try:
            clients = await self.client.get_clients()
            aps = await self.client.get_aps()
        except ArubaAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ArubaApiError as err:
            raise UpdateFailed(str(err)) from err
        return ArubaData(clients=clients, aps={ap.serial: ap for ap in aps})


def hub_device_info(entry: ArubaConfigEntry) -> DeviceInfo:
    """Device for the Instant virtual controller, shared by its hub-level entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Aruba",
        model="Instant AP",
        configuration_url=f"https://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}",
    )
