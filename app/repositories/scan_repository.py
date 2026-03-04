"""
Scan 도메인 Repository (임시 인메모리 구현)

- 현재 Scan 모델이 DB에 없어 딕셔너리로 관리
- 추후 Scan 모델 추가 시 Tortoise ORM으로 전환
- 항상 user_id 스코프: 다른 사용자 scan 조회 불가
"""

from __future__ import annotations

from typing import Any

# 임시: scan_id -> scan data
_SCAN_STORE: dict[int, dict[str, Any]] = {}


class ScanRepository:
    def __init__(self):
        self._store = _SCAN_STORE

    def _next_scan_id(self) -> int:
        """다음 scan_id 생성"""
        return (max(self._store.keys()) + 1) if self._store else 1

    async def create(self, user_id: int, *, file_path: str) -> dict[str, Any]:
        """Scan 생성 (파일 업로드 시)"""
        scan_id = self._next_scan_id()
        scan_data = {
            "scan_id": scan_id,
            "user_id": user_id,
            "status": "uploaded",
            "analyzed_at": None,
            "document_date": None,
            "diagnosis": None,
            "drugs": [],
            "raw_text": None,
            "ocr_raw": None,
            "file_path": file_path,
        }
        self._store[scan_id] = scan_data
        return scan_data

    async def get_by_id_for_user(self, user_id: int, scan_id: int) -> dict[str, Any] | None:
        """user_id 소유의 scan만 조회"""
        scan = self._store.get(scan_id)
        if scan and scan.get("user_id") == user_id:
            return scan
        return None

    async def update(self, user_id: int, scan_id: int, **fields: Any) -> dict[str, Any] | None:
        """Scan 데이터 업데이트 (user 소유 검증)"""
        scan = await self.get_by_id_for_user(user_id, scan_id)
        if not scan:
            return None
        scan.update(fields)
        return scan

    async def list_by_user(self, user_id: int, *, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """사용자의 scan 목록 조회"""
        user_scans = [s for s in self._store.values() if s.get("user_id") == user_id]
        user_scans.sort(key=lambda x: x.get("scan_id", 0), reverse=True)
        return user_scans[offset : offset + limit]
