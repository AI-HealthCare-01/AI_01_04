from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.scans import Scan


def _to_dict(scan: Scan) -> dict[str, Any]:
    return {
        "scan_id": scan.id,
        "user_id": scan.user_id,
        "status": scan.status,
        "analyzed_at": scan.analyzed_at.isoformat() if scan.analyzed_at else None,
        "document_type": scan.document_type,  # [ADD]
        "document_date": scan.document_date,
        "diagnosis": scan.diagnosis,
        "clinical_note": scan.clinical_note,  # [ADD]
        "drugs": scan.drugs or [],
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
        document_type: str = "prescription",  # [ADD]
    ) -> dict[str, Any]:
        scan = await Scan.create(
            user_id=user_id,
            file_path=file_path,
            document_type=document_type,  # [ADD]
            status="uploaded",
        )
        return _to_dict(scan)

    async def get_by_id_for_user(self, user_id: int, scan_id: int) -> dict[str, Any] | None:
        scan = await Scan.get_or_none(id=scan_id, user_id=user_id)
        return _to_dict(scan) if scan else None

    async def update(self, user_id: int, scan_id: int, **fields: Any) -> dict[str, Any] | None:
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
        scans = await Scan.filter(user_id=user_id).order_by("-id").offset(offset).limit(limit)
        return [_to_dict(scan) for scan in scans]
