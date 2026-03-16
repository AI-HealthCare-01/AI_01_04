"""스캔 도메인 Repository.

Scan 레코드 생성/조회/업데이트를 담당한다.
ORM 객체 대신 dict를 반환하여 서비스 레이어와의 결합도를 낮춘다.
항상 user_id 스코프로 다른 사용자 데이터 접근을 차단한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.scans import Scan


def _to_dict(scan: Scan) -> dict[str, Any]:
    """Scan ORM 객체를 API 응답용 dict로 변환한다.

    Args:
        scan (Scan): 변환할 Scan ORM 객체.

    Returns:
        dict[str, Any]: scan 필드를 담은 딕셔너리.
    """
    return {
        "scan_id": scan.id,
        "user_id": scan.user_id,
        "status": scan.status,
        "analyzed_at": scan.analyzed_at.isoformat() if scan.analyzed_at else None,
        "document_type": scan.document_type,
        "document_date": scan.document_date,
        "diagnosis_list": scan.diagnosis_list or [],
        "diagnosis": scan.diagnosis_list[0] if scan.diagnosis_list else None,
        "clinical_note": scan.clinical_note,
        "drugs": scan.drugs or [],
        "unrecognized_drugs": scan.unrecognized_drugs or [],
        "raw_text": scan.raw_text,
        "ocr_raw": scan.ocr_raw,
        "file_path": scan.file_path,
    }


class ScanRepository:
    async def create(
        self,
        user_id: int,
        *,
        file_path: str,
        document_type: str = "prescription",
    ) -> dict[str, Any]:
        """스캔 레코드를 생성한다 (uploaded 상태로 초기화).

        Args:
            user_id (int): 소유자 사용자 ID.
            file_path (str): 업로드된 파일 경로.
            document_type (str): 문서 유형 (prescription 또는 medical_record). 기본값 prescription.

        Returns:
            dict[str, Any]: 생성된 스캔 정보 딕셔너리.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        scan = await Scan.create(
            user_id=user_id,
            file_path=file_path,
            document_type=document_type,
            status="uploaded",
        )
        return _to_dict(scan)

    async def get_by_id_for_user(self, user_id: int, scan_id: int) -> dict[str, Any] | None:
        """user_id 소유의 스캔을 단건 조회한다.

        Args:
            user_id (int): 소유자 사용자 ID.
            scan_id (int): 조회할 스캔 ID.

        Returns:
            dict[str, Any] | None: 스캔 정보 딕셔너리. 없거나 소유자가 다르면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        scan = await Scan.get_or_none(id=scan_id, user_id=user_id)
        return _to_dict(scan) if scan else None

    async def update(self, user_id: int, scan_id: int, **fields: Any) -> dict[str, Any] | None:
        """스캔 필드를 업데이트한다 (소유자 검증 후 저장).

        Args:
            user_id (int): 소유자 사용자 ID.
            scan_id (int): 업데이트할 스캔 ID.
            **fields: 업데이트할 필드와 값 (status, diagnosis, drugs 등).

        Returns:
            dict[str, Any] | None: 업데이트된 스캔 정보 딕셔너리. 소유자가 다르면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        scan = await Scan.get_or_none(id=scan_id, user_id=user_id)
        if not scan:
            return None

        if "scan_id" in fields:
            fields.pop("scan_id")

        analyzed_at = fields.get("analyzed_at")
        if isinstance(analyzed_at, str):
            fields["analyzed_at"] = datetime.fromisoformat(analyzed_at)

        for key, value in fields.items():
            if hasattr(scan, key):
                setattr(scan, key, value)

        await scan.save()
        return _to_dict(scan)

    async def list_by_user(self, user_id: int, *, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """사용자의 스캔 목록을 조회한다 (id 내림차순).

        Args:
            user_id (int): 조회할 사용자 ID.
            limit (int): 최대 반환 건수. 기본값 50.
            offset (int): 건너뛸 건수. 기본값 0.

        Returns:
            list[dict[str, Any]]: 스캔 정보 딕셔너리 목록 (최신순).

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        scans = await Scan.filter(user_id=user_id).order_by("-id").offset(offset).limit(limit)
        return [_to_dict(scan) for scan in scans]
