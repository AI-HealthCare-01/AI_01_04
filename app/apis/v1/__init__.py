# v1 버전 API를 묶는 루트 라우터
# 새로운 도메인 추가 시 여기 include
from fastapi import APIRouter

from app.apis.v1.auth_routers import auth_router

# 추가 부분
from app.apis.v1.dashboard_router import dashboard_router

# 관리 이력/상세/수정
from app.apis.v1.health_router import health_router

# 복약 이력/상세/수정
from app.apis.v1.medication_router import medication_router

# OCR 결과 화면의 “건강관리 추천” 탭 조회/수정/삭제/저장
from app.apis.v1.recommendation_router import recommendation_router

# 문서 업로드/분석 시작/OCR 결과 조회/수정/저장
from app.apis.v1.scan_router import scan_router
from app.apis.v1.user_routers import user_router

v1_routers = APIRouter(prefix="/api/v1")
v1_routers.include_router(auth_router)
v1_routers.include_router(user_router)
v1_routers.include_router(dashboard_router)
v1_routers.include_router(medication_router)
v1_routers.include_router(health_router)
v1_routers.include_router(scan_router)
v1_routers.include_router(recommendation_router)
