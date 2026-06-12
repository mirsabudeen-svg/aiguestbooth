"""Seed demo event, booth, and operator user.

Usage (from backend/):
    python -m scripts.seed
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.booth import Booth
from app.models.event import Event
from app.models.user import User


def seed() -> None:
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "operator@booth.local").first():
            db.add(
                User(
                    email="operator@booth.local",
                    password_hash=hash_password("booth123"),
                    role="admin",
                )
            )

        if not db.query(Event).filter(Event.slug == "demo-wedding").first():
            event = Event(
                name="Demo Wedding",
                slug="demo-wedding",
                event_type="wedding",
                venue="Grand Ballroom",
                max_record_seconds=120,
                is_active=True,
            )
            db.add(event)
            db.flush()
            db.add(Booth(event_id=event.id, name="Booth 1", location_label="Near dance floor"))

        db.commit()
        print("Seed complete.")
        print("  Operator login: operator@booth.local / booth123")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
