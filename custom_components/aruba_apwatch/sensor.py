"""Sensors for Aruba APWatch."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CONF_HOST, CONF_PORT, PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import RadioInfo
from .const import DOMAIN
from .coordinator import ArubaConfigEntry, ArubaCoordinator


@dataclass(frozen=True, kw_only=True)
class RadioSensorDescription(SensorEntityDescription):
    """Describes a per-radio sensor."""

    value_fn: Callable[[RadioInfo], int | None]


RADIO_SENSORS: tuple[RadioSensorDescription, ...] = (
    RadioSensorDescription(
        key="power",
        translation_key="radio_power",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement="dBm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda radio: radio.power_dbm,
    ),
    RadioSensorDescription(
        key="channel",
        translation_key="radio_channel",
        value_fn=lambda radio: radio.channel,
    ),
    RadioSensorDescription(
        key="utilization",
        translation_key="radio_utilization",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda radio: radio.utilization,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ArubaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([WirelessClientsSensor(coordinator)])

    known: set[tuple[str, int, str]] = set()

    @callback
    def _add_new_radios() -> None:
        new: list[RadioSensor] = []
        for serial, ap in coordinator.data.aps.items():
            for index in ap.radios:
                for description in RADIO_SENSORS:
                    key = (serial, index, description.key)
                    if key not in known:
                        known.add(key)
                        new.append(RadioSensor(coordinator, serial, index, description))
        if new:
            async_add_entities(new)

    _add_new_radios()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_radios))


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


class RadioSensor(CoordinatorEntity[ArubaCoordinator], SensorEntity):
    """A power / channel / utilization reading for one radio of one AP."""

    _attr_has_entity_name = True
    entity_description: RadioSensorDescription

    def __init__(
        self,
        coordinator: ArubaCoordinator,
        serial: str,
        radio_index: int,
        description: RadioSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._serial = serial
        self._radio_index = radio_index
        entry = coordinator.config_entry
        ap = coordinator.data.aps[serial]
        self._attr_unique_id = f"{serial}_radio{radio_index}_{description.key}"
        self._attr_translation_placeholders = {
            "band": ap.radios[radio_index].band.replace("GHz", " GHz")
        }
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=ap.name,
            manufacturer="Aruba",
            model=ap.model,
            serial_number=serial,
            via_device=(DOMAIN, entry.entry_id),
            configuration_url=f"https://{ap.ip}:{entry.data[CONF_PORT]}",
        )

    @property
    def _radio(self) -> RadioInfo | None:
        ap = self.coordinator.data.aps.get(self._serial)
        return ap.radios.get(self._radio_index) if ap else None

    @property
    def available(self) -> bool:
        return super().available and self._radio is not None

    @property
    def native_value(self) -> int | None:
        radio = self._radio
        return self.entity_description.value_fn(radio) if radio else None
