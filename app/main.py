from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles

from app.apis.v1 import v1_routers
from app.core import config
from app.db.databases import initialize_tortoise

app = FastAPI(
    default_response_class=ORJSONResponse, docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json"
)
initialize_tortoise(app)

app.include_router(v1_routers)

# ✅ static 파일 서빙 (프로필 업로드, 스캔 업로드 등)
# /static/uploads/...  →  {FILE_STORAGE_DIR}/uploads/...
base_dir = getattr(config, "FILE_STORAGE_DIR", "./artifacts")
app.mount("/static", StaticFiles(directory=base_dir), name="static")
