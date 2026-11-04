"""Aruba APWatch — monitor Aruba Instant APs from Home Assistant."""
from __future__ import annotations

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ArubaInstantClient
from .coordinator import ArubaConfigEntry, ArubaCoordinator

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ArubaConfigEntry) -> bool:
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, False)
    client = ArubaInstantClient(
        async_get_clientsession(hass, verify_ssl=verify_ssl),
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        verify_ssl,
    )
    coordinator = ArubaCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ArubaConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.logout()
    return unloaded


async def _async_reload_on_options(hass: HomeAssistant, entry: ArubaConfigEntry) -> None:
    """Reload so the coordinator picks up a changed scan interval."""
    await hass.config_entries.async_reload(entry.entry_id)
