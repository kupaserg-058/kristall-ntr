import io
import json
import logging
import uuid

from google import genai
from google.genai import types
from sqlalchemy import select

from backend import storage
from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models import Confidence, Direction, DocStatus, Document, VerificationStatus

logger = logging.getLogger("kristall.gemini")

MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = """Ты — эксперт по анализу стратегических документов в сфере \
научно-технологического развития России.

Приоритетные направления НТР, утверждённые Указом Президента РФ №529 от 18.06.2024:
1. Высокоэффективная и ресурсосберегающая энергетика
2. Превентивная и персонализированная медицина, обеспечение здорового долголетия
3. Высокопродуктивное и устойчивое к изменениям природной среды сельское хозяйство
4. Безопасность получения, хранения, передачи и обработки информации
5. Интеллектуальные транспортные и телекоммуникационные системы, включая автономные транспортные средства
6. Укрепление социокультурной идентичности российского общества и повышение уровня его образования
7. Адаптация к изменениям климата, сохранение и рациональное использование природных ресурсов

К каждому направлению относятся следующие наукоёмкие технологии (для точного сопоставления):
— Направление 1: технологии генерации/хранения/распределения энергии, энергосистемы с замкнутым топливным циклом, атомные технологии
— Направление 2: биомедицинские и когнитивные технологии, лекарственные средства нового поколения, медицинские изделия, биогибридные и нейротехнологии, персонализированное питание
— Направление 3: технологии повышения продуктивности с/х животных и растений, ветеринарные препараты, новые сорта и гибриды растений, биологические средства защиты урожая
— Направление 4: микроэлектроника и фотоника, квантовые системы передачи данных, защищённое программное обеспечение, технологии безопасности информации
— Направление 5: транспортные технологии (море/земля/воздух), беспилотные и автономные системы, космическое приборостроение, системы связи и навигации
— Направление 6: технологии системного анализа социально-экономического развития, укрепление цивилизационных основ и традиционных ценностей, социально-психологические технологии
— Направление 7: мониторинг и прогнозирование климата и окружающей среды, экологически чистые технологии добычи и переработки ресурсов, сохранение биоразнообразия

Сквозные технологии (применимы к нескольким направлениям): синтетическая биология и генная инженерия, новые материалы с заданными свойствами, малотоннажная химическая продукция, технологии искусственного интеллекта, отечественные средства производства и научное приборостроение, природоподобные технологии, биотехнологии.

Твоя задача: проанализируй документ региональной стратегии или программы. Найди ВСЕ \
конкретные мероприятия, задачи, меры и направления в сфере науки и технологий. \
Для каждого найденного элемента определи наиболее подходящее федеральное направление \
из списка выше (или null, если не относится ни к одному).

Отвечай СТРОГО в формате JSON без markdown-обёртки и без ```json:
{
  "directions": [
    {
      "title": "точное название мероприятия/задачи как в документе",
      "federal_match": "одно из 7 направлений выше или null",
      "fragment": "дословная цитата из документа до 400 символов",
      "confidence": "high | medium | low"
    }
  ]
}"""

USER_PROMPT = "Проанализируй приложенный документ согласно инструкции и верни JSON."

# JSON-схема для строгого вывода (response_schema)
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
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                },
                "required": ["title", "fragment", "confidence"],
            },
        }
    },
    "required": ["directions"],
}

_client: genai.Client | None = None


def get_client() -> genai.Client:
    """Ленивая инициализация Gemini-клиента (чтобы старт не падал без ключа)."""
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY не задан")
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


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


def _parse_response(raw: str) -> dict:
    """Парсит ответ модели: сначала напрямую, потом срезав markdown-фенсы."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    text = raw.strip()
    if text.startswith("```"):
        # убрать первую строку с ``` (возможно ```json) и закрывающие ```
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


async def analyze_document(
    document_id: uuid.UUID,
    file_bytes: bytes,
    mime_type: str,
    original_name: str,
) -> None:
    """Фоновая задача: анализирует документ через Gemini и сохраняет направления."""
    async with AsyncSessionLocal() as session:
        document = await session.get(Document, document_id)
        if document is None:
            logger.error("Документ %s не найден для анализа", document_id)
            return

        document.status = DocStatus.analyzing
        await session.commit()

        raw_response = ""
        try:
            client = get_client()
            is_pdf = mime_type == "application/pdf" or original_name.lower().endswith(
                ".pdf"
            )

            if is_pdf:
                uploaded = await client.aio.files.upload(
                    file=io.BytesIO(file_bytes),
                    config=types.UploadFileConfig(mime_type="application/pdf"),
                )
                document.gemini_file_uri = getattr(uploaded, "uri", None) or getattr(
                    uploaded, "name", None
                )
                await session.commit()
                storage.delete_temp(document_id)
                contents = [USER_PROMPT, uploaded]
            else:
                text = extract_text_from_docx(file_bytes)
                storage.delete_temp(document_id)
                if not text.strip():
                    raise ValueError("Не удалось извлечь текст из DOCX (пустой документ)")
                contents = [f"{USER_PROMPT}\n\nТекст документа:\n{text}"]

            response = await client.aio.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                ),
            )
            raw_response = response.text or ""
            data = _parse_response(raw_response)

            directions = data.get("directions", [])
            if not isinstance(directions, list):
                raise ValueError("Поле 'directions' не является списком")

            for item in directions:
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
                "Документ %s проанализирован: %d направлений",
                document_id,
                len(directions),
            )

        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            document = await session.get(Document, document_id)
            if document is not None:
                document.status = DocStatus.error
                msg = f"{type(exc).__name__}: {exc}"
                if raw_response:
                    msg += f"\n\nСырой ответ модели:\n{raw_response[:2000]}"
                document.error_message = msg[:4000]
                await session.commit()
            logger.exception("Ошибка анализа документа %s", document_id)
