import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Direction, Document, VerificationStatus
from backend.schemas import DirectionOut, StatusUpdate

router = APIRouter(prefix="/api/directions", tags=["directions"])


@router.get("", response_model=list[DirectionOut])
async def list_directions(
    doc_id: uuid.UUID | None = Query(default=None),
    federal_match: str | None = Query(default=None),
    verification_status: VerificationStatus | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[DirectionOut]:
    stmt = select(Direction, Document.original_name).join(
        Document, Direction.document_id == Document.id
    )
    if doc_id is not None:
        stmt = stmt.where(Direction.document_id == doc_id)
    if federal_match:
        stmt = stmt.where(Direction.federal_match == federal_match)
    if verification_status is not None:
        stmt = stmt.where(Direction.verification_status == verification_status)
    stmt = stmt.order_by(Direction.created_at)

    rows = (await db.execute(stmt)).all()
    out = []
    for direction, doc_name in rows:
        item = DirectionOut.model_validate(direction)
        item.document_name = doc_name
        out.append(item)
    return out


@router.patch("/{direction_id}/status", response_model=DirectionOut)
async def update_status(
    direction_id: uuid.UUID,
    payload: StatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> DirectionOut:
    direction = await db.get(Direction, direction_id)
    if direction is None:
        raise HTTPException(status_code=404, detail="Направление не найдено")

    direction.verification_status = payload.status
    await db.commit()
    await db.refresh(direction)

    document = await db.get(Document, direction.document_id)
    item = DirectionOut.model_validate(direction)
    item.document_name = document.original_name if document else None
    return item
