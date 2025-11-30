#!/usr/bin/env python3
#
# CPU Direct USB Checker (Linux Port)
# Based on the tool by Marius Heier: https://tools.mariusheier.com/cpudirect.html
#
import os
import sys
import subprocess
import glob
import re
import argparse
import json
from typing import Any, Dict, List, Optional, Union, TypedDict, cast


# Type definitions
class ControllerInfo(TypedDict):
    name: str
    type: str


class DeviceInfo(TypedDict):
    name: str
    vid_pid: str
    controller: str
    controller_type: str
    status: str
    hubs: List[str]


class OutputData(TypedDict):
    controllers: List[ControllerInfo]
    devices: List[DeviceInfo]
    error: Optional[str]


# ANSI Colors
class Colors:
    HEADER = "\033[36m"  # Cyan
    LABEL = "\033[33m"  # Yellow
    BEST = "\033[32m"  # Green
    GOOD = "\033[32m"  # Green
    WARN = "\033[33m"  # Yellow
    BAD = "\033[31m"  # Red
    TEXT = "\033[90m"  # Gray (Bright Black)
    VALUE = "\033[97m"  # White
    RESET = "\033[0m"

    @staticmethod
    def disable() -> None:
        Colors.HEADER = ""
        Colors.LABEL = ""
        Colors.BEST = ""
        Colors.GOOD = ""
        Colors.WARN = ""
        Colors.BAD = ""
        Colors.TEXT = ""
        Colors.VALUE = ""
        Colors.RESET = ""


def read_file_content(path: str, default: str = "") -> str:
    """Helper to safely read a single line from a file."""
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return default


def get_pci_name(pci_slot: str) -> str:
    """
    Get the pretty name of a PCI device using lspci.
    """
    try:
        # lspci -s 05:00.4
        output = (
            subprocess.check_output(
                ["lspci", "-s", pci_slot], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
        # Output ex: 05:00.4 USB controller: Advanced Micro Devices, Inc. [AMD] Device 14c9 (rev da)
        # We want the part after "USB controller: "
        if "USB controller:" in output:
            return output.split("USB controller:", 1)[1].strip()
        return output
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return f"Unknown Controller [{pci_slot}]"


def is_cpu_controller(pci_name: str, pci_slot: str) -> bool:
    """
    Heuristic to determine if a controller is CPU-direct or Chipset.
    Based on common naming patterns.
    """
    name_lower = pci_name.lower()

    # Strong indicators of Chipset/External
    if "chipset" in name_lower:
        return False
    if "asmedia" in name_lower:
        return False  # ASMedia is often the chipset or aux controller on AMD boards
    if "via" in name_lower or "nec" in name_lower:
        return False  # Add-in cards

    # Default to True (CPU) for generic AMD/Intel controllers not marked as Chipset
    return True


def get_usb_info(sys_path: str) -> Optional[Dict[str, Any]]:
    """
    Traverse up from a USB device to find its controller and any intermediate hubs.
    """
    try:
        real_path = os.path.realpath(sys_path)
    except OSError:
        return None

    hub_count = 0
    hubs: List[str] = []

    curr = real_path
    controller_pci: Optional[str] = None

    # Walk up the directory structure
    while True:
        parent = os.path.dirname(curr)
        base = os.path.basename(curr)

        # Check if we hit the PCI device (directory name pattern HHHH:BB:DD.F)
        if re.match(r"^[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f]$", base):
            controller_pci = base
            break

        if base.startswith("usb") and base[3:].isdigit():
            # This is the root hub (e.g. usb3), pass through to parent
            pass
        elif re.match(r"^\d+-\d+(\.\d+)*$", base):
            # This is a USB device/hub in the chain.
            # If it's not the device itself (which we started with), it's a hub.
            if curr != real_path:
                hub_count += 1
                hub_name = read_file_content(
                    os.path.join(curr, "product"), "Unknown Hub"
                )
                hubs.append(hub_name)

        if parent == curr:  # Reached root without finding PCI (shouldn't happen)
            break
        curr = parent

    return {"controller_pci": controller_pci, "hub_count": hub_count, "hubs": hubs}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check USB device connection path (CPU vs Chipset)."
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Disable colored output"
    )
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    args = parser.parse_args()

    if args.no_color or args.json:
        Colors.disable()

    # Check for lspci
    if (
        subprocess.call(
            ["which", "lspci"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        != 0
    ):
        error_msg = "Error: 'lspci' command not found. Please install pciutils (e.g., sudo apt install pciutils)."
        if args.json:
            print(json.dumps({"error": error_msg}))
        else:
            print(f"{Colors.BAD}{error_msg}{Colors.RESET}")
        sys.exit(1)

    controllers: Dict[str, Dict[str, Any]] = {}  # slot -> info
    data: OutputData = {"controllers": [], "devices": [], "error": None}

    try:
        # Get all USB controllers via lspci
        lspci_out = (
            subprocess.check_output(["lspci", "-nn"], stderr=subprocess.DEVNULL)
            .decode()
            .splitlines()
        )
        for line in lspci_out:
            # Look for Class 0c03 (USB)
            if "USB controller" in line or "0c03" in line:
                parts = line.split(" ", 1)
                slot = parts[0]

                # Check if it exists in sysfs
                sys_matches = glob.glob(f"/sys/bus/pci/devices/*{slot}")
                if sys_matches:
                    full_slot = os.path.basename(sys_matches[0])
                    name = get_pci_name(slot)

                    is_cpu = is_cpu_controller(name, slot)

                    controllers[full_slot] = {"name": name, "is_cpu": is_cpu}
                    data["controllers"].append(
                        cast(
                            ControllerInfo,
                            {"name": name, "type": "CPU" if is_cpu else "Chipset"},
                        )
                    )

                    if not args.json:
                        prefix = (
                            f"{Colors.BEST}[CPU]    "
                            if is_cpu
                            else f"{Colors.TEXT}[Chipset]"
                        )
                        print(f"  {prefix} {Colors.VALUE}{name}{Colors.RESET}")

    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
        if args.json:
            data["error"] = f"Error scanning controllers: {e}"
        else:
            print(f"{Colors.BAD}Error scanning controllers: {e}{Colors.RESET}")

    # 2. Input Devices
    if not args.json:
        print("")
        print(f"{Colors.LABEL}INPUT DEVICES{Colors.RESET}")

    found_any = False

    # Scan /sys/bus/usb/devices/
    usb_devices = glob.glob("/sys/bus/usb/devices/*")

    for dev_path in usb_devices:
        base = os.path.basename(dev_path)
        # Skip root hubs (usbX) and interfaces (1-1:1.0)
        if ":" in base or not "-" in base:
            continue

        product_name = read_file_content(
            os.path.join(dev_path, "product"), "Unknown Device"
        )
        vid = read_file_content(os.path.join(dev_path, "idVendor"))
        pid = read_file_content(os.path.join(dev_path, "idProduct"))

        if not vid or not pid:
            continue

        # Check if HID (Class 03)
        is_input = False
        interfaces = glob.glob(os.path.join(dev_path, "*:*.*/bInterfaceClass"))
        for iface_class_file in interfaces:
            if read_file_content(iface_class_file) == "03":  # HID
                is_input = True
                break

        # Skip Hubs (Class 09) from the device list
        if read_file_content(os.path.join(dev_path, "bDeviceClass")) == "09":
            continue

        if not is_input:
            continue

        # Filter generic names
        if re.search(
            r"HID-compliant (mouse|keyboard|device|vendor|consumer|system)",
            product_name,
            re.I,
        ):
            continue
        if re.match(r"^USB Input Device$|^HID Keyboard Device$", product_name, re.I):
            continue

        found_any = True

        # Get topology info
        info = get_usb_info(dev_path)
        if not info or not info["controller_pci"]:
            continue

        pci_slot = info["controller_pci"]
        ctrl_info = (
            controllers.get(pci_slot, {"name": "Unknown", "is_cpu": False})
            if pci_slot
            else {"name": "Unknown", "is_cpu": False}
        )

        is_cpu = ctrl_info["is_cpu"]
        has_hub = info["hub_count"] > 0

        # Determine Status
        if is_cpu and not has_hub:
            status = "BEST"
        elif is_cpu and has_hub:
            status = "HUB"
        elif not is_cpu and not has_hub:
            status = "CHIPSET"
        else:
            status = "CHIPSET+HUB"

        device_data = {
            "name": product_name,
            "vid_pid": f"{vid}:{pid}",
            "controller": ctrl_info["name"],
            "controller_type": "CPU" if is_cpu else "Chipset",
            "status": status,
            "hubs": info["hubs"] if has_hub else [],
        }
        data["devices"].append(cast(DeviceInfo, device_data))

        if not args.json:
            print("")
            print(f"  {Colors.VALUE}{product_name}{Colors.RESET}")
            print(f"  {Colors.TEXT}VID:PID {vid}:{pid}{Colors.RESET}")

            # Controller
            ct_prefix = Colors.BEST if is_cpu else Colors.WARN
            ct_suffix = "(direct to CPU die)" if is_cpu else "(extra latency)"
            print(
                f"  {Colors.TEXT}Controller: {ct_prefix}{ctrl_info['name']} {Colors.TEXT}{ct_suffix}{Colors.RESET}"
            )

        if not args.json:
            # Hub
            if has_hub:
                hub_names = ", ".join(info["hubs"]) if info["hubs"] else "Yes"
                print(
                    f"  {Colors.TEXT}Hub: {Colors.WARN}YES - {hub_names}{Colors.RESET}"
                )

            # Status
            status_color = (
                Colors.BEST
                if status == "BEST"
                else Colors.WARN if status in ["HUB", "CHIPSET"] else Colors.BAD
            )
            print(f"  {Colors.TEXT}Status: {status_color}[{status}]{Colors.RESET}")

    if not args.json:
        if not found_any:
            print(f"\n  {Colors.TEXT}No USB input devices found.{Colors.RESET}")

        # Legend
        print("")
        print(
            f"{Colors.HEADER}============================================================{Colors.RESET}"
        )
        print("")
        print(f"{Colors.LABEL}STATUS GUIDE:{Colors.RESET}")
        print(
            f"  {Colors.BEST}[BEST]        {Colors.TEXT}CPU-direct, no hub - lowest possible latency{Colors.RESET}"
        )
        print(
            f"  {Colors.WARN}[HUB]         {Colors.TEXT}CPU-direct but through a hub - try another port{Colors.RESET}"
        )
        print(
            f"  {Colors.WARN}[CHIPSET]     {Colors.TEXT}Chipset USB - move to CPU port if available{Colors.RESET}"
        )
        print(
            f"  {Colors.BAD}[CHIPSET+HUB] {Colors.TEXT}Worst path - definitely move this device{Colors.RESET}"
        )
        print("")

    # Output JSON if requested
    if args.json:
        print(json.dumps(data, indent=2))
    print(
        f"{Colors.HEADER}============================================================{Colors.RESET}"
    )
    print("")
    print(f"{Colors.LABEL}STATUS GUIDE:{Colors.RESET}")
    print(
        f"  {Colors.BEST}[BEST]        {Colors.TEXT}CPU-direct, no hub - lowest possible latency{Colors.RESET}"
    )
    print(
        f"  {Colors.WARN}[HUB]         {Colors.TEXT}CPU-direct but through a hub - try another port{Colors.RESET}"
    )
    print(
        f"  {Colors.WARN}[CHIPSET]     {Colors.TEXT}Chipset USB - move to CPU port if available{Colors.RESET}"
    )
    print(
        f"  {Colors.BAD}[CHIPSET+HUB] {Colors.TEXT}Worst path - definitely move this device{Colors.RESET}"
    )
    print("")


if __name__ == "__main__":
    main()
