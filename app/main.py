import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles

from app.apis.v1 import v1_routers
from app.core import config
from app.db.databases import initialize_tortoise
from app.models.health import HealthChecklistTemplate

from .ui import chatbot

logger = logging.getLogger(__name__)


async def seed_health_templates() -> None:
    """
    건강관리 체크리스트 기본 템플릿 시딩.

    물 마시기, 걸기, 스트레칭 항목을 없으면 생성.
    """
    labels = ["물 마시기", "걷기", "스트레칭"]
    for i, lb in enumerate(labels):
        await HealthChecklistTemplate.get_or_create(
            label=lb,
            defaults={"sort_order": i, "is_active": True},
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await seed_health_templates()
    except Exception:
        logger.exception("Failed to seed health templates")
    yield


app = FastAPI(
    default_response_class=ORJSONResponse,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:80",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chatbot.router)
app.include_router(v1_routers)
initialize_tortoise(app)

# ✅ static 파일 서빙 (프로필 업로드, 스캔 업로드 등)
# /static/uploads/...  →  {FILE_STORAGE_DIR}/uploads/...
base_dir = getattr(config, "FILE_STORAGE_DIR", "./artifacts")
Path(base_dir, "uploads").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=base_dir), name="static")
