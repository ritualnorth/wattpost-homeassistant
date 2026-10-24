"""Binary sensors — currently just "online" connectivity for the site.

Online is true when the cloud has seen a heartbeat in the last 15 min
(matches the cloud's own definition). Goes off the moment heartbeats
stop arriving — covers "Pi unplugged", "internet died", "container
crashed" without us needing to know which.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WattPostCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WattPostCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WattPostOnlineSensor(coordinator)])


class WattPostOnlineSensor(
    CoordinatorEntity[WattPostCoordinator], BinarySensorEntity,
):
    """Site connectivity. `on` = the cloud has seen a heartbeat
    in the last 15 minutes."""

    _attr_has_entity_name = True
    _attr_name = "Online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: WattPostCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.site_id}_online"

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
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return bool(self.coordinator.data.get("online"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "last_seen":  data.get("last_seen"),
            "slug":       data.get("slug"),
        }
