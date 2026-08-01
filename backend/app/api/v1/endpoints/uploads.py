"""Image upload endpoint (local disk storage, served at /uploads)."""

from __future__ import annotations

import uuid

import anyio
from fastapi import APIRouter, HTTPException, UploadFile, status

from app.api.deps import CurrentActiveUser
from app.core.config import settings

router = APIRouter()

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _image_extension(head: bytes) -> str | None:
    """Detect the image type from magic bytes; content-type headers can lie."""
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith(b"\x89PNG"):
        return "png"
    if head.startswith(b"GIF8"):
        return "gif"
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return "webp"
    return None


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image, returns its public URL",
)
async def upload_image(
    file: UploadFile,
    _: CurrentActiveUser,
) -> dict[str, str]:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Image exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
        )
    ext = _image_extension(content)
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File must be a JPEG, PNG, GIF, or WebP image",
        )
    name = f"{uuid.uuid4().hex}.{ext}"
    path = settings.UPLOAD_DIR / name
    await anyio.to_thread.run_sync(path.write_bytes, content)
    return {"url": f"/uploads/{name}"}
