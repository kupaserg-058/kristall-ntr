# CLAUDE.md

Гайд для Claude Code по проекту **Кристалл.НТР**.

## Что это

MVP веб-сервиса для анализа стратегических документов и извлечения направлений
научно-технологического развития (НТР). Пользователь загружает PDF/DOCX, Gemini
анализирует документ и находит направления НТР с привязкой к 7 федеральным
приоритетам (Указ Президента РФ №145 от 28.02.2024). Эксперт затем верифицирует
найденные направления (подтвердить / уточнить / отклонить).

## Стек

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), asyncpg
- **Frontend:** React 18 + Vite, чистый CSS (без UI-библиотек)
- **БД:** PostgreSQL
- **AI:** Google Gemini 2.5 Flash через `google-genai` SDK (новый Gen AI SDK,
  НЕ legacy `google-generativeai`). File API для PDF.

## Структура

```
backend/
  main.py        — FastAPI app, CORS, lifespan-инициализация
  config.py      — настройки из env (pydantic-settings)
  database.py    — async engine, AsyncSession, Base, get_db()
  models.py      — ORM-модели Document, Direction + Enum-ы
  schemas.py     — Pydantic-схемы ответов
  gemini.py      — вся логика Gemini (upload + analyze_document)
  storage.py     — временный буфер файлов между upload и analyze
  startup.py     — create_all + скан /federal_docs
  routers/       — documents, directions, stats
frontend/src/
  api.js         — все fetch к backend в одном месте
  pages/         — DocumentsPage, DirectionsPage
  components/    — DocumentCard, DirectionRow, StatusBadge
federal_docs/    — пред-загруженные федеральные документы (PDF/DOCX)
```

## Команды

```bash
# Backend
docker-compose up -d                          # поднять PostgreSQL
pip install -r requirements.txt
uvicorn backend.main:app --reload             # http://localhost:8000 ; /docs

# Frontend
cd frontend && npm install && npm run dev     # http://localhost:5173
```

## Правила (важно соблюдать)

- **Все операции с БД — async** (AsyncSession, await).
- **UUID — первичный ключ везде**, генерится server-side (`uuid.uuid4`).
- **Файлы НЕ хранятся локально постоянно.** Постоянное хранилище — Gemini File API.
  На время между upload и analyze байты лежат во временном буфере
  (`backend/storage.py`, системный tmp) и удаляются сразу после отправки в Gemini.
- **DOCX:** текст извлекается локально через `python-docx` и шлётся как текст;
  **PDF** грузится в Gemini File API напрямую.
- **CORS:** в dev — `localhost:5173`; в prod — из env `CORS_ORIGINS` (через запятую).
- **Формат ошибок:** всегда `{"detail": "..."}`. Ошибки БД → 503, плохой файл → 400.
- **Анализ — фоновая задача** (FastAPI BackgroundTasks): POST /analyze сразу
  возвращает `{"status": "analyzing"}`, обработка идёт в фоне.
- Авторизация в MVP не нужна.

## Env

- `GEMINI_API_KEY` — ключ Google AI Studio (aistudio.google.com/apikey).
- `DATABASE_URL` — обязательно с драйвером `postgresql+asyncpg://`.
- `CORS_ORIGINS` — список origin'ов через запятую.
