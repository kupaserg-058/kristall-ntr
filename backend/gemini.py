import asyncio
import io
import json
import logging
import pathlib
import uuid

from google import genai
from google.genai import types

from backend import storage
from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models import Confidence, Direction, DocStatus, Document, VerificationStatus

logger = logging.getLogger("kristall.gemini")

MODEL = "gemini-2.5-flash"
CHUNK_SIZE = 12_000      # символов на чанк (~3-4 страницы текста)
MAX_RETRIES = 3          # попыток на чанк при 503/429
RETRY_DELAY = 8          # секунд между попытками

_HIERARCHY_FILE = pathlib.Path(__file__).parent.parent / "ntr_hierarchy_final.json"


# ── Иерархия НТР ────────────────────────────────────────────────────────────

def _build_hierarchy_text() -> str:
    try:
        data = json.loads(_HIERARCHY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return ""
    lines: list[str] = []
    for d in data.get("directions", []):
        lines.append(f"\n{d['id']}. {d['title']}")
        for c in d.get("children", []):
            lines.append(f"   • {c['title']}")
            for g in c.get("children", []):
                lines.append(f"     – {g['title']}")
    for item in data.get("unmatched", []):
        lines.append(f"   • {item['title']}")
    return "\n".join(lines)


_HIERARCHY_TEXT = _build_hierarchy_text()

SYSTEM_INSTRUCTION = f"""Ты — эксперт по анализу стратегических документов в сфере \
научно-технологического развития России.

Ниже приведена полная иерархия приоритетных направлений НТР (Указ №529 от 18.06.2024 \
и конкретизирующие документы).

Уровень 1 — 7 федеральных приоритетов. Уровень 2/3 — детализация.

{_HIERARCHY_TEXT}

Твоя задача: найди ВСЕ конкретные мероприятия, задачи и направления в сфере науки и \
технологий. Для каждого определи наиболее подходящее направление уровня 1 (или null).

Отвечай СТРОГО в формате JSON без markdown:
{{
  "directions": [
    {{
      "title": "точное название как в документе",
      "federal_match": "одно из 7 направлений или null",
      "fragment": "цитата до 400 символов",
      "confidence": "high | medium | low"
    }}
  ]
}}"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "directions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "federal_match": {"type": "string", "nullable": True},
                    "fragment": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["title", "fragment", "confidence"],
            },
        }
    },
    "required": ["directions"],
}


# ── Ротация ключей ───────────────────────────────────────────────────────────

class KeyRotator:
    """Циклически переключает Gemini-клиентов при ошибках 429/503."""

    def __init__(self, keys: list[str]) -> None:
        if not keys:
            raise RuntimeError("GEMINI_API_KEY не задан")
        self._clients = [genai.Client(api_key=k) for k in keys]
        self._index = 0
        logger.info("Gemini: загружено %d ключ(ей)", len(self._clients))

    @property
    def current(self) -> genai.Client:
        return self._clients[self._index]

    def rotate(self) -> genai.Client:
        """Переключиться на следующий ключ."""
        self._index = (self._index + 1) % len(self._clients)
        logger.warning("Gemini: переключение на ключ #%d", self._index)
        return self._clients[self._index]


_rotator: KeyRotator | None = None


def get_rotator() -> KeyRotator:
    global _rotator
    if _rotator is None:
        _rotator = KeyRotator(settings.gemini_api_keys)
    return _rotator


# ── Извлечение текста ────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Извлекает текст из PDF локально через pymupdf."""
    import fitz  # pymupdf

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    parts: list[str] = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            parts.append(text)
    doc.close()
    return "\n".join(parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Извлекает текст из .docx (параграфы + таблицы)."""
    from docx import Document as DocxDocument

    doc = DocxDocument(io.BytesIO(file_bytes))
    parts: list[str] = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """Разбивает текст на чанки по абзацам, не превышая chunk_size символов."""
    paragraphs = [p for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > chunk_size and current:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += len(para)

    if current:
        chunks.append("\n".join(current))

    return chunks


# ── Анализ одного чанка с retry ──────────────────────────────────────────────

async def _analyze_chunk(text: str, chunk_num: int, total: int) -> list[dict]:
    """Отправляет один чанк в Gemini, возвращает список direction-объектов."""
    rotator = get_rotator()
    prompt = (
        f"[Часть {chunk_num} из {total}]\n\n"
        "Проанализируй фрагмент документа согласно инструкции и верни JSON.\n\n"
        f"Текст:\n{text}"
    )

    for attempt in range(MAX_RETRIES):
        try:
            client = rotator.current
            response = await client.aio.models.generate_content(
                model=MODEL,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                ),
            )
            data = _parse_response(response.text or "")
            directions = data.get("directions", [])
            logger.info(
                "Чанк %d/%d: найдено %d направлений", chunk_num, total, len(directions)
            )
            return directions

        except Exception as exc:
            err = str(exc)
            is_retryable = any(
                code in err for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")
            )
            if is_retryable and attempt < MAX_RETRIES - 1:
                # Если несколько ключей — переключаемся, иначе просто ждём
                if len(get_rotator()._clients) > 1:
                    rotator.rotate()
                delay = RETRY_DELAY * (attempt + 1)
                logger.warning(
                    "Чанк %d/%d: %s, retry %d/%d через %ds",
                    chunk_num, total, err[:80], attempt + 1, MAX_RETRIES, delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error("Чанк %d/%d не обработан: %s", chunk_num, total, err[:200])
                return []  # пропускаем чанк, не роняем весь документ

    return []


# ── Дедупликация ─────────────────────────────────────────────────────────────

def _deduplicate(directions: list[dict]) -> list[dict]:
    """Убирает дубли по title (нормализуем до нижнего регистра)."""
    seen: set[str] = set()
    result: list[dict] = []
    for d in directions:
        key = (d.get("title") or "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(d)
    return result


# ── Вспомогательные ─────────────────────────────────────────────────────────

def _parse_response(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)


def _map_confidence(value: str | None) -> Confidence:
    try:
        return Confidence(value)
    except (ValueError, TypeError):
        return Confidence.medium


# ── Главная функция ──────────────────────────────────────────────────────────

async def analyze_document(
    document_id: uuid.UUID,
    file_bytes: bytes,
    mime_type: str,
    original_name: str,
) -> None:
    """Фоновая задача: конвертирует документ в текст, режет на чанки,
    анализирует каждый через Gemini с ротацией ключей, сохраняет результаты."""

    async with AsyncSessionLocal() as session:
        document = await session.get(Document, document_id)
        if document is None:
            logger.error("Документ %s не найден", document_id)
            return

        document.status = DocStatus.analyzing
        await session.commit()

        try:
            # 1. Извлечь текст локально
            is_pdf = original_name.lower().endswith(".pdf")
            if is_pdf:
                text = extract_text_from_pdf(file_bytes)
            else:
                text = extract_text_from_docx(file_bytes)

            storage.delete_temp(document_id)

            if not text.strip():
                raise ValueError("Не удалось извлечь текст из документа")

            logger.info(
                "Документ %s: извлечено %d символов текста", document_id, len(text)
            )

            # 2. Разбить на чанки
            chunks = split_into_chunks(text, CHUNK_SIZE)
            logger.info("Документ %s: %d чанков", document_id, len(chunks))

            # 3. Анализировать чанки последовательно
            all_directions: list[dict] = []
            for i, chunk in enumerate(chunks, 1):
                chunk_dirs = await _analyze_chunk(chunk, i, len(chunks))
                all_directions.extend(chunk_dirs)
                # Небольшая пауза между чанками чтобы не перегружать API
                if i < len(chunks):
                    await asyncio.sleep(2)

            # 4. Дедупликация
            unique_directions = _deduplicate(all_directions)
            logger.info(
                "Документ %s: %d уникальных направлений (из %d)",
                document_id, len(unique_directions), len(all_directions),
            )

            # 5. Сохранить в БД
            for item in unique_directions:
                if not isinstance(item, dict):
                    continue
                title = (item.get("title") or "").strip()
                if not title:
                    continue
                federal_match = item.get("federal_match")
                if federal_match in (None, "", "null"):
                    federal_match = None
                fragment = (item.get("fragment") or "")[:400]
                session.add(
                    Direction(
                        document_id=document.id,
                        title=title,
                        federal_match=federal_match,
                        fragment=fragment,
                        confidence=_map_confidence(item.get("confidence")),
                        verification_status=VerificationStatus.pending,
                    )
                )

            document.status = DocStatus.done
            document.error_message = None
            await session.commit()
            logger.info(
                "Документ %s готов: %d направлений сохранено",
                document_id, len(unique_directions),
            )

        except Exception as exc:
            await session.rollback()
            document = await session.get(Document, document_id)
            if document is not None:
                document.status = DocStatus.error
                document.error_message = f"{type(exc).__name__}: {exc}"[:4000]
                await session.commit()
            logger.exception("Ошибка анализа документа %s", document_id)
