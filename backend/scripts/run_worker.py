"""Poll and run queued AI processing jobs.

Usage (from backend/):
    python -m scripts.run_worker

Runs until interrupted. Useful when not using in-process thread scheduler.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models.processing_job import ProcessingJob
from app.workers.jobs import run_full_pipeline

POLL_SECONDS = 5


def main() -> None:
    print("AI worker started — polling for queued jobs")
    while True:
        db = SessionLocal()
        try:
            jobs = (
                db.query(ProcessingJob)
                .filter(ProcessingJob.status == "queued")
                .order_by(ProcessingJob.created_at.asc())
                .limit(5)
                .all()
            )
            for job in jobs:
                print(f"Running job {job.id} for message {job.audio_message_id}")
                run_full_pipeline(job.audio_message_id, job_id=job.id)
        finally:
            db.close()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
