#!/usr/bin/env python3
#
# CPU Direct USB Checker (Linux Port)
# Based on the tool by Marius Heier: https://tools.mariusheier.com/cpudirect.html
#
import os
import subprocess
import glob
import re
import json
from importlib.metadata import version as get_version
from typing import Any, Dict, List, Optional, TypedDict, cast

import typer
from rich.console import Console


# Type definitions
USB_CLASS_HID = "03"
USB_CLASS_HUB = "09"
USB_CLASS_CONTROLLER = "0c03"
USB_CLASS_AUDIO = "01"
USB_CLASS_VIDEO = "0e"
USB_CLASS_WIRELESS = "e0"

DEVICE_CLASSES = (USB_CLASS_HID, USB_CLASS_AUDIO, USB_CLASS_VIDEO)

DEVICE_CLASS_NAMES = {
    "hid": USB_CLASS_HID,
    "audio": USB_CLASS_AUDIO,
    "video": USB_CLASS_VIDEO,
    "wireless": USB_CLASS_WIRELESS,
    "hub": USB_CLASS_HUB,
    "controller": USB_CLASS_CONTROLLER,
}

PCI_SLOT_PATTERN = re.compile(r"^[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f]$")
USB_DEVICE_PATTERN = re.compile(r"^\d+-\d+(\.\d+)*$")
HID_NAME_FILTER = re.compile(
    r"HID-compliant (mouse|keyboard|device|vendor|consumer|system)", re.I
)
GENERIC_NAME_FILTER = re.compile(r"^USB Input Device$|^HID Keyboard Device$", re.I)


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
        output = subprocess.check_output(
            ["lspci", "-s", pci_slot], stderr=subprocess.DEVNULL, encoding="utf-8"
        ).strip()
        # Output ex: 05:00.4 USB controller: Advanced Micro Devices, Inc. [AMD] Device 14c9 (rev da)
        # We want the part after "USB controller: "
        if "USB controller:" in output:
            return output.split("USB controller:", 1)[1].strip()
        return output
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return f"Unknown Controller [{pci_slot}]"


def is_cpu_controller(pci_name: str, pci_slot: str, force_cpu: bool = False) -> bool:
    """
    Heuristic to determine if a controller is CPU-direct or Chipset.
    Based on common naming patterns.
    """
    if force_cpu:
        return True

    name_lower = pci_name.lower()

    # Strong indicators of CPU-direct (AMD/Intel naming patterns)
    if "amd" in name_lower and ("usb" in name_lower or "xhc" in name_lower):
        return True
    if "intel" in name_lower and ("xhci" in name_lower or "usb" in name_lower):
        return True

    # Strong indicators of Chipset/External
    if "chipset" in name_lower:
        return False
    if "asmedia" in name_lower:
        return False
    if "via" in name_lower or "nec" in name_lower:
        return False
    if "promontory" in name_lower:
        return False

    # Default to False (unknown - assume Chipset for safety)
    return False


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
        if PCI_SLOT_PATTERN.match(base):
            controller_pci = base
            break

        if base.startswith("usb") and base[3:].isdigit():
            # This is the root hub (e.g. usb3), pass through to parent
            pass
        elif USB_DEVICE_PATTERN.match(base):
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


app = typer.Typer(help="Check USB device connection path (CPU vs Chipset).")
console = Console()


def main(
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
    csv_output: bool = typer.Option(False, "--csv", help="Output in CSV format"),
    table_output: bool = typer.Option(False, "--table", help="Output in table format"),
    format: Optional[str] = typer.Option(
        None,
        "--format",
        "-f",
        help="Output format: json, csv, table",
    ),
    only_best: bool = typer.Option(
        False, "--only-best", help="Show only devices with BEST status"
    ),
    show_all: bool = typer.Option(
        False, "--show-all", help="Show all device classes (not just input devices)"
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write output to file (for json/csv formats)",
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Show verbose debug info"
    ),
    quiet: bool = typer.Option(
        False, "-q", "--quiet", help="Suppress non-essential output"
    ),
    summary: bool = typer.Option(
        False, "--summary", help="Show only a summary of device counts"
    ),
    device_class: Optional[List[str]] = typer.Option(
        None,
        "--device-class",
        "-d",
        help="Filter by device class (hid, audio, video, wireless)",
    ),
    controller: Optional[str] = typer.Option(
        None,
        "--controller",
        "-c",
        help="Show only devices on a specific controller (partial name match)",
    ),
    version: bool = typer.Option(False, "--version", help="Show version"),
) -> None:
    if version:
        try:
            prog_version = get_version("cpu-direct-usb-linux")
        except Exception:
            prog_version = "1.0.0"
        typer.echo(prog_version)
        raise typer.Exit()

    # Determine output mode first for console setup
    if format:
        format = format.lower()
        if format == "json":
            json_output = True
        elif format == "csv":
            csv_output = True
        elif format == "table":
            table_output = True
        else:
            typer.echo(
                f"Error: Unknown format '{format}'. Use json, csv, or table.", err=True
            )
            raise typer.Exit(1)

    if no_color or json_output or csv_output or table_output:
        Colors.disable()
        console = Console(force_terminal=False)
    else:
        console = Console()

    if (
        subprocess.call(
            ["which", "lspci"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        != 0
    ):
        error_msg = "lspci command not found. Please install pciutils (e.g., sudo apt install pciutils)."
        if csv_output:
            print("error,message")
            print(f'1,"{error_msg}"')
        elif json_output:
            print(json.dumps({"error": error_msg}))
        else:
            console.print(f"[bold red]Error: {error_msg}[/]")
        raise typer.Exit(1)

    controllers: Dict[str, Dict[str, Any]] = {}
    data: OutputData = {"controllers": [], "devices": [], "error": None}

    try:
        lspci_out = subprocess.check_output(
            ["lspci", "-nn"], stderr=subprocess.DEVNULL, encoding="utf-8"
        ).splitlines()
        for line in lspci_out:
            if "USB controller" in line or USB_CLASS_CONTROLLER in line:
                parts = line.split(" ", 1)
                if len(parts) < 2:
                    continue
                slot = parts[0]

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

                    if not json_output and not quiet:
                        prefix = (
                            "[green][CPU][/]    " if is_cpu else "[dim][Chipset][/]"
                        )
                        console.print(f"  {prefix} [white]{name}[/]")

    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
        if json_output:
            data["error"] = f"Error scanning controllers: {e}"
        else:
            console.print(f"[bold red]Error scanning controllers: {e}[/]")

    if not json_output and not quiet:
        console.print("")

    if not json_output and not quiet:
        console.print("[bold yellow]CONTROLLERS[/]")

    found_any = False

    usb_devices = glob.glob("/sys/bus/usb/devices/*")

    for dev_path in usb_devices:
        base = os.path.basename(dev_path)
        if ":" in base or "-" not in base:
            continue

        product_name = read_file_content(
            os.path.join(dev_path, "product"), "Unknown Device"
        )
        vid = read_file_content(os.path.join(dev_path, "idVendor"))
        pid = read_file_content(os.path.join(dev_path, "idProduct"))

        if not vid or not pid:
            continue

        is_supported_device = False
        device_classes: List[str] = []
        interfaces = glob.glob(os.path.join(dev_path, "*:*.*/bInterfaceClass"))
        for iface_class_file in interfaces:
            class_code = read_file_content(iface_class_file)
            if class_code in DEVICE_CLASSES:
                is_supported_device = True
                device_classes.append(class_code)

        if read_file_content(os.path.join(dev_path, "bDeviceClass")) == USB_CLASS_HUB:
            continue

        if not is_supported_device and not show_all:
            if verbose:
                dev_class = read_file_content(os.path.join(dev_path, "bDeviceClass"))
                console.print(f"  [dim]Skipping {product_name} (class {dev_class})[/]")
            continue

        # For --show-all, include devices even without recognized interface classes
        if not is_supported_device and show_all:
            is_supported_device = True
            device_classes = [
                read_file_content(os.path.join(dev_path, "bDeviceClass"), "Unknown")
            ]

        # Filter by device class if specified
        if device_class:
            filtered_classes = [
                DEVICE_CLASS_NAMES.get(dc.lower()) for dc in device_class
            ]
            filtered_classes = [c for c in filtered_classes if c]
            if not any(dc in device_classes for dc in filtered_classes):
                if verbose:
                    console.print(
                        f"  [dim]Skipping {product_name} (not in requested classes)[/]"
                    )
                continue

        found_any = True

        info = get_usb_info(dev_path)
        if not info or not info["controller_pci"]:
            continue

        pci_slot = info["controller_pci"]
        ctrl_info = (
            controllers.get(pci_slot, {"name": "Unknown", "is_cpu": False})
            if pci_slot
            else {"name": "Unknown", "is_cpu": False}
        )

        # Filter by controller if specified
        if controller and controller.lower() not in ctrl_info["name"].lower():
            if verbose:
                console.print(
                    f"  [dim]Skipping {product_name} (not on controller {controller})[/]"
                )
            continue

        is_cpu = ctrl_info["is_cpu"]
        has_hub = info["hub_count"] > 0

        if is_cpu and not has_hub:
            status = "BEST"
        elif is_cpu and has_hub:
            status = "HUB"
        elif not is_cpu and not has_hub:
            status = "CHIPSET"
        else:
            status = "CHIPSET+HUB"

        if only_best and status != "BEST":
            continue

        device_data = {
            "name": product_name,
            "vid_pid": f"{vid}:{pid}",
            "controller": ctrl_info["name"],
            "controller_type": "CPU" if is_cpu else "Chipset",
            "status": status,
            "hubs": info["hubs"] if has_hub else [],
        }
        data["devices"].append(cast(DeviceInfo, device_data))

        if not json_output and not quiet:
            if found_any:
                console.print("")
            console.print("[bold yellow]DEVICES[/]")
            console.print("")
            console.print(f"  [white]{product_name}[/]")
            console.print(f"  [dim]VID:PID {vid}:{pid}[/]")

            ct_prefix = "green" if is_cpu else "yellow"
            ct_suffix = "(direct to CPU die)" if is_cpu else "(extra latency)"
            console.print(
                f"  [dim]Controller: [{ct_prefix}]{ctrl_info['name']}[/] [dim]{ct_suffix}[/]"
            )

            if has_hub:
                hub_names = ", ".join(info["hubs"]) if info["hubs"] else "Yes"
                console.print(f"  [dim]Hub: [yellow]YES - {hub_names}[/]")

            status_color = (
                "green"
                if status == "BEST"
                else "yellow"
                if status in ["HUB", "CHIPSET"]
                else "red"
            )
            console.print(f"  [dim]Status: [{status_color}][{status}][/]")

    # Calculate summary
    status_counts: Dict[str, int] = {
        "BEST": 0,
        "HUB": 0,
        "CHIPSET": 0,
        "CHIPSET+HUB": 0,
    }
    for dev in data["devices"]:
        status_counts[dev["status"]] = status_counts.get(dev["status"], 0) + 1

    if summary:
        console.print("")
        console.print("[bold yellow]Summary:[/]")
        console.print(f"  [green]BEST:        {status_counts['BEST']}[/]")
        console.print(f"  [yellow]HUB:         {status_counts['HUB']}[/]")
        console.print(f"  [yellow]CHIPSET:     {status_counts['CHIPSET']}[/]")
        console.print(f"  [red]CHIPSET+HUB: {status_counts['CHIPSET+HUB']}[/]")
        console.print(f"  [dim]Total:       {len(data['devices'])}[/]")
        console.print("")

    if not json_output and not quiet:
        if not found_any:
            console.print("\n  [dim]No supported USB devices found.[/]")

        console.print("")
        console.print(
            "[cyan]============================================================[/]"
        )
        console.print("")
        console.print("[bold yellow]STATUS GUIDE:[/]")
        console.print(
            "  [green][BEST]        [/][dim]CPU-direct, no hub - lowest possible latency[/]"
        )
        console.print(
            "  [yellow][HUB]         [/][dim]CPU-direct but through a hub - try another port[/]"
        )
        console.print(
            "  [yellow][CHIPSET]     [/][dim]Chipset USB - move to CPU port if available[/]"
        )
        console.print(
            "  [red][CHIPSET+HUB] [/][dim]Worst path - definitely move this device[/]"
        )
        console.print("")

    if json_output:
        output_str = json.dumps(data, indent=2)
        if output_file:
            with open(output_file, "w") as f:
                f.write(output_str)
        else:
            print(output_str)
    elif csv_output:
        import csv
        import io

        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(
            ["Name", "VID:PID", "Controller", "Controller Type", "Status", "Hubs"]
        )
        for dev in data["devices"]:
            csv_writer.writerow(
                [
                    dev["name"],
                    dev["vid_pid"],
                    dev["controller"],
                    dev["controller_type"],
                    dev["status"],
                    ", ".join(dev["hubs"]) if dev["hubs"] else "",
                ]
            )
        csv_str = csv_buffer.getvalue()
        if output_file:
            with open(output_file, "w") as f:
                f.write(csv_str)
        else:
            print(csv_str)
    elif table_output:
        from rich.table import Table

        table = Table(title="USB Devices")
        table.add_column("Name", style="white")
        table.add_column("VID:PID", style="dim")
        table.add_column("Controller", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Hubs", style="yellow")

        for dev in data["devices"]:
            status_style = (
                "green"
                if dev["status"] == "BEST"
                else "yellow"
                if dev["status"] in ["HUB", "CHIPSET"]
                else "red"
            )
            table.add_row(
                dev["name"],
                dev["vid_pid"],
                dev["controller"][:40] + "..."
                if len(dev["controller"]) > 40
                else dev["controller"],
                f"[{status_style}]{dev['status']}[/{status_style}]",
                ", ".join(dev["hubs"]) if dev["hubs"] else "-",
            )
        console.print(table)


if __name__ == "__main__":
    app()
