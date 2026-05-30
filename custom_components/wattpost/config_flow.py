"""Config flow for the WattPost Cloud integration.

Two-step UI:

  1. Paste an API token (and optionally override the base URL for
     self-hosters). We validate by calling /api/v1/me — clear error
     if the token is rejected or the URL is unreachable.

  2. Pick which paired site (appliance) this config entry will
     represent. One HA "device" per site, so customers with multiple
     sites just run through the flow once per site.

Token + base_url live in entry.data (don't change at runtime). Scan
interval lives in entry.options so it can be tuned without re-auth.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # noqa: F401  (imported for HA's lifecycle)
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import (
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL_SECONDS,
    CONF_SITE_ID,
    CONF_TOKEN,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import (
    WattPostAuthError,
    async_list_sites,
    async_validate_token,
)


_LOGGER = logging.getLogger(__name__)


class WattPostConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for adding one WattPost site."""

    VERSION = 1

    def __init__(self) -> None:
        self._base_url: str = DEFAULT_BASE_URL
        self._token: str = ""
        self._sites: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._base_url = (user_input.get(CONF_BASE_URL) or DEFAULT_BASE_URL).strip()
            self._token = user_input[CONF_TOKEN].strip()
            try:
                me = await async_validate_token(self.hass, self._base_url, self._token)
                _LOGGER.debug("WattPost token validated for %s", me.get("email"))
                self._sites = await async_list_sites(
                    self.hass, self._base_url, self._token,
                )
            except WattPostAuthError:
                errors["base"] = "invalid_auth"
            except UpdateFailed as e:
                _LOGGER.warning("WattPost reachability failed: %s", e)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating WattPost token")
                errors["base"] = "unknown"
            else:
                if not self._sites:
                    errors["base"] = "no_sites"
                else:
                    return await self.async_step_pick_site()

        schema = vol.Schema({
            vol.Required(CONF_TOKEN, default=user_input.get(CONF_TOKEN) if user_input else ""): str,
            vol.Optional(
                CONF_BASE_URL,
                default=(user_input or {}).get(CONF_BASE_URL, DEFAULT_BASE_URL),
            ): str,
        })
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors or None,
            description_placeholders={"docs": "https://wattpost.cloud/docs/api"},
        )

    async def async_step_pick_site(
        self, user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        if user_input is not None:
            site_id = int(user_input[CONF_SITE_ID])
            await self.async_set_unique_id(f"{self._base_url}::{site_id}")
            self._abort_if_unique_id_configured()
            site = next((s for s in self._sites if s["id"] == site_id), None)
            label = (site or {}).get("label") or f"Site {site_id}"
            return self.async_create_entry(
                title=label,
                data={
                    CONF_BASE_URL: self._base_url,
                    CONF_TOKEN:    self._token,
                    CONF_SITE_ID:  site_id,
                },
            )

        # Build a label-keyed map for the select; HA shows label, returns id.
        options = {
            str(s["id"]): f"{s.get('label') or s.get('slug')}  ·  {'online' if s.get('online') else 'offline'}"
            for s in self._sites
        }
        schema = vol.Schema({vol.Required(CONF_SITE_ID): vol.In(options)})
        return self.async_show_form(step_id="pick_site", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "WattPostOptionsFlow":
        return WattPostOptionsFlow(config_entry)


class WattPostOptionsFlow(config_entries.OptionsFlow):
    """Tunable settings post-setup. Scan interval lives here so the
    user can dial it from the UI without re-auth."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL_SECONDS,
            int(DEFAULT_SCAN_INTERVAL.total_seconds()),
        )
        schema = vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL_SECONDS, default=current): vol.All(
                vol.Coerce(int),
                vol.Range(
                    min=int(MIN_SCAN_INTERVAL.total_seconds()),
                    max=int(MAX_SCAN_INTERVAL.total_seconds()),
                ),
            ),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
