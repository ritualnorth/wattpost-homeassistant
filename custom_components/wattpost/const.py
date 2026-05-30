"""Constants for the WattPost Cloud integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "wattpost"
MANUFACTURER = "WattPost"

DEFAULT_BASE_URL = "https://wattpost.cloud"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)
MIN_SCAN_INTERVAL = timedelta(seconds=30)
MAX_SCAN_INTERVAL = timedelta(seconds=900)

CONF_BASE_URL = "base_url"
CONF_TOKEN = "token"
CONF_SITE_ID = "site_id"
CONF_SCAN_INTERVAL_SECONDS = "scan_interval_seconds"

USER_AGENT = (
    "WattPostHA/0.1 (+https://github.com/ritualnorth/wattpost-homeassistant)"
)
