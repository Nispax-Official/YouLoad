from __future__ import annotations

import importlib.metadata
import json
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

from config import APP_VERSION, GITHUB_OWNER, GITHUB_REPOSITORY


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def http_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "YouLoad-Update-Checker/0.3",
            "Accept": "application/vnd.github+json, application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=12) as response:
        data = response.read().decode("utf-8")

    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError("Unexpected update service response")

    return value


def package_version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def command_version(command: list[str], pattern: str) -> str | None:
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    output = f"{process.stdout}\n{process.stderr}".strip()
    match = re.search(pattern, output, re.IGNORECASE)
    return match.group(1) if match else None


def normalize_version(value: str | None) -> tuple[int, ...]:
    if not value:
        return ()

    parts = re.findall(r"\d+", value)
    return tuple(int(part) for part in parts)


def compare_versions(current: str | None, latest: str | None) -> str:
    if not current:
        return "missing"

    if not latest:
        return "unavailable"

    current_version = normalize_version(current)
    latest_version = normalize_version(latest)

    if not current_version or not latest_version:
        return "unknown"

    size = max(len(current_version), len(latest_version))
    current_version += (0,) * (size - len(current_version))
    latest_version += (0,) * (size - len(latest_version))

    if current_version < latest_version:
        return "update_available"

    if current_version > latest_version:
        return "newer_local"

    return "up_to_date"


def github_release_version(repository: str) -> tuple[str | None, str | None]:
    try:
        data = http_json(
            f"https://api.github.com/repos/{repository}/releases/latest"
        )
    except Exception as exc:
        return None, str(exc)

    version = data.get("tag_name") or data.get("name")
    return (str(version) if version else None), None


def pypi_version(package: str) -> tuple[str | None, str | None]:
    try:
        data = http_json(
            f"https://pypi.org/pypi/{package}/json"
        )
    except Exception as exc:
        return None, str(exc)

    info = data.get("info")
    if not isinstance(info, dict):
        return None, "Invalid PyPI response"

    version = info.get("version")
    return (str(version) if version else None), None


def check_component(
    name: str,
    current: str | None,
    source: str,
    latest_loader,
) -> dict[str, Any]:
    latest, error = latest_loader()

    result = {
        "name": name,
        "current": current,
        "latest": latest,
        "status": compare_versions(current, latest) if not error else "unavailable",
        "source": source,
        "error": error,
    }

    return result


def find_ffmpeg() -> Path | None:
    candidate = project_root() / "runtime" / "ffmpeg" / "ffmpeg.exe"
    return candidate if candidate.exists() else None


def check_all_dependencies() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    app_repo = f"{GITHUB_OWNER}/{GITHUB_REPOSITORY}"

    results.append(
        check_component(
            "YouLoad",
            APP_VERSION,
            "GitHub",
            lambda: github_release_version(app_repo),
        )
    )

    results.append(
        check_component(
            "PySide6",
            package_version("PySide6"),
            "PyPI",
            lambda: pypi_version("PySide6"),
        )
    )

    results.append(
        check_component(
            "PySide6 Essentials",
            package_version("PySide6-Essentials"),
            "PyPI",
            lambda: pypi_version("PySide6-Essentials"),
        )
    )

    results.append(
        check_component(
            "PySide6 Addons",
            package_version("PySide6-Addons"),
            "PyPI",
            lambda: pypi_version("PySide6-Addons"),
        )
    )

    results.append(
        check_component(
            "Shiboken6",
            package_version("shiboken6"),
            "PyPI",
            lambda: pypi_version("shiboken6"),
        )
    )

    ytdlp_path = project_root() / "runtime" / "yt-dlp.exe"
    if ytdlp_path.exists():
        ytdlp_current = command_version(
            [str(ytdlp_path), "--version"],
            r"(\d{4}\.\d{2}\.\d{2})",
        )
    else:
        ytdlp_current = package_version("yt-dlp")

    results.append(
        check_component(
            "yt-dlp",
            ytdlp_current,
            "GitHub",
            lambda: github_release_version("yt-dlp/yt-dlp"),
        )
    )

    ffmpeg_path = find_ffmpeg()
    ffmpeg_current = (
        command_version(
            [str(ffmpeg_path), "-version"],
            r"ffmpeg version\s+([^\s]+)",
        )
        if ffmpeg_path
        else None
    )

    results.append(
        check_component(
            "FFmpeg",
            ffmpeg_current,
            "FFmpeg Windows build",
            lambda: github_release_version("BtbN/FFmpeg-Builds"),
        )
    )

    return results
