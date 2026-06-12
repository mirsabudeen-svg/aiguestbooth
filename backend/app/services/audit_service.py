from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditService:
    def log(
        self,
        db: Session,
        *,
        actor_type: str,
        actor_id: str | None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    def log_user_action(
        self,
        db: Session,
        user_id: UUID,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        return self.log(
            db,
            actor_type="user",
            actor_id=str(user_id),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )

    def log_device_action(
        self,
        db: Session,
        device_id: UUID,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        return self.log(
            db,
            actor_type="device",
            actor_id=str(device_id),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )


def get_audit_service() -> AuditService:
    return AuditService()
