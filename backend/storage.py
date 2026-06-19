"""Временный буфер для загруженных файлов.

Файлы НЕ хранятся постоянно: байты кладутся во временный системный каталог
между запросами upload и analyze, и удаляются сразу после отправки в Gemini.
Постоянное хранилище файлов — только Gemini File API.
"""

import os
import tempfile
import uuid
from pathlib import Path

_TMP_DIR = Path(tempfile.gettempdir()) / "kristall_uploads"
_TMP_DIR.mkdir(parents=True, exist_ok=True)

# Каталог с пред-загруженными федеральными документами
FEDERAL_DOCS_DIR = Path(__file__).resolve().parent.parent / "federal_docs"


def _path_for(document_id: uuid.UUID) -> Path:
    return _TMP_DIR / f"{document_id}"


def save_temp(document_id: uuid.UUID, data: bytes) -> None:
    """Сохраняет байты во временный буфер."""
    _path_for(document_id).write_bytes(data)


def read_temp(document_id: uuid.UUID) -> bytes | None:
    """Читает байты из временного буфера, если они есть."""
    path = _path_for(document_id)
    return path.read_bytes() if path.exists() else None


def delete_temp(document_id: uuid.UUID) -> None:
    """Удаляет временный буфер (вызывать после загрузки в Gemini)."""
    path = _path_for(document_id)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def read_federal_doc(filename: str) -> bytes | None:
    """Читает пред-загруженный федеральный документ из /federal_docs."""
    path = FEDERAL_DOCS_DIR / filename
    if path.exists() and path.is_file():
        return path.read_bytes()
    return None
