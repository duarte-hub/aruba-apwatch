"""Sensors for Aruba APWatch."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ArubaConfigEntry, ArubaCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ArubaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([WirelessClientsSensor(entry.runtime_data)])


class WirelessClientsSensor(CoordinatorEntity[ArubaCoordinator], SensorEntity):
    """Number of wireless clients connected to the Instant cluster."""

    _attr_has_entity_name = True
    _attr_translation_key = "wireless_clients"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "clients"

    def __init__(self, coordinator: ArubaCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        host = entry.data[CONF_HOST]
        self._attr_unique_id = f"{entry.entry_id}_wireless_clients"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Aruba",
            model="Instant AP",
            configuration_url=f"https://{host}:{entry.data[CONF_PORT]}",
        )

    @property
    def native_value(self) -> int:
        return self.coordinator.data.wireless_clients
