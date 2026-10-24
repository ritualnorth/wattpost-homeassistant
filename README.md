# WattPost Cloud · Home Assistant integration

Surfaces your WattPost-paired sites in Home Assistant by polling the
public REST API at `wattpost.cloud`. Cloud-mode by design — Home
Assistant never has to reach your appliance directly, so a remote
cabin, off-grid van, or boat on poor cellular still works as long as
the appliance is uploading to the cloud.

## Which route should I use?

There are two, and they are not alternatives to stack:

**Same network as the appliance → use MQTT, not this integration.**
The appliance has an MQTT exporter that publishes Home Assistant
discovery messages. Turn it on (Settings → Integrations → MQTT, or
`exporters.mqtt` with `ha_discovery: true` in `config.yaml`), point it at
your Mosquitto broker, and Home Assistant's built-in MQTT integration
creates every sensor on its own. That is local push: real-time,
no cloud account, no API quota, and it keeps working with the internet
down. Home Assistant classifies it as `local_push`; this integration is
`cloud_polling`.

**Home Assistant is somewhere else → use this integration.** A cabin, van
or boat whose appliance you can't reach from home. It reads the data the
appliance last uploaded to wattpost.cloud, so values are as fresh as the
appliance's last upload (about a minute on a good link) and the "Online"
sensor tells you when it has gone quiet.

## What you get

One Home Assistant device per paired site, with:

- **State of charge** (%)
- **Net power** (W, signed: + charging, − discharging)
- **Battery voltage** (V)
- **Battery current** (A)
- **Solar today** (Wh, energy dashboard friendly)
- **Load today** (Wh, energy dashboard friendly)
- **Bank net today** (Wh)
- **Remaining capacity** (Ah)
- **Time to empty** (minutes)
- **Battery temperature** (°C)
- **Online** (binary — the cloud has seen a heartbeat in the last 15 minutes)

All sensors carry HA's native device-classes and state-classes so they
slot into the Energy dashboard out of the box.

## Requirements

- Home Assistant 2024.4 or newer
- A WattPost account with at least one paired appliance
- An API token, minted at **WattPost → Account → API keys**. API tokens
  need a paid plan (Pro or Installer); the free Hobby plan can't mint
  them.

## Installation

### Option A — HACS (recommended)

1. In Home Assistant, open **HACS → Integrations**.
2. Click the **⋮** menu, **Custom repositories**.
3. Add this repo URL with category **Integration**, click **Add**.
4. Search for **WattPost Cloud** and install.
5. Restart Home Assistant.
6. **Settings → Devices & services → Add integration → WattPost Cloud**.

### Option B — Manual

1. Copy the `custom_components/wattpost/` folder into your HA
   `<config>/custom_components/` directory.
2. Restart Home Assistant.
3. **Settings → Devices & services → Add integration → WattPost Cloud**.

## Setup

1. Paste your API token. (Self-hosted? Override the base URL with
   your wattpost-cloud install URL.)
2. Pick which site this device represents. Each WattPost site = one HA
   device. Run setup again per site if you have more than one.
3. Optionally tune the polling interval under **Options** (default 300
   seconds, range 60 – 900). The appliance uploads every few minutes, so
   polling faster than that won't reveal new data — it just chews API
   quota (see below).

## How it works

```
   ┌────────────┐  uploads (BLE / Modbus → JSON, ~60s)       ┌──────────────┐
   │ Appliance  │ ──────────────────────────────────────────► │ wattpost.cloud │
   │ at the     │                                              │  REST API    │
   │ cabin/van  │                                              └──────┬───────┘
   └────────────┘                                                     │
                                                                      │ polls
                                                                      ▼
                                                              ┌──────────────┐
                                                              │ Home Assistant│
                                                              │  (at home)    │
                                                              └──────────────┘
```

The appliance pushes its data up to wattpost.cloud whenever it has any
internet, and keeps a backlog while it doesn't. Home Assistant (running
on the customer's home internet) pulls from the cloud. There is no direct
path between HA and the appliance — which is exactly the point.

## Privacy + costs

- Reads only. The token has read-only scope on your sites.
- All traffic between HA and `wattpost.cloud` is HTTPS.
- API quota is per-token, monthly. Watch `X-RateLimit-Remaining` in
  the HA debug logs if you want to see how much is left. The default
  quota is 10,000 calls a month, which is one call every ~4.3 minutes.
  The default polling interval (300 s, ~8,600 calls/month) fits one
  site; two sites on one token need ≥ 600 s each, or a token per site.
  Polling at 60 s would use ~43,000 calls a month and run dry in about
  a week, after which the integration reports the quota error until
  the 1st.

## Troubleshooting

- **"Invalid auth"** — the token is wrong, revoked, or copy-pasted with
  extra whitespace. Mint a fresh one and try again.
- **"Cannot connect"** — the wattpost.cloud host isn't reachable from
  HA. Check HA's network access.
- **"No sites"** — your account has no paired appliances. Pair one
  first via the wattpost dashboard.
- **Entities go unavailable** — the most recent poll failed.
  HA shows the reason; usually a transient network hiccup. The
  coordinator backs off automatically.

## License

Apache-2.0. See `LICENSE`.
