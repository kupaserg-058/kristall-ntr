import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, OperationalError

from backend.config import settings
from backend.routers import directions, documents, stats
from backend.startup import init

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kristall")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init()
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка инициализации при старте")
    yield


app = FastAPI(title="Кристалл.НТР", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(OperationalError)
@app.exception_handler(DBAPIError)
async def db_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Ошибка БД: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "База данных недоступна"},
    )


app.include_router(documents.router)
app.include_router(directions.router)
app.include_router(stats.router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
