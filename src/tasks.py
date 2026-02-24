from datetime import datetime, timedelta, timezone

from asgiref.sync import async_to_sync
from sqlalchemy import select

from database import SessionLocal
from src.celery_app import celery_app
from src.models.users import ActivationToken


async def async_delete_expired_tokens():
    async with SessionLocal() as db:
        now = datetime.now(timezone.utc) + timedelta(days=2)
        result = await db.execute(
            select(ActivationToken).where(ActivationToken.expires_at < now)
        )
        expired_tokens = result.scalars().all()

        for token in expired_tokens:
            await db.delete(token)

        await db.commit()
        print(f"Delete {len(expired_tokens)} expired tokens")

        await db.close()


@celery_app.task(name="tasks.delete_expired_tokens")
def delete_expired_tokens():
    return async_to_sync(async_delete_expired_tokens)()
