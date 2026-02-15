# CPU Direct USB Checker (Linux)

A Python utility to detect whether your USB devices (mice, keyboards, controllers, audio gear) are connected through **CPU-direct USB ports** or **Chipset USB ports** on Linux systems.

This is a Linux port of the concept and tool by **Marius Heier**.  
Original Project: [https://tools.mariusheier.com/cpudirect.html](https://tools.mariusheier.com/cpudirect.html)

## Why does this matter?

- **CPU-direct ports** connect directly to the CPU die, offering the lowest possible latency. This is critical for competitive gaming and low-latency audio.
- **Chipset ports** route data through the motherboard chipset before reaching the CPU, adding ~1-3ms of latency.
- **USB Hubs** (external or internal) add further latency and should be avoided for competitive input devices.

## Features

- Detects USB Controller type (CPU vs Chipset)
- Detects if a device is connected through a Hub
- Provides a "Status" rating (BEST, HUB, CHIPSET, CHIPSET+HUB)
- Color-coded terminal output with Rich
- Filter by device class (HID, audio, video, wireless)
- Filter by controller
- JSON output for scripting
- Summary view for quick overview
- Shell completion support

## Installation

### From PyPI
```bash
pip install cpu-direct-usb-linux
```

### From Source
```bash
git clone https://github.com/lance0/cpu-direct-linux.git
cd cpu-direct-linux
uv sync
```

### System Requirements

- Linux
- Python 3.9+
- `pciutils` (provides `lspci`)

```bash
# Debian/Ubuntu
sudo apt install pciutils

# Arch Linux
sudo pacman -S pciutils

# Fedora
sudo dnf install pciutils
```

## Usage

```bash
cpu-usb-check
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--no-color` | | Disable colored output |
| `--json` | | Output in JSON format |
| `--only-best` | | Show only devices with BEST status |
| `--show-all` | | Show all USB device classes |
| `--device-class` | `-d` | Filter by device class (hid, audio, video, wireless) |
| `--controller` | `-c` | Filter by controller name (partial match) |
| `--quiet` | `-q` | Suppress non-essential output |
| `--summary` | | Show device count summary |
| `--output` | `-o` | Write JSON output to file |
| `--verbose` | `-v` | Show verbose debug info |
| `--version` | | Show version |
| `--install-completion` | | Install shell completion |

### Examples

Show all devices:
```bash
cpu-usb-check
```

Show only BEST devices:
```bash
cpu-usb-check --only-best
```

Show only audio devices:
```bash
cpu-usb-check --device-class audio
```

Show devices on a specific controller:
```bash
cpu-usb-check --controller amd
```

Show summary:
```bash
cpu-usb-check --summary
```

JSON output for scripting:
```bash
cpu-usb-check --json > output.json
```

Save JSON to file:
```bash
cpu-usb-check --json --output devices.json
```

Suppress headers:
```bash
cpu-usb-check --quiet --only-best
```

## Example Output

```text
CONTROLLERS
  [CPU]      Advanced Micro Devices, Inc. [AMD] Device 14c9
  [Chipset]  ASMedia Technology Inc. ASM3242 USB 3.2 Host Controller

DEVICES

  Razer DeathAdder V3
  VID:PID 1532:00B2
  Controller: Advanced Micro Devices, Inc. [AMD] Device 14c9 (direct to CPU die)
  Status: [BEST]

  Keychron Q1
  VID:PID 3434:0240
  Controller: ASMedia Technology Inc. ASM3242 USB 3.2 Host Controller (extra latency)
  Hub: YES - Hub Name
  Status: [HUB]

============================================================

STATUS GUIDE:
  [BEST]        CPU-direct, no hub - lowest possible latency
  [HUB]         CPU-direct but through a hub - try another port
  [CHIPSET]     Chipset USB - move to CPU port if available
  [CHIPSET+HUB] Worst path - definitely move this device
```

### Summary Output
```text
Summary:
  BEST:        2
  HUB:         1
  CHIPSET:     0
  CHIPSET+HUB: 0
  Total:       3
```

## JSON Output

```json
{
  "controllers": [
    {"name": "AMD Device 14c9", "type": "CPU"}
  ],
  "devices": [
    {
      "name": "Razer DeathAdder V3",
      "vid_pid": "1532:00B3",
      "controller": "AMD Device 14c9",
      "controller_type": "CPU",
      "status": "BEST",
      "hubs": []
    }
  ]
}
```

## How it works

The script uses `lspci` to enumerate USB controllers and reads `/sys/bus/usb/devices/` to map physical devices to their parent PCI controllers. It distinguishes CPU vs Chipset controllers based on PCI device naming patterns (AMD XHCI, Intel XHCI are CPU-direct; ASMedia, VIA, NEC are chipset).

## Shell Completion

Install shell completion for your shell:

```bash
# Bash
cpu-usb-check --install-completion bash

# Zsh
cpu-usb-check --install-completion zsh

# Fish
cpu-usb-check --install-completion fish
```

## Development

```bash
# Run tests
uv run pytest

# Lint
uvx ruff check

# Type check
uvx mypy
```

## License

MIT License
