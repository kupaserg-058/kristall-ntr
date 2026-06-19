from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Direction, Document, VerificationStatus
from backend.schemas import FederalDirectionStat, StatsOut

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
async def get_stats(db: AsyncSession = Depends(get_db)) -> StatsOut:
    total_documents = await db.scalar(select(func.count(Document.id))) or 0
    total_directions = await db.scalar(select(func.count(Direction.id))) or 0
    confirmed = (
        await db.scalar(
            select(func.count(Direction.id)).where(
                Direction.verification_status == VerificationStatus.confirmed
            )
        )
        or 0
    )
    pending = (
        await db.scalar(
            select(func.count(Direction.id)).where(
                Direction.verification_status == VerificationStatus.pending
            )
        )
        or 0
    )

    by_federal_rows = (
        await db.execute(
            select(Direction.federal_match, func.count(Direction.id))
            .where(Direction.federal_match.is_not(None))
            .group_by(Direction.federal_match)
            .order_by(func.count(Direction.id).desc())
        )
    ).all()

    by_federal = [
        FederalDirectionStat(name=name, count=count) for name, count in by_federal_rows
    ]

    return StatsOut(
        total_documents=total_documents,
        total_directions=total_directions,
        confirmed=confirmed,
        pending=pending,
        by_federal_direction=by_federal,
    )
