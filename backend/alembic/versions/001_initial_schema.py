"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(50), server_default="wedding"),
        sa.Column("start_at", sa.DateTime(timezone=True)),
        sa.Column("end_at", sa.DateTime(timezone=True)),
        sa.Column("venue", sa.String(255)),
        sa.Column("branding_json", postgresql.JSONB),
        sa.Column("prompt_audio_url", sa.Text()),
        sa.Column("thank_you_audio_url", sa.Text()),
        sa.Column("max_record_seconds", sa.Integer(), server_default="120"),
        sa.Column("language_mode", sa.String(20), server_default="auto"),
        sa.Column("moderation_enabled", sa.Boolean(), server_default="true"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_events_slug", "events", ["slug"], unique=True)

    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("serial_number", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(100)),
        sa.Column("firmware_version", sa.String(50)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("battery_level", sa.Integer()),
        sa.Column("wifi_strength", sa.Integer()),
        sa.Column("current_state", sa.String(30)),
        sa.Column("status", sa.String(30), server_default="registered"),
        sa.Column("auth_token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_devices_serial_number", "devices", ["serial_number"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), server_default="operator"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "booths",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("location_label", sa.String(255)),
        sa.Column("status", sa.String(30), server_default="offline"),
        sa.Column("assigned_device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id"), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_booths_event_id", "booths", ["event_id"])
    op.create_index("ix_booths_status", "booths", ["status"])

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("booth_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("booths.id"), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("trigger_type", sa.String(20), server_default="button"),
        sa.Column("status", sa.String(30), server_default="started"),
        sa.Column("upload_status", sa.String(30), server_default="pending"),
        sa.Column("local_reference", sa.String(100)),
    )
    op.create_index("ix_sessions_event_id", "sessions", ["event_id"])
    op.create_index("ix_sessions_booth_id", "sessions", ["booth_id"])
    op.create_index("ix_sessions_device_id", "sessions", ["device_id"])
    op.create_index("ix_sessions_status", "sessions", ["status"])
    op.create_index("ix_sessions_upload_status", "sessions", ["upload_status"])

    op.create_table(
        "audio_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("raw_audio_path", sa.Text(), nullable=False),
        sa.Column("normalized_audio_path", sa.Text()),
        sa.Column("duration_seconds", sa.Float()),
        sa.Column("file_size_bytes", sa.Integer()),
        sa.Column("mime_type", sa.String(50), server_default="audio/wav"),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audio_messages_session_id", "audio_messages", ["session_id"], unique=True)
    op.create_index("ix_audio_messages_checksum", "audio_messages", ["checksum"])

    op.create_table(
        "transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("audio_message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audio_messages.id"), nullable=False),
        sa.Column("transcript_text", sa.Text()),
        sa.Column("cleaned_text", sa.Text()),
        sa.Column("summary_text", sa.Text()),
        sa.Column("sentiment_label", sa.String(50)),
        sa.Column("moderation_label", sa.String(30), server_default="pending"),
        sa.Column("language_code", sa.String(10)),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_transcripts_audio_message_id", "transcripts", ["audio_message_id"], unique=True)

    op.create_table(
        "message_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("audio_message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audio_messages.id"), nullable=False),
        sa.Column("tag", sa.String(50), nullable=False),
        sa.UniqueConstraint("audio_message_id", "tag", name="uq_message_tag"),
    )
    op.create_index("ix_message_tags_audio_message_id", "message_tags", ["audio_message_id"])

    op.create_table(
        "operator_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("audio_message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audio_messages.id"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("note_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_operator_notes_audio_message_id", "operator_notes", ["audio_message_id"])

    op.create_table(
        "export_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("status", sa.String(30), server_default="queued"),
        sa.Column("format", sa.String(20), server_default="zip"),
        sa.Column("output_path", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_export_jobs_event_id", "export_jobs", ["event_id"])
    op.create_index("ix_export_jobs_status", "export_jobs", ["status"])

    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("audio_message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audio_messages.id"), nullable=False),
        sa.Column("job_type", sa.String(50), server_default="full_pipeline"),
        sa.Column("status", sa.String(30), server_default="queued"),
        sa.Column("attempts", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_processing_jobs_audio_message_id", "processing_jobs", ["audio_message_id"])
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_type", sa.String(20)),
        sa.Column("actor_id", sa.String(100)),
        sa.Column("action", sa.String(50)),
        sa.Column("resource_type", sa.String(50)),
        sa.Column("resource_id", sa.String(100)),
        sa.Column("details", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("processing_jobs")
    op.drop_table("export_jobs")
    op.drop_table("operator_notes")
    op.drop_table("message_tags")
    op.drop_table("transcripts")
    op.drop_table("audio_messages")
    op.drop_table("sessions")
    op.drop_table("booths")
    op.drop_table("users")
    op.drop_table("devices")
    op.drop_table("events")
