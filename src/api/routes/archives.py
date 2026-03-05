"""Archive (soul transfer) endpoints — export and import memory snapshots."""

import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from src.api.auth import verify_api_key
from src.api.dependencies import get_adapter
from src.api.middleware_adapter import MiddlewareAdapter
from src.api.models.system import (
    ArchiveExportRequest,
    ArchiveImportRequest,
    ArchiveResponse,
)

router = APIRouter(
    prefix="/v1/archives",
    tags=["archives"],
    dependencies=[Depends(verify_api_key)],
)

MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500 MB


@router.post(
    "/export/",
    response_model=ArchiveResponse,
    summary="Export memory archive",
)
async def export_archive(
    body: ArchiveExportRequest,
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Export all memories as a portable archive (soul transfer)."""
    return adapter.export_archive(body)


@router.post(
    "/import/",
    response_model=ArchiveResponse,
    summary="Import memory archive",
)
async def import_archive(
    body: ArchiveImportRequest,
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Import a previously exported memory archive."""
    return adapter.import_archive(body)


@router.post(
    "/upload/",
    response_model=ArchiveResponse,
    summary="Upload and import an archive file",
)
async def upload_and_import(
    file: UploadFile = File(...),
    adapter: MiddlewareAdapter = Depends(get_adapter),
):
    """Upload an archive file and import it.

    Accepts ``.tar.gz`` or ``.bma.tar.gz`` files.  The file is written to a
    temporary directory, imported, and then cleaned up.
    """
    # Sanitise filename — strip path components to prevent traversal
    raw_name = file.filename or "upload.tar.gz"
    safe_name = os.path.basename(raw_name)
    if not safe_name:
        safe_name = "upload.tar.gz"

    # Validate extension
    if not (safe_name.endswith(".tar.gz") or safe_name.endswith(".bma")):
        raise HTTPException(
            status_code=400,
            detail="Only .tar.gz and .bma archive files are accepted.",
        )

    tmp_dir = Path(tempfile.mkdtemp(prefix="bmam_upload_"))
    try:
        dest = tmp_dir / safe_name
        size = 0
        with open(dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum {MAX_UPLOAD_SIZE // (1024*1024)} MB.",
                    )
                f.write(chunk)

        req = ArchiveImportRequest(archive_path=str(dest))
        return adapter.import_archive(req)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
