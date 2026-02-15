# CPU Direct USB Checker (Linux)

A Python utility to detect whether your USB devices (mice, keyboards, controllers) are connected through **CPU-direct USB ports** or **Chipset USB ports** on Linux systems.

This is a Linux port of the concept and tool by **Marius Heier**.  
Original Project: [https://tools.mariusheier.com/cpudirect.html](https://tools.mariusheier.com/cpudirect.html)

## Why does this matter?
- **CPU-direct ports** connect directly to the CPU die, offering the lowest possible latency. This is preferred for high-performance gaming peripherals.
- **Chipset ports** route data through the motherboard chipset before reaching the CPU, adding a small amount of latency.
- **USB Hubs** (external or internal) add further latency and should be avoided for competitive input devices.

## Features
- Detects USB Controller type (CPU vs Chipset).
- Detects if a device is connected through a Hub.
- Provides a "Status" rating (BEST, HUB, CHIPSET, BAD).
- Color-coded terminal output.

## Prerequisites
- Linux
- Python 3.8+
- `pciutils` (provides the `lspci` command)
- `typer` and `rich` (installed automatically)

## Installation

### From PyPI (Recommended)
```bash
pip install cpu-direct-usb-linux
```

### From Source
1. Clone the repository:
    ```bash
    git clone https://github.com/lance0/cpu-direct-linux.git
    cd cpu-direct-linux
    ```

2. Install with uv (recommended):
    ```bash
    uv sync
    ```

   Or with pip:
    ```bash
    pip install .
    ```

### System Requirements
Ensure `lspci` is installed (part of pciutils):
```bash
# Debian/Ubuntu
sudo apt install pciutils

# Arch Linux
sudo pacman -S pciutils

# Fedora
sudo dnf install pciutils
```

## Usage

After installation, run the command:

```bash
cpu-usb-check
```

Or run the script directly from source:

```bash
python3 cpu_usb_check.py
```

To disable colors:

```bash
cpu-usb-check --no-color
```

For JSON output (useful for scripting):

```bash
cpu-usb-check --json
```

Example JSON output:
```json
{
  "controllers": [
    {"name": "Controller Name", "type": "CPU"}
  ],
  "devices": [
    {
      "name": "Device Name",
      "vid_pid": "1234:5678",
      "controller": "Controller Name",
      "controller_type": "CPU",
      "status": "BEST",
      "hubs": []
    }
  ]
}
```

## Example Output

```text
CONTROLLERS
  [CPU]      Advanced Micro Devices, Inc. [AMD] Device 14c9 (rev da)
  [Chipset]  ASMedia Technology Inc. ASM3242 USB 3.2 Host Controller

INPUT DEVICES

  Razer DeathAdder V3
  VID:PID 1532:00B2
  Controller: Advanced Micro Devices, Inc. [AMD] Device 14c9 (direct to CPU die)
  Hub: NO
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

## How it works
The script uses `lspci` to list USB controllers and analyzes `/sys/bus/usb/devices/` to map physical devices to their parent PCI controllers. It attempts to distinguish CPU vs Chipset controllers based on PCI device names and hierarchy heuristics.

## Development

### Running Tests
```bash
uv run pytest
```

### Linting & Type Checking
This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and [mypy](https://mypy.readthedocs.io/) for type checking.
```bash
uvx ruff check
uvx mypy
```

## License
MIT License
