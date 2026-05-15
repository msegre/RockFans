# Tuya Ceiling Fan — Home Assistant Custom Integration

Local-control integration for Tuya protocol ceiling fans that report the wrong device
type in the stock Tuya integration. No cloud connection required. No `tinytuya`
dependency — the integration speaks the Tuya LAN protocol directly using only the
Python standard library and the `cryptography` package (already present in HA).

---

## Features

Each fan you add creates **two entities** that share one device:

| Entity | Card | Controls |
|---|---|---|
| `fan.<name>` | Mushroom Fan Card | On/Off · Speed (6 levels) · Direction |
| `light.<name>_light` | Light Card | On/Off · Brightness · Color Temperature |

---

## Installation

### Option A — HACS (recommended)

1. In HACS → **Custom Repositories**, add the URL to this repo, category **Integration**.
2. Install **Tuya Ceiling Fan**, then restart Home Assistant.

### Option B — Manual

1. Copy the `tuya_ceiling_fan/` folder into `<config>/custom_components/`.
2. Restart Home Assistant.

---

## Adding a Fan

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Tuya Ceiling Fan**.
3. Fill in the form:

| Field | Example |
|---|---|
| Fan name | `Porch` |
| IP address | `192.168.20.35` |
| Device ID | `eb3664fdce6e186f7e2ecn` |
| Local key | `#3BE=@RWTMO(kD..` |

4. Click **Submit**. The integration will test connectivity before saving.

Repeat for each fan. Your five fans and their credentials:

| Name | IP | Device ID | Local Key |
|---|---|---|---|
| Porch | 192.168.20.35 | eb3664fdce6e186f7e2ecn | `#3BE=@RWTMO(kD..` |
| Guest BR | 192.168.20.36 | eb38837aa876ffa00evylj | `*Es^pM_l[`!=*g)r` |
| Office | 192.168.20.37 | ebc2aed12ae50cf88cfxkc | `D89zI{P?R#zgw+I]` |
| Primary BR | 192.168.20.38 | eb097d683fe950736anqzg | `$ltSLAuXH-'d0{by` |
| Living Room | 192.168.20.39 | ebdd5394103f0b8166qrif | `TOs\|5K73Z\|#0f$?\|` |

---

## Mushroom Fan Card (HACS)

Install the [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom) HACS
frontend plugin, then add a card like this to your dashboard:

```yaml
type: custom:mushroom-fan-card
entity: fan.porch
show_percentage_control: true
show_oscillate_control: false
icon_animation: true
```

---

## DPS Reference

| DPS | Code | Type | Values |
|---|---|---|---|
| Light on/off | 20 | bool | true / false |
| Light mode | 21 | enum | white / colour / music |
| Brightness | 22 | int | 0–1000 |
| Color temp | 23 | int | 0 (warm 2700 K) – 1000 (cool 6500 K) |
| Fan direction | 101 | enum | forward / reverse |
| Fan speed | 102 | enum | level_1 … level_6 |
| Countdown | 103 | enum | cancel |
| Fan speed (num) | 104 | int | 1–6 |
| Fan on/off | 105 | bool | true / false |
| Fan mode | 106 | enum | fresh |

---

## Troubleshooting

**Cannot connect during setup**
- Confirm the fan is on the same VLAN/subnet as Home Assistant.
- Verify the IP is static (set a DHCP reservation using the MAC addresses in the docs).
- Double-check the local key — it changes if you reset the device or re-pair it in the app.

**Entities unavailable after adding**
- Check HA logs (`Settings → System → Logs`) for errors from `tuya_ceiling_fan`.
- The integration polls every 30 seconds; a single failed poll won't mark entities
  unavailable immediately (HA requires several consecutive failures).

**Protocol version**
- The client tries v3.5 first (AES-GCM, port 6668). If your firmware is older it
  will automatically fall back on subsequent retries. You can verify the firmware
  version in the Smart Life / Tuya app under device info.
