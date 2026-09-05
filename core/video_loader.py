from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from html import unescape
from pathlib import Path
from typing import Any


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def find_ytdlp() -> str:
    root = _project_root()
    candidates = [
        root / "runtime" / "yt-dlp.exe",
        root / "runtime" / "yt-dlp",
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    bundled = shutil.which("yt-dlp")
    if bundled:
        return bundled

    try:
        probe = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except OSError:
        probe = None

    if probe and probe.returncode == 0:
        return "__PYTHON_MODULE__"

    raise FileNotFoundError(
        "yt-dlp was not found. Place yt-dlp.exe in runtime/ or install yt-dlp."
    )


def _sanitize_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value)
    for removed in ("\u200b", "\u2060", "\ufeff"):
        text = text.replace(removed, "")

    text = "".join(ch for ch in text if ch not in {"\u200b", "\u2060", "\ufeff"})
    text = text.strip()
    return text or None


def _fallback_title_from_webpage(url: str, video_id: str) -> str | None:
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
        )

        with urllib.request.urlopen(request, timeout=15) as response:
            html = response.read().decode("utf-8", errors="replace")

        patterns = [
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+name=["\']title["\'][^>]+content=["\']([^"\']+)["\']',
            r'<title>(.*?)</title>',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                continue

            candidate = unescape(match.group(1))
            candidate = re.sub(r"\s+", " ", candidate).strip()
            candidate = _sanitize_text(candidate)
            if candidate:
                return candidate

    except Exception:
        pass

    return f"YouTube video {video_id}" if video_id else "Unknown title"


def _thumbnail_data_url(url: str) -> str:
    if not url:
        return ""

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
        )

        with urllib.request.urlopen(request, timeout=12) as response:
            content = response.read()
            content_type = response.headers.get_content_type() or "image/jpeg"

        encoded = base64.b64encode(content).decode("ascii")
        return f"data:{content_type};base64,{encoded}"

    except Exception:
        return url


def get_video_info(url: str) -> dict[str, Any]:
    url = url.strip()

    if not url:
        raise ValueError("Paste a YouTube URL first.")

    ytdlp = find_ytdlp()

    if ytdlp == "__PYTHON_MODULE__":
        command = [sys.executable, "-m", "yt_dlp"]
    else:
        command = [ytdlp]

    command.extend(
        [
            "--dump-single-json",
            "--no-playlist",
            "--skip-download",
            "--no-warnings",
            url,
        ]
    )

    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )

    if process.returncode != 0:
        error = (
            process.stderr.strip()
            or process.stdout.strip()
            or "yt-dlp failed."
        )
        raise RuntimeError(error)

    try:
        data = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "yt-dlp returned invalid video metadata."
        ) from exc

    video_id = str(data.get("id") or "").strip()

    title = (
        _sanitize_text(data.get("title"))
        or _sanitize_text(data.get("fulltitle"))
        or _sanitize_text(data.get("alt_title"))
        or _sanitize_text(data.get("track"))
        or _sanitize_text(data.get("uploader"))
        or _sanitize_text(data.get("channel"))
        or _sanitize_text(data.get("creator"))
        or _fallback_title_from_webpage(data.get("webpage_url") or url, video_id)
    )

    creator = (
        _sanitize_text(data.get("uploader"))
        or _sanitize_text(data.get("channel"))
        or _sanitize_text(data.get("creator"))
        or "Unknown creator"
    )

    duration = format_duration(data.get("duration"))

    thumbnail = data.get("thumbnail") or ""

    if not thumbnail and video_id:
        thumbnail = (
            f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        )

    return {
        "title": str(title),
        "creator": str(creator),
        "thumbnail": _thumbnail_data_url(str(thumbnail)),
        "duration": duration,
        "webpage_url": data.get("webpage_url") or url,
        "id": video_id,
        "is_live": bool(data.get("is_live")),
    }


def format_duration(value: Any) -> str:
    if value is None:
        return "Unknown duration"

    try:
        total = max(0, int(value))
    except (TypeError, ValueError):
        return "Unknown duration"

    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"

    return f"{minutes}:{seconds:02d}"