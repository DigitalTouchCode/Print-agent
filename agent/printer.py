"""Direct USB access to ESC/POS thermal printers via pyusb + libusb.

This is the same low-level approach the browser's WebUSB code was taking
(claim the printer-class interface, bulk-transfer OUT raw ESC/POS bytes) —
the difference is this runs as a native process, so it only needs the
WinUSB driver bound once (via Zadig, see the setup guide) rather than
fighting Chrome's per-origin WebUSB permission model and the OS printer
driver every time.
"""
import logging

import usb.backend.libusb1
import usb.core
import usb.util

logger = logging.getLogger("dt_print_agent")

USB_CLASS_PRINTER = 7


def _backend():
    """Locate libusb-1.0 via the bundled `libusb` PyPI package.

    Falls back to pyusb's default search (system-installed libusb) if the
    `libusb` package isn't available for some reason.
    """
    try:
        import libusb

        return usb.backend.libusb1.get_backend(find_library=lambda x: libusb.dll)
    except Exception:
        logger.warning("Bundled libusb not found, falling back to system libusb")
        return usb.backend.libusb1.get_backend()


_BACKEND = _backend()


def _candidate_devices():
    """All USB devices that look like they could be a receipt printer.

    Prefers devices exposing the standard USB printer class (7) on any
    interface, but also includes any device with a bulk OUT endpoint so
    printers that don't declare the standard class still show up — same
    permissive approach the WebUSB `pairUsb()` picker used.
    """
    for dev in usb.core.find(find_all=True, backend=_BACKEND):
        try:
            for cfg in dev:
                for intf in cfg:
                    is_printer_class = intf.bInterfaceClass == USB_CLASS_PRINTER
                    has_bulk_out = any(
                        usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT
                        and usb.util.endpoint_type(ep.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK
                        for ep in intf
                    )
                    if is_printer_class or has_bulk_out:
                        yield dev, is_printer_class
                        break
                else:
                    continue
                break
        except (usb.core.USBError, NotImplementedError):
            # Some devices refuse descriptor reads without an open handle
            # (e.g. still claimed by another driver) — skip, don't crash
            # the whole scan over one bad device.
            continue


def list_devices() -> list[dict]:
    devices = []
    seen = set()
    for dev, is_printer_class in _candidate_devices():
        key = (dev.idVendor, dev.idProduct, dev.bus, dev.address)
        if key in seen:
            continue
        seen.add(key)
        try:
            product = usb.util.get_string(dev, dev.iProduct) if dev.iProduct else None
        except Exception:
            product = None
        try:
            manufacturer = usb.util.get_string(dev, dev.iManufacturer) if dev.iManufacturer else None
        except Exception:
            manufacturer = None
        devices.append({
            "vendorId": dev.idVendor,
            "productId": dev.idProduct,
            "product": product or f"USB device {dev.idVendor:04x}:{dev.idProduct:04x}",
            "manufacturer": manufacturer,
            "printerClass": is_printer_class,
        })
    # Printer-class devices first — most likely to be the actual receipt printer.
    devices.sort(key=lambda d: not d["printerClass"])
    return devices


class PrinterNotFound(Exception):
    pass


class PrinterWriteError(Exception):
    pass


def send_raw(vendor_id: int, product_id: int, data: bytes) -> None:
    dev = usb.core.find(idVendor=vendor_id, idProduct=product_id, backend=_BACKEND)
    if dev is None:
        raise PrinterNotFound("Printer not found. Check the USB cable and power.")

    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except (NotImplementedError, usb.core.USBError):
        pass  # Windows: no kernel driver concept the same way, this is a no-op

    try:
        dev.set_configuration()
    except usb.core.USBError:
        pass  # already configured

    cfg = dev.get_active_configuration()
    target_intf, out_ep = None, None
    for intf in cfg:
        ep = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: (
                usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
                and usb.util.endpoint_type(e.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK
            ),
        )
        if ep is not None:
            target_intf, out_ep = intf, ep
            if intf.bInterfaceClass == USB_CLASS_PRINTER:
                break  # prefer the standard printer-class interface

    if out_ep is None:
        raise PrinterWriteError("Couldn't find a printable USB endpoint on this device.")

    try:
        usb.util.claim_interface(dev, target_intf.bInterfaceNumber)
        chunk_size = 4096
        for i in range(0, len(data), chunk_size):
            out_ep.write(data[i : i + chunk_size], timeout=5000)
    except usb.core.USBError as e:
        raise PrinterWriteError(
            "Access denied talking to the printer. If this is the first print, "
            "run Zadig once to bind the WinUSB driver — see the setup guide."
        ) from e
    finally:
        try:
            usb.util.release_interface(dev, target_intf.bInterfaceNumber)
        except Exception:
            pass
        usb.util.dispose_resources(dev)
