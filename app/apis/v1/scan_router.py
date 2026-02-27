from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, Path, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.models.users import User
from app.services.scan_analysis import ScanAnalysisService
from app.dtos.scan import (
    ScanUploadResponse,
    ScanAnalyzeResponse,
    ScanResultResponse,
    ScanResultUpdateRequest,
    ScanSaveResponse,
)

scan_router = APIRouter(prefix="/scans", tags=["scans"])


@scan_router.post(
    "/upload",
    response_model=ScanUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_scan(
    user: Annotated[User, Depends(get_request_user)],
    scan_service: Annotated[ScanAnalysisService, Depends(ScanAnalysisService)],
    file: UploadFile = File(...),
) -> Response:
    """
    처방전 파일 업로드
    - jpg/png/pdf
    - 10MB 이하
    """

    result = await scan_service.upload_file(user=user, file=file)

    return Response(
        ScanUploadResponse.model_validate(result).model_dump(),
        status_code=status.HTTP_201_CREATED,
    )


@scan_router.post(
    "/{scan_id}/analyze",
    response_model=ScanAnalyzeResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_scan(
    user: Annotated[User, Depends(get_request_user)],
    scan_service: Annotated[ScanAnalysisService, Depends(ScanAnalysisService)],
    scan_id: Annotated[int, Path(..., ge=1)],
) -> Response:
    """
    OCR 분석 시작
    """

    result = await scan_service.start_analysis(user=user, scan_id=scan_id)

    return Response(
        ScanAnalyzeResponse.model_validate(result).model_dump(),
        status_code=status.HTTP_200_OK,
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
    OCR 분석 결과 조회
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
    data: ScanResultUpdateRequest = ...,
) -> Response:
    """
    OCR 결과 수정
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
    OCR 결과 저장 → 처방/복약 시스템에 반영
    """

    result = await scan_service.save_result(user=user, scan_id=scan_id)

    return Response(
        ScanSaveResponse.model_validate(result).model_dump(),
        status_code=status.HTTP_200_OK,
    )