import unittest
from unittest.mock import patch, mock_open
import sys
import os
import subprocess
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from usbpeek import (
    read_file_content,
    get_pci_name,
    is_cpu_controller,
    get_usb_info,
    get_polling_rate,
)


class TestUsbPeek(unittest.TestCase):
    def test_read_file_content_success(self) -> None:
        with patch("builtins.open", mock_open(read_data="test content\n")):
            result = read_file_content("/fake/path")
            self.assertEqual(result, "test content")

    def test_read_file_content_default(self) -> None:
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = read_file_content("/fake/path", "default")
            self.assertEqual(result, "default")

    def test_read_file_content_permission_error(self) -> None:
        with patch("builtins.open", side_effect=PermissionError):
            result = read_file_content("/fake/path", "default")
            self.assertEqual(result, "default")

    def test_read_file_content_unicode_error(self) -> None:
        with patch(
            "builtins.open",
            side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid"),
        ):
            result = read_file_content("/fake/path", "default")
            self.assertEqual(result, "default")

    @patch("subprocess.check_output")
    def test_get_pci_name_success(self, mock_subprocess: Any) -> None:
        mock_subprocess.return_value = "05:00.4 USB controller: Test Controller"
        result = get_pci_name("05:00.4")
        self.assertEqual(result, "Test Controller")

    @patch("subprocess.check_output")
    def test_get_pci_name_no_usb(self, mock_subprocess: Any) -> None:
        mock_subprocess.return_value = "05:00.4 Some other device"
        result = get_pci_name("05:00.4")
        self.assertEqual(result, "05:00.4 Some other device")

    @patch(
        "subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "lspci")
    )
    def test_get_pci_name_exception(self, mock_subprocess: Any) -> None:
        result = get_pci_name("05:00.4")
        self.assertEqual(result, "Unknown Controller [05:00.4]")

    def test_is_cpu_controller_chipset(self) -> None:
        self.assertFalse(is_cpu_controller("Chipset USB Controller", "00:00.0"))

    def test_is_cpu_controller_asmedia(self) -> None:
        self.assertFalse(is_cpu_controller("ASMedia Technology Inc.", "00:00.0"))

    def test_is_cpu_controller_via(self) -> None:
        self.assertFalse(is_cpu_controller("VIA Technologies", "00:00.0"))

    def test_is_cpu_controller_cpu(self) -> None:
        self.assertTrue(is_cpu_controller("AMD USB Controller", "00:00.0"))

    def test_is_cpu_controller_renesas(self) -> None:
        self.assertFalse(
            is_cpu_controller("Renesas Electronics Corp. uPD720200", "00:00.0")
        )

    def test_is_cpu_controller_promontory(self) -> None:
        self.assertFalse(is_cpu_controller("AMD Promontory", "00:00.0"))

    def test_is_cpu_controller_intel(self) -> None:
        self.assertTrue(
            is_cpu_controller("Intel Corporation USB 3.2 Gen 2x2", "00:00.0")
        )

    def test_is_cpu_controller_fresco(self) -> None:
        self.assertFalse(is_cpu_controller("Fresco Logic FL1100", "00:00.0"))

    def test_is_cpu_controller_vl805(self) -> None:
        self.assertFalse(is_cpu_controller("VIA Labs VL805", "00:00.0"))

    @patch("os.path.realpath")
    @patch("os.path.dirname")
    @patch("os.path.basename")
    @patch("usbpeek.read_file_content")
    def test_get_usb_info_no_realpath(
        self, mock_read: Any, mock_basename: Any, mock_dirname: Any, mock_realpath: Any
    ) -> None:
        mock_realpath.side_effect = OSError
        result = get_usb_info("/fake/path")
        self.assertIsNone(result)

    @patch("os.path.realpath")
    def test_get_usb_info_pci_found(self, mock_realpath: Any) -> None:
        mock_realpath.return_value = "/sys/devices/pci0000:00/0000:00:14.0"
        result = get_usb_info("/fake/path")
        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result["controller_pci"], "0000:00:14.0")

    @patch("usbpeek.read_file_content")
    def test_get_polling_rate_high_speed(self, mock_read: Any) -> None:
        def mock_file_content(path: str, default: str = "") -> str:
            basename = os.path.basename(path)
            if basename == "bInterval":
                return "4"
            if basename == "speed":
                return "480"
            return default

        mock_read.side_effect = mock_file_content
        result = get_polling_rate("/sys/bus/usb/devices/1-1")
        self.assertEqual(result, 1000)

    @patch("usbpeek.read_file_content")
    def test_get_polling_rate_full_speed(self, mock_read: Any) -> None:
        def mock_file_content(path: str, default: str = "") -> str:
            basename = os.path.basename(path)
            if basename == "bInterval":
                return "8"
            if basename == "speed":
                return "12"
            return default

        mock_read.side_effect = mock_file_content
        result = get_polling_rate("/sys/bus/usb/devices/1-1")
        self.assertEqual(result, 125)

    @patch("usbpeek.read_file_content")
    def test_get_polling_rate_no_binterval(self, mock_read: Any) -> None:
        mock_read.return_value = ""
        result = get_polling_rate("/sys/bus/usb/devices/1-1")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
