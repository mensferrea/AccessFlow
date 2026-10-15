from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AuditLog

class AuditService:
    @staticmethod
    async def log_action(
        db: AsyncSession,
        request_id: Optional[int],
        actor_id: Optional[int],
        action: str,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        log_entry = AuditLog(
            request_id=request_id,
            actor_id=actor_id,
            action=action,
            old_status=old_status,
            new_status=new_status,
            details=details or {}
        )
        db.add(log_entry)
        await db.commit()
        await db.refresh(log_entry)
        return log_entry
