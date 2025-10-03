from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx
from fastapi import APIRouter, Depends, HTTPException

from src.interfaces.http.deps import get_app_settings

if TYPE_CHECKING:
    from src.config.settings import Settings

router = APIRouter(prefix="/mobile", tags=["mobile"])
logger = logging.getLogger(__name__)


@router.get("/version")
async def get_version(settings: Settings = Depends(get_app_settings)) -> dict:
    """Get latest mobile app version from S3"""

    if not settings.s3_mobile_public_url_base:
        raise HTTPException(status_code=503, detail="Mobile S3 bucket not configured")

    version_url = f"{settings.s3_mobile_public_url_base}/version.json"
    logger.info(f"Fetching version from: {version_url}")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(version_url, timeout=5.0)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch version: {e}")
            raise HTTPException(status_code=503, detail="Version info unavailable")


@router.get("/check-update")
async def check_update(
    current_version: str, settings: Settings = Depends(get_app_settings)
) -> dict:
    """Check if update is available for given version"""

    version_info = await get_version(settings)
    latest = version_info["version"]

    # Simple semantic version comparison (major.minor.patch)
    def parse_version(v: str) -> tuple[int, int, int]:
        try:
            parts = v.split(".")
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            logger.warning(f"Invalid version format: {v}")
            return (0, 0, 0)

    has_update = parse_version(latest) > parse_version(current_version)

    return {
        "hasUpdate": has_update,
        "currentVersion": current_version,
        "latestVersion": latest,
        "updateInfo": version_info if has_update else None,
    }
