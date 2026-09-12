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

#: Key in `version.json` holding the Android `versionCode` that the published
#: JS bundle needs the installed APK to be at least.
#:
#: An OTA bundle only replaces web assets. Anything native — a new Capacitor
#: plugin, a manifest change, an SDK bump — has to ship as a store build. When
#: a bundle that needs native code lands on an older shell, the app keeps
#: running but the feature is silently dead: that is how v096 shipped the
#: Android back button fix as JS while the `@capacitor/app` plugin it depends on
#: stayed out of the installed APK, leaving the back button closing the app.
#:
#: Set this to the `versionCode` of the APK that first carried the native
#: pieces the bundle needs, and old shells are told to install from the store
#: instead of being handed a bundle they cannot run.
MIN_NATIVE_BUILD_KEY = "minNativeBuild"


def _parse_version(value: str) -> tuple[int, ...]:
    """Version string to a comparable tuple, tolerant of junk.

    Pads to three parts so "1.0" and "1.0.0" compare equal instead of making a
    two-part version look older than everything.
    """
    parts: list[int] = []
    for chunk in str(value).split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    if not parts:
        logger.warning("Unparseable version %r", value)
        return (0, 0, 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


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
            raise HTTPException(status_code=503, detail="Version info unavailable") from str(e)


def needs_native_update(version_info: dict, native_build: int | None) -> bool:
    """Whether this device's APK is too old to run the published bundle.

    A device that cannot report its build is treated as too old: the only shells
    that cannot answer are the ones predating the plugin that answers, which are
    exactly the ones that need replacing.
    """
    required = version_info.get(MIN_NATIVE_BUILD_KEY)
    if required is None:
        # No floor declared: the bundle is pure web and runs on any shell.
        return False
    try:
        required = int(required)
    except (TypeError, ValueError):
        logger.warning("Invalid %s in version.json: %r", MIN_NATIVE_BUILD_KEY, required)
        return False
    if native_build is None:
        return True
    return native_build < required


@router.get("/check-update")
async def check_update(
    current_version: str,
    native_build: int | None = None,
    settings: Settings = Depends(get_app_settings),
) -> dict:
    """Check if update is available for given version.

    `native_build` is the installed APK's `versionCode`. Pass it so a bundle
    that needs native code is not handed to a shell that cannot run it; omit it
    and the device is assumed to be too old to say, which it is.
    """

    version_info = await get_version(settings)
    latest = version_info["version"]

    has_update = _parse_version(latest) > _parse_version(current_version)
    requires_native = needs_native_update(version_info, native_build)

    return {
        "hasUpdate": has_update,
        "currentVersion": current_version,
        "latestVersion": latest,
        # Withheld when the shell is too old: handing over the bundle URL is
        # what lets a client install something it cannot run.
        "updateInfo": version_info if has_update and not requires_native else None,
        "requiresNativeUpdate": requires_native,
        "nativeUpdate": {
            "minNativeBuild": version_info.get(MIN_NATIVE_BUILD_KEY),
            "installedBuild": native_build,
            "version": latest,
            "apkUrl": version_info.get("latestApkUrl") or version_info.get("apkUrl"),
        }
        if requires_native
        else None,
    }
