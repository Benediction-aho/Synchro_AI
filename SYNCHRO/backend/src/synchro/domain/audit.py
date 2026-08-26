from sqlalchemy import select
from sqlalchemy.orm import Session

from synchro.db.models.system import ActorType, AuditLog


def record(db: Session, actor: ActorType, action: str, reason: str | None = None) -> AuditLog:
    entry = AuditLog(actor=actor, action=action[:128], reason=reason)
    db.add(entry)
    db.flush()
    return entry


def count_actions(db: Session, action_prefix: str) -> int:
    stmt = select(AuditLog).where(AuditLog.action.like(f"{action_prefix}%"))
    return len(list(db.scalars(stmt).all()))
