# WattPost Cloud

Cloud-mode Home Assistant integration for **WattPost**. Polls the
public REST API at `wattpost.cloud` so HA can surface your sites from
home even when the appliance itself lives in a poor-connectivity
cabin, van, or boat — the appliance pushes heartbeats up to the cloud,
HA pulls from the cloud, the cabin never has to be reachable.

## Sensors

State of charge · Net power · Battery voltage / current · Solar
today · Load today · Bank net today · Remaining capacity · Time to
empty · Battery temperature · Online (binary).

All HA device-class + state-class tagged so they slot into the Energy
dashboard.

## Setup

Mint an API token at **WattPost → Account → API keys**. Add the
integration in **Settings → Devices & services**, paste the token,
pick which site this HA device represents.

See [README](https://github.com/ritualnorth/wattpost-homeassistant) for
full docs.
