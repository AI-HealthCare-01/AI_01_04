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
from app.middleware import AuditLogMiddleware
from app.models.health import HealthChecklistTemplate

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


def _validate_config() -> None:
    """필수 환경변수 검증."""
    if not config.SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not set. Check your .env file.")
    if config.ENV == "prod":
        missing = [
            k for k in ("OPENAI_API_KEY", "NAVER_OCR_SECRET_KEY", "NAVER_OCR_API_URL") if not getattr(config, k, "")
        ]
        if missing:
            raise RuntimeError(f"Production missing config: {', '.join(missing)}")


def _build_cors_origins() -> list[str]:
    """환경별 CORS origins 목록 생성."""
    origins: list[str] = []

    if config.ENV != "prod":
        origins.extend(
            [
                "null",
                "http://localhost",
                "http://localhost:80",
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:5174",
                "http://localhost:8000",
                "http://127.0.0.1",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:5174",
                "http://127.0.0.1:8000",
            ]
        )

    extra = getattr(config, "CORS_ORIGINS", "")
    if extra:
        origins.extend([origin.strip() for origin in extra.split(",") if origin.strip()])
    else:
        # prod에서 CORS_ORIGINS가 비어있으면 경고 로그
        if config.ENV == "prod":
            logger.warning("CORS_ORIGINS is empty in production. Frontend API calls will be blocked.")

    return list(dict.fromkeys(origins))


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_config()
    try:
        await seed_health_templates()
    except Exception:
        logger.exception("Failed to seed health templates")
    yield


app = FastAPI(
    default_response_class=ORJSONResponse,
    docs_url="/api/docs" if config.ENV != "prod" else None,
    redoc_url="/api/redoc" if config.ENV != "prod" else None,
    openapi_url="/api/openapi.json" if config.ENV != "prod" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "Authorization"],
)
app.add_middleware(AuditLogMiddleware)

app.include_router(v1_routers)

initialize_tortoise(app)

# ✅ static 파일 서빙 (프로필 업로드, 스캔 업로드 등)
# /static/uploads/...  →  {FILE_STORAGE_DIR}/uploads/...
base_dir = config.FILE_STORAGE_DIR
Path(base_dir, "uploads").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=base_dir), name="static")
