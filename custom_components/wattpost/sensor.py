"""Sensor entities for one WattPost site.

Each entity is defined declaratively via `WattPostSensorDescription`,
which carries the field path within the coordinator's payload, plus
HA-native device_class / state_class / unit. New sensors = one row
in `_SENSORS`.

Payload shape (from GET /api/v1/sites/{id}):

    {
      "id": 12, "label": "Garage Stack", "slug": "wp-xxxx",
      "online": true,
      "last_seen": "...",
      "latest": {
        "received_at": "...",
        "soc_pct": 64.5, "net_w": -125,
        "extras": { "voltage_v": 12.6, "current_a": -8.4,
                    "pv_today_wh": 1700, "load_today_wh": 1500,
                    "bank_net_today_wh": 200,
                    "time_to_go_minutes": 1320, ... }
      }
    }
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WattPostCoordinator


def _latest(data: dict[str, Any]) -> dict[str, Any]:
    return (data or {}).get("latest") or {}


def _extras(data: dict[str, Any]) -> dict[str, Any]:
    return _latest(data).get("extras") or {}


@dataclass(frozen=True, kw_only=True)
class WattPostSensorDescription(SensorEntityDescription):
    """Sensor + how to pull its value out of the coordinator payload."""
    value_fn: Callable[[dict[str, Any]], Any]


_SENSORS: tuple[WattPostSensorDescription, ...] = (
    WattPostSensorDescription(
        key="soc",
        translation_key="soc",
        name="State of charge",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: _latest(d).get("soc_pct"),
    ),
    WattPostSensorDescription(
        key="net_power",
        translation_key="net_power",
        name="Net power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda d: _latest(d).get("net_w"),
    ),
    WattPostSensorDescription(
        key="voltage",
        translation_key="voltage",
        name="Battery voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda d: _extras(d).get("voltage_v"),
    ),
    WattPostSensorDescription(
        key="current",
        translation_key="current",
        name="Battery current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda d: _extras(d).get("current_a"),
    ),
    WattPostSensorDescription(
        key="pv_today",
        translation_key="pv_today",
        name="Solar today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        value_fn=lambda d: _extras(d).get("pv_today_wh") or _extras(d).get("sources_today_wh"),
    ),
    WattPostSensorDescription(
        key="load_today",
        translation_key="load_today",
        name="Load today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        value_fn=lambda d: _extras(d).get("load_today_wh"),
    ),
    WattPostSensorDescription(
        key="bank_net_today",
        translation_key="bank_net_today",
        name="Bank net today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        value_fn=lambda d: _extras(d).get("bank_net_today_wh"),
    ),
    WattPostSensorDescription(
        key="remaining_ah",
        translation_key="remaining_ah",
        name="Remaining capacity",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="Ah",
        icon="mdi:battery-50",
        value_fn=lambda d: _extras(d).get("remaining_ah") or _extras(d).get("bank_remaining_ah"),
    ),
    WattPostSensorDescription(
        key="time_to_go",
        translation_key="time_to_go",
        name="Time to empty",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:battery-clock",
        value_fn=lambda d: _extras(d).get("time_to_go_minutes") or _extras(d).get("time_to_empty_min"),
    ),
    WattPostSensorDescription(
        key="temperature",
        translation_key="temperature",
        name="Battery temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: _extras(d).get("temperature_c"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WattPostCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        WattPostSensor(coordinator, desc) for desc in _SENSORS
    )


class WattPostSensor(CoordinatorEntity[WattPostCoordinator], SensorEntity):
    """One sensor reading off the shared coordinator payload."""

    _attr_has_entity_name = True
    entity_description: WattPostSensorDescription

    def __init__(
        self,
        coordinator: WattPostCoordinator,
        description: WattPostSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.site_id}_{description.key}"

    @property
    def device_info(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        slug = data.get("slug") or f"site-{self.coordinator.site_id}"
        return {
            "identifiers":  {(DOMAIN, str(self.coordinator.site_id))},
            "manufacturer": "WattPost",
            "name":         data.get("label") or f"WattPost {slug}",
            "model":        "WattPost appliance",
            "configuration_url": f"https://wattpost.cloud/app/site/{self.coordinator.site_id}",
        }

    @property
    def native_value(self) -> Any:
        try:
            return self.entity_description.value_fn(self.coordinator.data or {})
        except Exception:  # noqa: BLE001
            return None

    @property
    def available(self) -> bool:
        return super().available and (self.coordinator.data is not None)
