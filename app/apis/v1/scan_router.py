"""
스캔 라우터: 의료문서 업로드, OCR 분석, 결과 조회/수정/저장
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Path, UploadFile, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.scan import (
    ScanAnalyzeResponse,
    ScanResultResponse,
    ScanResultUpdateRequest,
    ScanSaveResponse,
    ScanUploadResponse,
)
from app.models.users import User
from app.services.scan_analysis import ScanAnalysisService

scan_router = APIRouter(prefix="/scans", tags=["scans"])


@scan_router.post(
    "/upload",
    response_model=ScanUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_scan(
    user: Annotated[User, Depends(get_request_user)],
    scan_service: Annotated[ScanAnalysisService, Depends(ScanAnalysisService)],
    file: UploadFile = File(...),  # noqa: B008
    document_type: Annotated[str, Form()] = "prescription",
) -> Response:
    """
    의료문서 파일 업로드.

    Args:
        user (User): JWT 인증으로 확인된 현재 사용자.
        scan_service (ScanAnalysisService): 스캔 분석 서비스 의존성.
        file (UploadFile): 업로드할 의료문서 (jpg/png/pdf, 10MB 이하).
        document_type (str): 문서 유형 - ``prescription`` (default) 또는 ``medical_record``.

    Returns:
        Response: scan_id, status, document_type 포함 응답 (201 Created).

    Raises:
        HTTPException: 파일 형식/용량 검증 실패 시 400.
    """

    result = await scan_service.upload_file(  # [CHANGED]
        user=user,
        file=file,
        document_type=document_type,
    )

    return Response(
        ScanUploadResponse.model_validate(result).model_dump(),
        status_code=status.HTTP_201_CREATED,
    )


@scan_router.post(
    "/{scan_id}/analyze",
    response_model=ScanAnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_scan(
    user: Annotated[User, Depends(get_request_user)],
    scan_service: Annotated[ScanAnalysisService, Depends(ScanAnalysisService)],
    background_tasks: BackgroundTasks,
    scan_id: Annotated[int, Path(..., ge=1)],
) -> Response:
    """
<<<<<<< HEAD
    OCR 분석 시작 (백그라운드 처리)
    - 즉시 202 반환, 분석은 백그라운드에서 진행
    - GET /{scan_id} 로 상태 폴링
=======
    OCR 분석 시작.

    Args:
        user (User): JWT 인증으로 확인된 현재 사용자.
        scan_service (ScanAnalysisService): 스캔 분석 서비스 의존성.
        scan_id (int): 분석할 스캔 ID.

    Returns:
        Response: scan_id, status, document_type 포함 응답.

    Raises:
        HTTPException: 스캔 미존재 시 404, OCR 실패 시 504/429/500.
>>>>>>> develop
    """
    result = await scan_service.prepare_analysis(user=user, scan_id=scan_id)
    background_tasks.add_task(scan_service.run_analysis_background, user=user, scan_id=scan_id)

    return Response(
        ScanAnalyzeResponse.model_validate(result).model_dump(),
        status_code=status.HTTP_202_ACCEPTED,
    )


@scan_router.get(
    "/{scan_id}",
    response_model=ScanResultResponse,
    status_code=status.HTTP_200_OK,
)
async def get_scan_result(
    user: Annotated[User, Depends(get_request_user)],
    scan_service: Annotated[ScanAnalysisService, Depends(ScanAnalysisService)],
    scan_id: Annotated[int, Path(..., ge=1)],
) -> Response:
    """
    OCR 분석 결과 조회.

    Args:
        user (User): JWT 인증으로 확인된 현재 사용자.
        scan_service (ScanAnalysisService): 스캔 분석 서비스 의존성.
        scan_id (int): 조회할 스캔 ID.

    Returns:
        Response: ScanResultResponse 직렬화 데이터.

    Raises:
        HTTPException: 스캔 미존재 또는 권한 없음 시 404.
    """

    result = await scan_service.get_result(user=user, scan_id=scan_id)

    return Response(
        ScanResultResponse.model_validate(result).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@scan_router.patch(
    "/{scan_id}/result",
    response_model=ScanResultResponse,
    status_code=status.HTTP_200_OK,
)
async def update_scan_result(
    user: Annotated[User, Depends(get_request_user)],
    scan_service: Annotated[ScanAnalysisService, Depends(ScanAnalysisService)],
    scan_id: Annotated[int, Path(..., ge=1)],
    data: ScanResultUpdateRequest,
) -> Response:
    """
    OCR 결과 수정.

    Args:
        user (User): JWT 인증으로 확인된 현재 사용자.
        scan_service (ScanAnalysisService): 스캔 분석 서비스 의존성.
        scan_id (int): 수정할 스캔 ID.
        data (ScanResultUpdateRequest): 수정할 필드 (document_date, diagnosis, clinical_note, drugs).

    Returns:
        Response: 수정된 ScanResultResponse 데이터.

    Raises:
        HTTPException: 스캔 미존재 또는 권한 없음 시 404.
    """

    result = await scan_service.update_result(user=user, scan_id=scan_id, data=data)

    return Response(
        ScanResultResponse.model_validate(result).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@scan_router.post(
    "/{scan_id}/save",
    response_model=ScanSaveResponse,
    status_code=status.HTTP_200_OK,
)
async def save_scan_result(
    user: Annotated[User, Depends(get_request_user)],
    scan_service: Annotated[ScanAnalysisService, Depends(ScanAnalysisService)],
    scan_id: Annotated[int, Path(..., ge=1)],
) -> Response:
    """
    OCR 결과 저장 → 처방/복약 시스템 또는 진료기록 기반 추천에 반영.

    Args:
        user (User): JWT 인증으로 확인된 현재 사용자.
        scan_service (ScanAnalysisService): 스캔 분석 서비스 의존성.
        scan_id (int): 저장할 스캔 ID.

    Returns:
        Response: ScanSaveResponse (저장 여부, 생성된 처방 ID 목록 등).

    Raises:
        HTTPException: 스캔 미존재 또는 저장 불가 상태 시 404/400.
    """

    result = await scan_service.save_result(user=user, scan_id=scan_id)

    return Response(
        ScanSaveResponse.model_validate(result).model_dump(),
        status_code=status.HTTP_200_OK,
    )
