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
- Python 3.6+
- `pciutils` (provides the `lspci` command)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/lance0/cpu-direct-usb.git
   cd cpu-direct-usb
   ```

2. Ensure `lspci` is installed:
   ```bash
   # Debian/Ubuntu
   sudo apt install pciutils

   # Arch Linux
   sudo pacman -S pciutils

   # Fedora
   sudo dnf install pciutils
   ```

## Usage

Run the script directly:

```bash
python3 cpu_usb_check.py
```

Or make it executable:

```bash
chmod +x cpu_usb_check.py
./cpu_usb_check.py
```

## Example Output

```text
CPU DIRECT USB CHECKER (Linux Port)
============================================================
EXPERIMENTAL - detection heuristics are approximated

USB CONTROLLERS
  [CPU]      Advanced Micro Devices, Inc. [AMD] Device 14c9 (rev da)
  [Chipset]  ASMedia Technology Inc. ASM3242 USB 3.2 Host Controller

INPUT DEVICES

  Razer DeathAdder V3
  VID:PID 1532:00B2
  Controller: Advanced Micro Devices, Inc. [AMD] Device 14c9 (rev da) (direct to CPU die)
  Status: [BEST]

  Keychron Q1
  VID:PID 3434:0240
  Controller: ASMedia Technology Inc. ASM3242 USB 3.2 Host Controller (extra latency)
  Status: [CHIPSET]
```

## How it works
The script uses `lspci` to list USB controllers and analyzes `/sys/bus/usb/devices/` to map physical devices to their parent PCI controllers. It attempts to distinguish CPU vs Chipset controllers based on PCI device names and hierarchy heuristics.

## Development

### Running Tests
```bash
python3 -m unittest tests.test_cpu_usb_check
```

### Code Formatting
This project uses [Black](https://black.readthedocs.io/) for code formatting and [isort](https://pycqa.github.io/isort/) for import sorting.

### Type Checking
This project uses [mypy](https://mypy.readthedocs.io/) for static type checking.

## License
MIT License
