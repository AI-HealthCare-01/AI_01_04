import os
import re
import uuid
from pathlib import Path

from fastapi import UploadFile

# 요구사항: JPG/PNG/PDF
DEFAULT_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB


class FileValidationError(ValueError):
    """파일 검증 실패(확장자/용량/파일명 등)"""


def sanitize_filename(filename: str) -> str:
    """
    OS/경로 주입 방지 + 이상문자 제거.
    """
    filename = filename.strip()
    filename = filename.replace("\\", "/").split("/")[-1]  # 경로 제거
    filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
    if not filename or filename in {".", ".."}:
        filename = f"file_{uuid.uuid4().hex}"
    return filename


def get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_extension(filename: str, allowed: set[str] | None = None) -> None:
    allowed = allowed or DEFAULT_ALLOWED_EXTENSIONS
    ext = get_extension(filename)
    if ext not in allowed:
        raise FileValidationError(f"지원하지 않는 파일 형식입니다. 허용: {sorted(allowed)}")


async def validate_size(upload: UploadFile, max_bytes: int = DEFAULT_MAX_BYTES) -> int:
    """
    UploadFile의 사이즈를 측정. (stream을 끝까지 읽지 않고 file 객체 seek/tell 사용)
    - UploadFile.file 은 SpooledTemporaryFile이라 seek/tell 가능
    """
    f = upload.file
    try:
        cur = f.tell()
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(cur, os.SEEK_SET)
    except Exception:
        # seek/tell이 안되는 경우를 대비해 fallback (드물지만)
        # 이 경우 전체를 읽는 건 비효율적이므로, chunk로 읽되 max_bytes 초과 시 중단
        size = 0
        await upload.seek(0)
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                break
        await upload.seek(0)

    if size > max_bytes:
        raise FileValidationError(f"파일 용량이 너무 큽니다. 최대 {max_bytes // (1024 * 1024)}MB")

    return size


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def build_storage_path(
    base_dir: str | Path,
    user_id: int,
    original_filename: str,
) -> Path:
    """
    저장 경로 예시:
    {base_dir}/uploads/{user_id}/2026-02-26/{uuid}_{sanitized_name}.pdf
    날짜 폴더는 필요하면 서비스에서 추가해도 됨.
    """
    safe_name = sanitize_filename(original_filename)
    ext = get_extension(safe_name)
    name_wo_ext = Path(safe_name).stem
    unique = uuid.uuid4().hex[:12]
    filename = f"{unique}_{name_wo_ext}{ext}"

    user_dir = Path(base_dir) / "uploads" / str(user_id)
    ensure_dir(user_dir)
    return user_dir / filename


async def save_upload_file(upload: UploadFile, dest: Path) -> Path:
    """
    UploadFile 내용을 dest로 저장.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    await upload.seek(0)
    with dest.open("wb") as out:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)

    await upload.seek(0)
    return dest


async def save_user_upload_file(
    user_id: int,
    upload: UploadFile,
    base_dir: str | Path = "storage",
) -> str:
    """
    업로드 파일 검증 + 저장까지 한 번에 처리.
    반환: 저장된 file_path (str)
    """

    if not upload.filename:
        raise FileValidationError("파일명이 없습니다.")

    # 1️⃣ 확장자 검증
    validate_extension(upload.filename)

    # 2️⃣ 용량 검증
    await validate_size(upload)

    # 3️⃣ 저장 경로 생성
    dest = build_storage_path(
        base_dir=base_dir,
        user_id=user_id,
        original_filename=upload.filename,
    )

    # 4️⃣ 저장
    await save_upload_file(upload, dest)

    return str(dest)
