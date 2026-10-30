# Aruba APWatch

Home Assistant custom integration (HACS) that polls **Aruba Instant** access
points for connected wireless clients.

Unofficial community project — not affiliated with Aruba / HPE.

## Features

- [x] `sensor.<ap>_wireless_clients` — number of wireless clients on the Instant cluster
- [x] Per-AP devices, each with per-radio sensors for every band (2.4 / 5 / 6 GHz):
  transmit power (dBm), channel number, and channel utilization (%)
- [x] Configurable polling: Settings → Devices & Services → Aruba APWatch →
  **Configure** → scan interval (10–3600 s, default 60)
- [ ] Per-client listing (MAC, IP, SSID, AP, band, signal)
- [ ] Per-AP / per-SSID breakdown

## How it works

Talks to the Instant virtual controller's WebUI endpoint
`https://<ap>:4343/swarm.cgi` — the same calls the Aruba WebUI makes — and runs
`show clients` and `show aps`. No need to enable the separate Instant REST API
(`allow-rest-api`), no SNMP, no extra services.

If you have several Instant APs in one cluster, point it at the **virtual
controller IP**; the count covers the whole cluster.

## Install

1. HACS → ⋮ → **Custom repositories** → add this repo URL, category *Integration*.
2. Install **Aruba APWatch**, restart Home Assistant.
3. Settings → Devices & Services → **Add Integration** → *Aruba APWatch*.
4. Enter host (e.g. `192.168.0.4`), port `4343`, and your WebUI username/password.

Manual install: copy `custom_components/aruba_apwatch` into your HA
`config/custom_components/` folder and restart.

## Troubleshooting

Enable debug logging:

```yaml
logger:
  logs:
    custom_components.aruba_apwatch: debug
```
