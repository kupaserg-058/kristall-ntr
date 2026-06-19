import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import storage
from backend.database import get_db
from backend.gemini import analyze_document
from backend.models import Direction, DocStatus, DocType, Document
from backend.schemas import AnalyzeResponse, DirectionOut, DocumentOut

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXT = (".pdf", ".docx")
MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


async def _documents_with_counts(db: AsyncSession, document_id: uuid.UUID | None = None):
    """Возвращает документы вместе с количеством направлений."""
    count_subq = (
        select(Direction.document_id, func.count(Direction.id).label("cnt"))
        .group_by(Direction.document_id)
        .subquery()
    )
    stmt = select(Document, func.coalesce(count_subq.c.cnt, 0)).outerjoin(
        count_subq, Document.id == count_subq.c.document_id
    )
    if document_id is not None:
        stmt = stmt.where(Document.id == document_id)
    else:
        stmt = stmt.order_by(Document.uploaded_at.desc())
    result = await db.execute(stmt)
    return result.all()


def _to_out(document: Document, count: int) -> DocumentOut:
    out = DocumentOut.model_validate(document)
    out.directions_count = count
    return out


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: DocType = Form(...),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    original_name = file.filename or "document"
    ext = "." + original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail="Поддерживаются только файлы .pdf и .docx",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Файл пустой")

    document = Document(
        filename=original_name,
        original_name=original_name,
        doc_type=doc_type,
        status=DocStatus.uploaded,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Байты — только во временный буфер (постоянное хранилище — Gemini File API)
    storage.save_temp(document.id, data)

    return _to_out(document, 0)


@router.get("", response_model=list[DocumentOut])
async def list_documents(db: AsyncSession = Depends(get_db)) -> list[DocumentOut]:
    rows = await _documents_with_counts(db)
    return [_to_out(doc, count) for doc, count in rows]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> DocumentOut:
    rows = await _documents_with_counts(db, document_id)
    if not rows:
        raise HTTPException(status_code=404, detail="Документ не найден")
    doc, count = rows[0]
    return _to_out(doc, count)


@router.post("/{document_id}/analyze", response_model=AnalyzeResponse)
async def analyze(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # Источник байтов: временный буфер (пользовательская загрузка)
    # или пред-загруженный файл из /federal_docs.
    data = storage.read_temp(document_id)
    if data is None:
        data = storage.read_federal_doc(document.original_name)
    if data is None:
        raise HTTPException(
            status_code=400,
            detail="Файл недоступен для анализа (буфер пуст). Загрузите документ заново.",
        )

    ext = (
        "." + document.original_name.rsplit(".", 1)[-1].lower()
        if "." in document.original_name
        else ""
    )
    mime_type = MIME_BY_EXT.get(ext, "application/octet-stream")

    background_tasks.add_task(
        analyze_document, document_id, data, mime_type, document.original_name
    )
    return AnalyzeResponse(status="analyzing")


@router.get("/{document_id}/directions", response_model=list[DirectionOut])
async def document_directions(
    document_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> list[DirectionOut]:
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Документ не найден")
    result = await db.execute(
        select(Direction)
        .where(Direction.document_id == document_id)
        .order_by(Direction.created_at)
    )
    directions = result.scalars().all()
    out = []
    for d in directions:
        item = DirectionOut.model_validate(d)
        item.document_name = document.original_name
        out.append(item)
    return out
