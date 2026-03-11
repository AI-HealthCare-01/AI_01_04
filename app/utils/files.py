import os
import re
import uuid
from pathlib import Path

from fastapi import UploadFile

# 요구사항: JPG/PNG/PDF
DEFAULT_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB


class FileValidationError(ValueError):
    """파일 검증 실패 (확장자/용량/파일명 등)."""


def sanitize_filename(filename: str) -> str:
    """
    OS/경로 주입 방지 + 이상문자 제거.

    Args:
        filename (str): 원본 파일명.

    Returns:
        str: 안전하게 정제된 파일명.
    """
    filename = filename.strip()
    filename = filename.replace("\\", "/").split("/")[-1]  # 경로 제거
    filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
    if not filename or filename in {".", ".."}:
        filename = f"file_{uuid.uuid4().hex}"
    return filename


def get_extension(filename: str) -> str:
    """
    파일명에서 확장자를 소문자로 추출.

    Args:
        filename (str): 파일명.

    Returns:
        str: 소문자 확장자 (e.g. ``.pdf``).
    """
    return Path(filename).suffix.lower()


def validate_extension(filename: str, allowed: set[str] | None = None) -> None:
    """
    파일 확장자 화이트리스트 검증.

    Args:
        filename (str): 검증할 파일명.
        allowed (set[str] | None): 허용 확장자 세트. None이면 DEFAULT_ALLOWED_EXTENSIONS 사용.

    Raises:
        FileValidationError: 허용되지 않는 확장자인 경우.
    """
    allowed = allowed or DEFAULT_ALLOWED_EXTENSIONS
    ext = get_extension(filename)
    if ext not in allowed:
        raise FileValidationError(f"지원하지 않는 파일 형식입니다. 허용: {sorted(allowed)}")


async def validate_size(upload: UploadFile, max_bytes: int = DEFAULT_MAX_BYTES) -> int:
    """
    UploadFile의 사이즈를 측정.

    seek/tell을 사용하여 스트림을 끝까지 읽지 않고 파일 크기 확인.

    Args:
        upload (UploadFile): 검증할 업로드 파일.
        max_bytes (int): 허용 최대 바이트. 기본값 10MB.

    Returns:
        int: 파일 크기 (바이트).

    Raises:
        FileValidationError: 파일 크기가 max_bytes를 초과하는 경우.
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
    """
    디렉토리가 없으면 생성.

    Args:
        path (str | Path): 생성할 디렉토리 경로.

    Returns:
        Path: 생성된 Path 객체.
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def build_storage_path(
    base_dir: str | Path,
    user_id: int,
    original_filename: str,
) -> Path:
    """
    업로드 파일 저장 경로 생성.

    예시: ``{base_dir}/uploads/{user_id}/{uuid}_{sanitized_name}.pdf``

    Args:
        base_dir (str | Path): 저장소 루트 디렉토리.
        user_id (int): 사용자 ID.
        original_filename (str): 원본 파일명.

    Returns:
        Path: 생성된 저장 경로.
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

    Args:
        upload (UploadFile): 저장할 업로드 파일.
        dest (Path): 대상 저장 경로.

    Returns:
        Path: 저장된 파일 경로.
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

    Args:
        user_id (int): 사용자 ID.
        upload (UploadFile): 업로드할 파일.
        base_dir (str | Path): 저장소 루트 디렉토리. 기본값 ``storage``.

    Returns:
        str: 저장된 file_path.

    Raises:
        FileValidationError: 파일명 누락, 확장자 불허용, 용량 초과 시.
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
