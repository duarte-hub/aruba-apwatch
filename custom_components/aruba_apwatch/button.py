"""Buttons for Aruba APWatch."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ArubaConfigEntry, ArubaCoordinator, hub_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ArubaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([RefreshButton(entry.runtime_data)])


class RefreshButton(CoordinatorEntity[ArubaCoordinator], ButtonEntity):
    """Poll the virtual controller now instead of waiting for the next interval."""

    _attr_has_entity_name = True
    _attr_translation_key = "refresh"

    def __init__(self, coordinator: ArubaCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_refresh"
        self._attr_device_info = hub_device_info(coordinator.config_entry)

    async def async_press(self) -> None:
        await self.coordinator.async_refresh()
