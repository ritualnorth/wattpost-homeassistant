"""DataUpdateCoordinator for a single WattPost site.

One coordinator instance per config entry. Polls
`GET /api/v1/sites/{id}` on the user's chosen interval and stashes the
full payload — including the embedded `latest` heartbeat — in
`coordinator.data` for entities to read.

Bearer-token auth, X-RateLimit-* headers logged at debug. Network /
auth failures raise UpdateFailed so HA's coordinator surfaces them
into the UI instead of swallowing.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL_SECONDS,
    CONF_SITE_ID,
    CONF_TOKEN,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    USER_AGENT,
)


_LOGGER = logging.getLogger(__name__)


class WattPostAuthError(Exception):
    """Raised when the API returns 401 — token revoked or invalid."""


class WattPostCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the WattPost cloud for one site."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.base_url: str = entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL).rstrip("/")
        self.token: str = entry.data[CONF_TOKEN]
        self.site_id: int = int(entry.data[CONF_SITE_ID])

        scan_seconds = entry.options.get(CONF_SCAN_INTERVAL_SECONDS) or entry.data.get(
            CONF_SCAN_INTERVAL_SECONDS,
        )
        interval = (
            timedelta(seconds=int(scan_seconds))
            if scan_seconds else DEFAULT_SCAN_INTERVAL
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_site_{self.site_id}",
            update_interval=interval,
        )

    @property
    def site_url(self) -> str:
        return f"{self.base_url}/api/v1/sites/{self.site_id}"

    async def _async_update_data(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "User-Agent":    USER_AGENT,
            "Accept":        "application/json",
        }
        try:
            async with asyncio.timeout(15):
                async with session.get(self.site_url, headers=headers) as resp:
                    body = await resp.text()
                    if resp.status == 401:
                        raise WattPostAuthError("token revoked or invalid")
                    if resp.status == 404:
                        raise UpdateFailed(
                            "site not found (the appliance may have been "
                            "deleted from the account)"
                        )
                    if resp.status >= 400:
                        raise UpdateFailed(
                            f"WattPost API returned {resp.status}: {body[:200]}"
                        )
                    # Log rate-limit headers at debug for ops visibility.
                    rl_remaining = resp.headers.get("X-RateLimit-Remaining")
                    if rl_remaining is not None:
                        _LOGGER.debug(
                            "rate_limit: %s remaining (limit %s, reset %s)",
                            rl_remaining,
                            resp.headers.get("X-RateLimit-Limit"),
                            resp.headers.get("X-RateLimit-Reset"),
                        )
                    import json
                    return json.loads(body)
        except WattPostAuthError:
            raise
        except (TimeoutError, aiohttp.ClientError) as e:
            raise UpdateFailed(f"network error talking to WattPost: {e}") from e


# ---------- standalone helpers used by the config flow ----------


async def async_validate_token(
    hass: HomeAssistant, base_url: str, token: str,
) -> dict[str, Any]:
    """Call /api/v1/me to confirm the token is live. Returns the parsed
    response on success; raises WattPostAuthError on 401, UpdateFailed
    on other non-2xx, ClientError on network issues."""
    session = async_get_clientsession(hass)
    url = f"{base_url.rstrip('/')}/api/v1/me"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent":    USER_AGENT,
        "Accept":        "application/json",
    }
    async with asyncio.timeout(15):
        async with session.get(url, headers=headers) as resp:
            text = await resp.text()
            if resp.status == 401:
                raise WattPostAuthError("token rejected by WattPost")
            if resp.status != 200:
                raise UpdateFailed(f"WattPost API returned {resp.status}: {text[:200]}")
            import json
            return json.loads(text)


async def async_list_sites(
    hass: HomeAssistant, base_url: str, token: str,
) -> list[dict[str, Any]]:
    """Call /api/v1/sites to enumerate the user's appliances."""
    session = async_get_clientsession(hass)
    url = f"{base_url.rstrip('/')}/api/v1/sites"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent":    USER_AGENT,
        "Accept":        "application/json",
    }
    async with asyncio.timeout(15):
        async with session.get(url, headers=headers) as resp:
            text = await resp.text()
            if resp.status == 401:
                raise WattPostAuthError("token rejected by WattPost")
            if resp.status != 200:
                raise UpdateFailed(f"WattPost API returned {resp.status}: {text[:200]}")
            import json
            return list(json.loads(text).get("sites") or [])
