"""WattPost Cloud — Home Assistant integration.

Cloud-mode: HA polls wattpost.cloud's public REST API, NOT the local
appliance. This means a cabin / van / boat appliance with poor or no
LAN reachability still surfaces in HA — as long as its heartbeats are
making it up to the cloud, HA can see the data.

One config entry == one paired site. Entities live under a single HA
"device" so they cluster cleanly in the UI.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN
from .coordinator import WattPostAuthError, WattPostCoordinator


_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = WattPostCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except WattPostAuthError as e:
        raise ConfigEntryAuthFailed(str(e)) from e

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change (scan interval)."""
    await hass.config_entries.async_reload(entry.entry_id)
