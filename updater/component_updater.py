from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from packaging.version import InvalidVersion, Version


USER_AGENT = "YouLoad-Updater/0.4"
TIMEOUT = 60


def _root() -> Path:
    return (
        Path(__file__)
        .resolve()
        .parent
        .parent
    )


def _runtime() -> Path:
    return _root() / "runtime"


def _download(
    url: str,
    destination: Path,
) -> None:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
        },
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with urllib.request.urlopen(
        request,
        timeout=TIMEOUT,
    ) as response, destination.open(
        "wb"
    ) as output:
        while True:
            chunk = response.read(
                1024 * 1024
            )

            if not chunk:
                break

            output.write(chunk)


def _sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        while chunk := handle.read(
            1024 * 1024
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _request_json(
    url: str,
) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=TIMEOUT,
    ) as response:
        return json.loads(
            response.read().decode(
                "utf-8"
            )
        )


def _version(
    value: Any,
) -> Version | None:
    if value is None:
        return None

    match = re.search(
        r"(?<!\d)(\d+(?:\.\d+){1,3})(?!\d)",
        str(value),
    )

    if not match:
        return None

    try:
        return Version(
            match.group(1)
        )
    except InvalidVersion:
        return None


def _version_text(
    value: Any,
) -> str | None:
    parsed = _version(value)

    if parsed is None:
        return None

    return str(parsed)


def _find_checksum(
    release: dict[str, Any],
    asset_name: str,
) -> str | None:
    for asset in release.get(
        "assets",
        [],
    ):
        name = str(
            asset.get(
                "name",
                "",
            )
        ).lower()

        if not any(
            token in name
            for token in (
                "sha256",
                "sha2",
                "checksum",
            )
        ):
            continue

        url = asset.get(
            "browser_download_url"
        )

        if not url:
            continue

        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent":
                        USER_AGENT,
                },
            )

            with urllib.request.urlopen(
                request,
                timeout=TIMEOUT,
            ) as response:
                text = response.read().decode(
                    "utf-8",
                    errors="replace",
                )

            pattern = re.compile(
                rf"([A-Fa-f0-9]{{64}})"
                rf"\s+\*?{re.escape(asset_name)}"
            )

            match = pattern.search(
                text
            )

            if match:
                return (
                    match.group(1)
                    .lower()
                )

        except Exception:
            continue

    return None


def _backup_file(
    target: Path,
) -> Path:
    backup = target.with_name(
        f"{target.name}.backup"
    )

    shutil.copy2(
        target,
        backup,
    )

    return backup


def _replace_file(
    source: Path,
    target: Path,
) -> None:
    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if target.exists():
        _backup_file(target)

    os.replace(
        source,
        target,
    )


def _latest_stable_ytdlp_release() -> (
    tuple[dict[str, Any], dict[str, Any]]
):
    releases = _request_json(
        "https://api.github.com/repos/"
        "yt-dlp/yt-dlp/releases"
    )

    candidates = []

    for release in releases:
        if (
            release.get("draft")
            or release.get("prerelease")
        ):
            continue

        release_version = _version(
            release.get("tag_name")
        )

        if release_version is None:
            continue

        asset = next(
            (
                item
                for item in release.get(
                    "assets",
                    [],
                )
                if item.get("name")
                == "yt-dlp.exe"
            ),
            None,
        )

        if asset:
            candidates.append(
                (
                    release_version,
                    release,
                    asset,
                )
            )

    if not candidates:
        raise RuntimeError(
            "No stable yt-dlp Windows release was found."
        )

    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    _, release, asset = candidates[0]

    return release, asset


def update_ytdlp() -> dict[str, Any]:
    release, asset = (
        _latest_stable_ytdlp_release()
    )

    target = (
        _runtime() / "yt-dlp.exe"
    )

    with tempfile.TemporaryDirectory(
        prefix="youload-ytdlp-"
    ) as temporary:
        temporary_path = (
            Path(temporary)
            / "yt-dlp.exe"
        )

        _download(
            asset[
                "browser_download_url"
            ],
            temporary_path,
        )

        expected = _find_checksum(
            release,
            asset["name"],
        )

        if expected:
            actual = _sha256(
                temporary_path
            )

            if actual != expected:
                raise RuntimeError(
                    "yt-dlp checksum verification failed."
                )

        _replace_file(
            temporary_path,
            target,
        )

    version = _version_text(
        release.get(
            "tag_name"
        )
    )

    if not version:
        raise RuntimeError(
            "Could not determine the installed yt-dlp version."
        )

    return {
        "id": "yt-dlp",
        "name": "yt-dlp",
        "version": version,
        "path": str(target),
        "verified": bool(expected),
    }


def _ffmpeg_assets(
    releases: list[dict[str, Any]],
) -> list[
    tuple[
        Version,
        dict[str, Any],
        dict[str, Any],
    ]
]:
    candidates = []

    for release in releases:
        if release.get("draft"):
            continue

        for asset in release.get(
            "assets",
            [],
        ):
            name = str(
                asset.get(
                    "name",
                    "",
                )
            )

            lowered = name.lower()

            if (
                "win64-lgpl" not in lowered
                or "shared" in lowered
                or not lowered.endswith(
                    ".zip"
                )
            ):
                continue

            match = re.search(
                r"(?:^|-)n"
                r"(\d+(?:\.\d+){1,3})"
                r"(?:-|$)",
                name,
                re.IGNORECASE,
            )

            if not match:
                continue

            download_url = asset.get(
                "browser_download_url"
            )

            if not download_url:
                continue

            try:
                version = Version(
                    match.group(1)
                )
            except InvalidVersion:
                continue

            candidates.append(
                (
                    version,
                    release,
                    asset,
                )
            )

    return candidates


def _latest_ffmpeg_build() -> (
    tuple[
        Version,
        dict[str, Any],
        dict[str, Any],
    ]
):
    releases = _request_json(
        "https://api.github.com/repos/"
        "BtbN/FFmpeg-Builds/releases"
    )

    if not isinstance(
        releases,
        list,
    ):
        raise RuntimeError(
            "GitHub returned an unexpected FFmpeg response."
        )

    candidates = _ffmpeg_assets(
        releases
    )

    if not candidates:
        raise RuntimeError(
            "No suitable Windows x64 LGPL FFmpeg build was found."
        )

    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return candidates[0]


def update_ffmpeg() -> dict[str, Any]:
    (
        version,
        release,
        asset,
    ) = _latest_ffmpeg_build()

    with tempfile.TemporaryDirectory(
        prefix="youload-ffmpeg-"
    ) as temporary:
        temporary_dir = Path(
            temporary
        )

        archive_path = (
            temporary_dir
            / "ffmpeg.zip"
        )

        _download(
            asset[
                "browser_download_url"
            ],
            archive_path,
        )

        expected = _find_checksum(
            release,
            asset["name"],
        )

        if expected:
            actual = _sha256(
                archive_path
            )

            if actual != expected:
                raise RuntimeError(
                    "FFmpeg checksum verification failed."
                )

        extracted = (
            temporary_dir
            / "extracted"
        )

        extracted.mkdir()

        with zipfile.ZipFile(
            archive_path,
            "r",
        ) as archive:
            archive.extractall(
                extracted
            )

        ffmpeg = next(
            extracted.rglob(
                "ffmpeg.exe"
            ),
            None,
        )

        ffprobe = next(
            extracted.rglob(
                "ffprobe.exe"
            ),
            None,
        )

        if not ffmpeg:
            raise RuntimeError(
                "The FFmpeg archive did not contain ffmpeg.exe."
            )

        if not ffprobe:
            raise RuntimeError(
                "The FFmpeg archive did not contain ffprobe.exe."
            )

        target_dir = (
            _runtime()
            / "ffmpeg"
        )

        target_ffmpeg = (
            target_dir
            / "ffmpeg.exe"
        )

        target_ffprobe = (
            target_dir
            / "ffprobe.exe"
        )

        new_ffmpeg = (
            temporary_dir
            / "new-ffmpeg.exe"
        )

        new_ffprobe = (
            temporary_dir
            / "new-ffprobe.exe"
        )

        shutil.copy2(
            ffmpeg,
            new_ffmpeg,
        )

        shutil.copy2(
            ffprobe,
            new_ffprobe,
        )

        _replace_file(
            new_ffmpeg,
            target_ffmpeg,
        )

        _replace_file(
            new_ffprobe,
            target_ffprobe,
        )

    return {
        "id": "ffmpeg",
        "name": "FFmpeg",
        "version": str(version),
        "path": str(
            target_dir
        ),
        "verified": bool(expected),
    }


def update_component(
    component_id: str,
) -> dict[str, Any]:
    if component_id == "yt-dlp":
        return update_ytdlp()

    if component_id == "ffmpeg":
        return update_ffmpeg()

    raise ValueError(
        f"Unknown update component: "
        f"{component_id}"
    )