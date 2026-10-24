"""Constants for the WattPost Cloud integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "wattpost"
MANUFACTURER = "WattPost"

DEFAULT_BASE_URL = "https://wattpost.cloud"
# The cloud's API quota is 10,000 calls per token per month (one call per ~4.3
# minutes), and the appliance only uploads every few minutes, so polling faster
# than this shows nothing new and runs the quota out part-way through the month.
DEFAULT_SCAN_INTERVAL = timedelta(seconds=300)
MIN_SCAN_INTERVAL = timedelta(seconds=60)
MAX_SCAN_INTERVAL = timedelta(seconds=900)

CONF_BASE_URL = "base_url"
CONF_TOKEN = "token"
CONF_SITE_ID = "site_id"
CONF_SCAN_INTERVAL_SECONDS = "scan_interval_seconds"

USER_AGENT = (
    "WattPostHA/0.1 (+https://github.com/ritualnorth/wattpost-homeassistant)"
)
