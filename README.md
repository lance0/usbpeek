# usbpeek

A Python utility to analyze USB device latency and topology on Linux.

Detect whether your USB devices are connected through CPU-direct or Chipset USB ports, and check their polling rates.

## Why does this matter?

- **CPU-direct ports** connect directly to the CPU die, offering the lowest possible latency. This is critical for competitive gaming and low-latency audio.
- **Chipset ports** route data through the motherboard chipset before reaching the CPU, adding ~1-3ms of latency.
- **USB Hubs** (external or internal) add further latency and should be avoided for competitive input devices.
- **Polling rate** affects how often the device reports data to the system.

## Features

- Detects USB Controller type (CPU vs Chipset)
- Detects if a device is connected through a Hub
- Shows polling rate (125Hz, 500Hz, 1000Hz, etc.)
- Provides a "Status" rating (BEST, HUB, CHIPSET, CHIPSET+HUB)
- Color-coded terminal output with Rich
- Filter by device class (HID, audio, video, wireless)
- Filter by controller
- Multiple output formats: JSON, CSV, Table
- Summary view for quick overview
- Shell completion support

## Installation

### From PyPI
```bash
pip install usbpeek
```

### From Source
```bash
git clone https://github.com/lance0/usbpeek.git
cd usbpeek
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
usbpeek
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--no-color` | | Disable colored output |
| `--json` | | Output in JSON format |
| `--csv` | | Output in CSV format |
| `--table` | | Output in table format |
| `--format` | `-f` | Output format: json, csv, table |
| `--only-best` | | Show only devices with BEST status |
| `--show-all` | | Show all USB device classes |
| `--device-class` | `-d` | Filter by device class (hid, audio, video, wireless) |
| `--controller` | `-c` | Filter by controller name (partial match) |
| `--quiet` | `-q` | Suppress non-essential output |
| `--summary` | | Show device count summary |
| `--output` | `-o` | Write output to file |
| `--show-polling-rate` | | Show polling rate for each device |
| `--polling-rate-only` | | Show only devices with non-default rates |
| `--verbose` | `-v` | Show verbose debug info |
| `--version` | | Show version |
| `--install-completion` | | Install shell completion |

### Examples

Show all devices:
```bash
usbpeek
```

Show only BEST devices:
```bash
usbpeek --only-best
```

Show polling rates:
```bash
usbpeek --show-polling-rate
```

Show only high-polling-rate devices:
```bash
usbpeek --polling-rate-only
```

Show only audio devices:
```bash
usbpeek --device-class audio
```

Show summary:
```bash
usbpeek --summary
```

JSON output for scripting:
```bash
usbpeek --json > output.json
```

## Example Output

```text
CONTROLLERS
  [CPU]      AMD Device 14c9
  [Chipset]  ASMedia ASM3242 USB 3.2 Host Controller

DEVICES

  Razer DeathAdder V3
  VID:PID 1532:00B2
  Controller: AMD Device 14c9 (direct to CPU die)
  Polling Rate: 1000 Hz
  Status: [BEST]

============================================================

STATUS GUIDE:
  [BEST]        CPU-direct, no hub - lowest possible latency
  [HUB]         CPU-direct but through a hub - try another port
  [CHIPSET]     Chipset USB - move to CPU port if available
  [CHIPSET+HUB] Worst path - definitely move this device
```

## How it works

The tool uses `lspci` to enumerate USB controllers and reads `/sys/bus/usb/devices/` to map physical devices to their parent PCI controllers. It distinguishes CPU vs Chipset controllers based on PCI device naming patterns.

Polling rate is read from the USB device's `bInterval` descriptor and converted to Hz based on the device's speed (Full Speed, High Speed, etc.).

## Shell Completion

Install shell completion for your shell:

```bash
# Bash
usbpeek --install-completion bash

# Zsh
usbpeek --install-completion zsh

# Fish
usbpeek --install-completion fish
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
