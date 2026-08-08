"""Small database scheduler for follow-up reminders and task status transitions."""

from __future__ import annotations

import asyncio
import datetime as dt
import logging

from app.db.base import FollowUp, Notification, Task
from app.db.database import SessionLocal


logger = logging.getLogger(__name__)


def process_due_work() -> None:
    now = dt.datetime.now(dt.UTC).replace(tzinfo=None)
    with SessionLocal() as db:
        due_follow_ups = db.query(FollowUp).filter(
            FollowUp.status.in_(["pending", "scheduled"]),
            FollowUp.reminder_at.is_not(None),
            FollowUp.reminder_at <= now,
        ).all()
        for item in due_follow_ups:
            exists = db.query(Notification).filter(
                Notification.kind == "follow_up_reminder",
                Notification.related_id == item.id,
            ).first()
            if exists is None:
                db.add(
                    Notification(
                        kind="follow_up_reminder",
                        title=item.title,
                        body=f"Follow-up scheduled for {item.scheduled_at.isoformat()}",
                        related_type="follow_up",
                        related_id=item.id,
                    )
                )
        tasks = db.query(Task).filter(Task.status.in_(["upcoming", "today"])).all()
        for item in tasks:
            if item.due_at is None:
                continue
            item.status = "overdue" if item.due_at < now else "today" if item.due_at.date() == now.date() else "upcoming"
        db.commit()


async def scheduler_loop(interval_seconds: float = 30.0) -> None:
    while True:
        try:
            await asyncio.to_thread(process_due_work)
        except Exception:
            logger.exception("scheduler_iteration_failed")
        await asyncio.sleep(interval_seconds)


__all__ = ["process_due_work", "scheduler_loop"]
