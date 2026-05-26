from datetime import date

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_usage import ApiUsage

FMP_DAILY_LIMIT = 200


async def can_call_fmp(db: AsyncSession) -> bool:
    result = await db.execute(
        select(ApiUsage.call_count).where(ApiUsage.provider == "fmp", ApiUsage.date == date.today())
    )
    count = result.scalar_one_or_none() or 0
    return count < FMP_DAILY_LIMIT


async def record_fmp_call(db: AsyncSession, count: int = 1) -> None:
    stmt = insert(ApiUsage).values(provider="fmp", date=date.today(), call_count=count)
    stmt = stmt.on_conflict_do_update(
        index_elements=[ApiUsage.provider, ApiUsage.date],
        set_={"call_count": ApiUsage.call_count + count, "updated_at": func.now()},
    )
    await db.execute(stmt)
    await db.commit()
