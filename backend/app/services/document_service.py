from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

# backend/uploads
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads"

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


def validate_filename(filename: str | None) -> str:
    if not filename:
        raise ValueError("Filename is required")

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            "Unsupported file type. Allowed types: PDF, TXT, DOCX"
        )

    return extension


async def save_document_file(
    upload_file: UploadFile,
    knowledge_base_id: UUID,
    document_id: UUID,
) -> tuple[str, int]:
    """
    保存上传文件，返回相对路径和文件大小。
    文件名使用 UUID 生成，不使用用户提供的文件名作为磁盘路径。
    """
    extension = validate_filename(upload_file.filename)

    content = await upload_file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise ValueError("Uploaded file is empty")

    if len(content) > MAX_FILE_SIZE:
        raise ValueError("File size cannot exceed 20 MB")

    relative_path = (
        Path("uploads")
        / "knowledge_bases"
        / str(knowledge_base_id)
        / f"{document_id}{extension}"
    )

    absolute_path = UPLOAD_ROOT / "knowledge_bases" / str(
        knowledge_base_id
    ) / f"{document_id}{extension}"

    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(content)

    return relative_path.as_posix(), len(content)


def delete_document_file(storage_path: str) -> None:
    """
    根据数据库中的相对路径删除文件。
    不允许路径逃逸出 uploads 目录。
    """
    uploads_root = UPLOAD_ROOT.resolve()
    absolute_path = (UPLOAD_ROOT.parent / storage_path).resolve()

    if not absolute_path.is_relative_to(uploads_root):
        raise ValueError("Invalid storage path")

    if absolute_path.exists():
        absolute_path.unlink()