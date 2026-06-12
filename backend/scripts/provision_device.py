"""Assign a registered booth device to an event booth and optionally rotate its token.

Recommended flow:
  1. Flash firmware and power on once (auto-registers via POST /device/register, saves token to NVS)
  2. python -m scripts.seed
  3. python -m scripts.provision_device --serial BOOTH-001

Usage (from backend/):

    python -m scripts.provision_device
    python -m scripts.provision_device --serial BOOTH-001 --booth "Booth 1"
    python -m scripts.provision_device --rotate-token   # NVS recovery — flash printed token manually
    python -m scripts.provision_device --create           # Pre-create before first boot (advanced)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import generate_device_token, hash_device_token
from app.db.session import SessionLocal
from app.models.booth import Booth
from app.models.device import Device
from app.models.event import Event


def provision(
    serial: str,
    booth_name: str,
    event_slug: str,
    rotate_token: bool,
    create_if_missing: bool,
    display_name: str | None,
) -> None:
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.slug == event_slug).first()
        if not event:
            raise SystemExit(f"Event '{event_slug}' not found. Run: python -m scripts.seed")

        booth = (
            db.query(Booth)
            .filter(Booth.event_id == event.id, Booth.name == booth_name)
            .first()
        )
        if not booth:
            raise SystemExit(f"Booth '{booth_name}' not found for event '{event_slug}'")

        device = db.query(Device).filter(Device.serial_number == serial).first()
        token: str | None = None

        if device is None:
            if not create_if_missing:
                raise SystemExit(
                    f"Device '{serial}' not registered yet.\n"
                    "Power on the booth once (firmware auto-registers on first Wi-Fi connect),\n"
                    "or re-run with --create to pre-provision (blocks auto-register until token is flashed to NVS)."
                )
            token = generate_device_token()
            device = Device(
                serial_number=serial,
                display_name=display_name or serial,
                firmware_version="provisioned",
                auth_token_hash=hash_device_token(token),
                status="registered",
            )
            db.add(device)
            db.flush()
            print(f"Pre-created device {device.id} ({serial})")
        else:
            print(f"Found device {device.id} ({serial})")
            if rotate_token:
                token = generate_device_token()
                device.auth_token_hash = hash_device_token(token)
                device.status = "registered"
                print("Rotated device token")

        if booth.assigned_device_id and booth.assigned_device_id != device.id:
            prev = db.query(Booth).filter(Booth.id == booth.id).first()
            if prev and prev.assigned_device_id != device.id:
                pass
        other = db.query(Booth).filter(Booth.assigned_device_id == device.id, Booth.id != booth.id).first()
        if other:
            other.assigned_device_id = None
            print(f"Unassigned device from booth '{other.name}'")

        booth.assigned_device_id = device.id
        booth.status = "offline"
        db.commit()

        print("\nProvisioning complete")
        print(f"  Event:  {event.name} ({event.slug})")
        print(f"  Booth:  {booth.name} ({booth.id})")
        print(f"  Device: {device.display_name} ({device.id})")
        print(f"  Serial: {serial}")
        if token:
            print("\n  Device token (shown once):")
            print(f"  {token}")
            print("\n  If firmware NVS is empty, it cannot auto-register when this serial already exists.")
            print("  Either erase NVS and use --create before first boot, or flash this token via serial/NVS tool.")
        else:
            print("\n  Token unchanged. Firmware should already have credentials in NVS from first boot.")
        print("\nFirmware config.h:")
        print(f'  #define DEVICE_SERIAL "{serial}"')
        print(f'  #define API_BASE_URL "http://<your-server>:8000/api/v1"')
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision ESP32 booth device")
    parser.add_argument("--serial", default="BOOTH-001", help="Device serial number")
    parser.add_argument("--booth", default="Booth 1", help="Booth name to assign")
    parser.add_argument("--event-slug", default="demo-wedding", help="Event slug")
    parser.add_argument("--display-name", default=None, help="Optional device display name")
    parser.add_argument(
        "--rotate-token",
        action="store_true",
        help="Generate a new token for an existing device (NVS recovery)",
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Pre-create device in DB before first firmware boot (advanced)",
    )
    args = parser.parse_args()

    provision(
        serial=args.serial,
        booth_name=args.booth,
        event_slug=args.event_slug,
        rotate_token=args.rotate_token,
        create_if_missing=args.create,
        display_name=args.display_name,
    )


if __name__ == "__main__":
    main()
