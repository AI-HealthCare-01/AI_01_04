from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager

from app.apis.v1 import v1_routers
from app.core import config
from app.db.databases import initialize_tortoise
from app.models.health import HealthChecklistTemplate

async def seed_health_templates() -> None:
    labels = ["물 마시기", "걷기", "스트레칭"]
    for i, lb in enumerate(labels):
        await HealthChecklistTemplate.get_or_create(
            label=lb,
            defaults={"sort_order": i, "is_active": True},
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 1회 seed
    await seed_health_templates()
    yield


app = FastAPI(
    default_response_class=ORJSONResponse, docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json"
)
initialize_tortoise(app)

app.include_router(v1_routers)

# ✅ static 파일 서빙 (프로필 업로드, 스캔 업로드 등)
# /static/uploads/...  →  {FILE_STORAGE_DIR}/uploads/...
base_dir = getattr(config, "FILE_STORAGE_DIR", "./artifacts")
app.mount("/static", StaticFiles(directory=base_dir), name="static")
