# 📡 WiCS Survival Deck

A portable, battery-powered emergency computer built on a Raspberry Pi 4 by the **WiCS Build Project** team. It's designed to keep working when the internet, cell service and power are gone.

**Demo Day:** December 4, 2026

---

## What it does

The deck opens to a home screen with survival tools that all work **offline**:

| Tool | What it does | Status |
|---|---|---|
| 💬 **Messages** | A chat room on the deck's own Wi-Fi. Anyone nearby joins from their phone's browser, no cell service needed. | ✅ Working (`chat.py`) |
| 📚 **Library** | First aid, medical, repair and Wikipedia guides stored on the deck (Kiwix) | 🚧 In progress |
| 📻 **Radio** | NOAA weather radio and FM through a USB radio dongle | 🚧 In progress |
| 📓 **Journal** | Write entries and sketch drawings, saved with the date | 🚧 In progress |
| 🗺️ **Map** | Offline map of the area (saved image first, then a real map) | 🚧 In progress |
| 🧭 **Compass** | Digital compass from a magnetometer sensor | ⏳ Stretch goal |
| 📍 **GPS** | "You are here" dot on the map | ⏳ Stretch goal |

---

## Quick start: the chat

You can run the chat on a laptop right now, no Pi needed.

**On a laptop**
```bash
pip install flask
python chat.py
```
Open **http://localhost:5000** in two browser tabs and chat between them.

**On the Pi**
```bash
sudo apt install -y python3-flask
python3 chat.py
```
Then open the chat from:

| Where you are | Address |
|---|---|
| On the Pi itself | `http://localhost:5000` |
| A phone on the deck's hotspot | `http://10.42.0.1:5000` |
| A device on the same regular Wi-Fi | `http://<Pi's IP>:5000` (find it with `hostname -I`) |

Each person picks a nickname. New messages show up every 2 seconds, and they're saved to `messages.json`, so they survive a restart.

---

## Hardware

**Have**
- Raspberry Pi 4 (4GB) with a 64GB microSD card (Raspberry Pi OS)
- Keyboard, mouse, micro-HDMI to HDMI cable
- Power: USB-C laptop charger for now (needs 5V/3A), power bank for portable use
- USB 3 flash drive (storage until we get an SSD)
- 3.5mm headphones
- TVs or monitors for display

**Ordering**
- NooElec NESDR Smart radio dongle (RTL2832U + R820T2)
- Adafruit LIS3MDL compass sensor + STEMMA QT to female sockets cable
- VK-162 USB GPS dongle
- Rugged case (needed by late November)

---

## Setting up the Pi

### Remote access
```bash
sudo raspi-config      # Interface Options → turn on SSH and VNC
hostname -I            # shows the Pi's IP address
```
From a laptop on the **same network**:
```bash
ssh <username>@<Pi's IP>
```
The part before `@` is the Pi's **username** (shown in its terminal prompt), not the hostname.

> ⚠️ **Campus Wi-Fi blocks devices from talking to each other**, so SSH and VNC time out there. Use one of these:
> - **Phone hotspot:** connect the Pi and your laptop to the same hotspot, then run `hostname -I` again for the new IP.
> - **Raspberry Pi Connect:** works from anywhere through a browser.
>   ```bash
>   sudo apt install -y rpi-connect
>   rpi-connect signin
>   ```
>   Then go to **connect.raspberrypi.com** on your laptop.

### Health check
Run this whenever you add hardware or test something heavy:
```bash
vcgencmd measure_temp      # keep it under 75°C
vcgencmd get_throttled     # throttled=0x0 means power is fine
```
If `get_throttled` shows anything other than `0x0`, the power supply is too weak.

### Turning off safely
**Never just unplug the Pi.** It can corrupt the SD card and wipe everything.
```bash
sudo shutdown now
```
Wait for the green light to stop blinking, then unplug.

---

## Repository layout

```
survival-deck/
├── README.md        ← you are here
├── chat.py          ← offline chat (working)
├── templates/       ← pages for each home screen tile (planned)
├── static/          ← styles, images, offline code libraries (planned)
├── data/            ← saved journal entries (planned)
└── scripts/         ← Pi setup scripts (planned)
```

> **Offline rule:** never load code libraries from a CDN link. The deck has no internet. Download them into `static/libs/` instead.

---

## Team roles

| Team | Responsible for |
|---|---|
| **DevOps** | Pi setup, remote access, installing software (Kiwix, radio tools), the Wi-Fi hotspot, making the home screen start on boot, backups |
| **SWE** | The home screen and its tiles: chat, journal, map, radio buttons, compass screen, theme |
| **Embedded** | Wiring the compass, connecting the radio and GPS, power, the case and assembly |

---

## Timeline

| Date | Milestone |
|---|---|
| **Nov 6** | Hackathon: chat running on the Pi, library opens, parts ordered |
| **Nov 9–22** | Radio, journal and map connected to the home screen; full system test |
| **Nov 23–29** | Everything assembled into the case; heat test inside the case |
| **Nov 30** | Feature freeze, bug fixes only after this |
| **Dec 4** | 🎉 Demo Day |

---

## Contributing

1. `git pull` before you start
2. Make your changes and test them
3. `git add .`, then `git commit -m "what you changed"`, then `git push`
4. Tell your team lead what you finished

Pick **one** task, put your name on it, and give it a due date.

---

## Credits

- **WiCS Build Project team** (Fall 2026)
- Offline library: [Kiwix](https://www.kiwix.org)
- Map data: © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors
