from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.api_usage import ApiUsage
from app.services.rate_limiter import FMP_DAILY_LIMIT

router = APIRouter()


@router.get("/admin/usage")
async def get_usage(db: AsyncSession = Depends(get_db)) -> dict:
    count = (
        await db.execute(
            select(ApiUsage.call_count).where(ApiUsage.provider == "fmp", ApiUsage.date == date.today())
        )
    ).scalar_one_or_none() or 0
    return {"fmp": {"today": count, "limit": FMP_DAILY_LIMIT, "remaining": max(FMP_DAILY_LIMIT - count, 0)}}
