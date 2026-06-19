import logging

from sqlalchemy import select

from backend.database import AsyncSessionLocal, Base, engine
from backend.models import DocStatus, DocType, Document
from backend.storage import FEDERAL_DOCS_DIR

logger = logging.getLogger("kristall.startup")

ALLOWED_EXT = (".pdf", ".docx")


async def create_tables() -> None:
    """Создаёт таблицы, если их ещё нет."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def scan_federal_docs() -> None:
    """Регистрирует новые файлы из /federal_docs как федеральные документы.

    Анализ НЕ запускается — пользователь триггерит его вручную.
    """
    if not FEDERAL_DOCS_DIR.exists():
        logger.info("Каталог federal_docs отсутствует: %s", FEDERAL_DOCS_DIR)
        return

    files = [
        p
        for p in FEDERAL_DOCS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in ALLOWED_EXT
    ]
    if not files:
        return

    async with AsyncSessionLocal() as session:
        existing = set(
            (
                await session.execute(
                    select(Document.original_name).where(
                        Document.doc_type == DocType.federal
                    )
                )
            )
            .scalars()
            .all()
        )
        added = 0
        for path in files:
            if path.name in existing:
                continue
            session.add(
                Document(
                    filename=path.name,
                    original_name=path.name,
                    doc_type=DocType.federal,
                    status=DocStatus.uploaded,
                )
            )
            added += 1
        if added:
            await session.commit()
            logger.info("Добавлено федеральных документов из federal_docs: %d", added)


async def init() -> None:
    await create_tables()
    await scan_federal_docs()
