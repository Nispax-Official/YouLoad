from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from threading import Event
from typing import Any, Callable

from core.video_loader import find_ytdlp


ProgressCallback = Callable[[dict[str, Any]], None]


class DownloadCancelled(Exception):
    pass


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_download_directory() -> Path:
    downloads = Path.home() / "Downloads"
    downloads.mkdir(
        parents=True,
        exist_ok=True,
    )
    return downloads


def find_ffmpeg() -> str | None:
    root = project_root()

    candidates = [
        root
        / "runtime"
        / "ffmpeg"
        / "ffmpeg.exe",
        root
        / "runtime"
        / "ffmpeg"
        / "bin"
        / "ffmpeg.exe",
        root
        / "runtime"
        / "ffmpeg.exe",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    return shutil.which("ffmpeg")


def _command() -> list[str]:
    ytdlp = find_ytdlp()

    if ytdlp == "__PYTHON_MODULE__":
        return [
            sys.executable,
            "-m",
            "yt_dlp",
        ]

    return [ytdlp]


def _run_metadata_command(
    url: str,
) -> dict[str, Any]:
    command = _command()

    command.extend(
        [
            "--dump-single-json",
            "--no-playlist",
            "--skip-download",
            "--no-warnings",
            "--ignore-config",
            url,
        ]
    )

    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        creationflags=getattr(
            subprocess,
            "CREATE_NO_WINDOW",
            0,
        ),
        check=False,
    )

    if process.returncode != 0:
        message = (
            process.stderr.strip()
            or process.stdout.strip()
            or "yt-dlp failed to read video formats."
        )

        raise RuntimeError(message)

    try:
        return json.loads(
            process.stdout
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "yt-dlp returned invalid format information."
        ) from exc


def _format_rank(
    item: dict[str, Any],
) -> tuple[float, float, float, int]:
    height = float(
        item.get("height") or 0
    )

    bitrate = float(
        item.get("vbr")
        or item.get("tbr")
        or 0
    )

    fps = float(
        item.get("fps") or 0
    )

    ext_score = (
        1
        if item.get("ext") == "mp4"
        else 0
    )

    return (
        height,
        bitrate,
        fps,
        ext_score,
    )


def _audio_rank(
    item: dict[str, Any],
) -> tuple[int, float, float, int]:
    original = (
        1
        if _is_original_audio(item)
        else 0
    )

    bitrate = float(
        item.get("abr")
        or item.get("tbr")
        or 0
    )

    quality = float(
        item.get("quality")
        or -1
    )

    preference = int(
        item.get("audio_channels")
        or 0
    )

    return (
        original,
        bitrate,
        quality,
        preference,
    )


def _codec_name(
    value: Any,
) -> str:
    if not value:
        return "Unknown"

    text = str(value).lower()

    if text.startswith("avc"):
        return "H.264"

    if text.startswith("av01"):
        return "AV1"

    if (
        text.startswith("vp9")
        or text.startswith("vp09")
    ):
        return "VP9"

    if text.startswith("hev"):
        return "HEVC"

    return str(value).upper()


def _audio_codec_name(
    value: Any,
) -> str:
    if not value:
        return "Unknown"

    text = str(value).lower()

    if "opus" in text:
        return "Opus"

    if (
        "mp4a" in text
        or "aac" in text
    ):
        return "AAC"

    if "vorbis" in text:
        return "Vorbis"

    if "flac" in text:
        return "FLAC"

    return str(value).upper()


def _size_text(
    value: Any,
) -> str:
    try:
        size = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return ""

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ]

    amount = size
    index = 0

    while (
        amount >= 1024
        and index < len(units) - 1
    ):
        amount /= 1024
        index += 1

    if index == 0:
        return f"{int(amount)} {units[index]}"

    return f"{amount:.1f} {units[index]}"


def _audio_text(
    item: dict[str, Any],
) -> str:
    values = []

    for key in (
        "format_note",
        "format",
        "language",
        "language_preference",
        "audio_track",
        "audio_track_id",
        "audio_track_name",
        "name",
    ):
        value = item.get(key)

        if isinstance(
            value,
            dict,
        ):
            values.extend(
                str(v)
                for v in value.values()
                if v is not None
            )
        elif value is not None:
            values.append(
                str(value)
            )

    return " ".join(
        values
    ).strip()


def _is_original_audio(
    item: dict[str, Any],
) -> bool:
    text = _audio_text(item)

    if re.search(
        r"\boriginal\b",
        text,
        re.IGNORECASE,
    ):
        return True

    if re.search(
        r"\boriginal\s+audio\b",
        text,
        re.IGNORECASE,
    ):
        return True

    return False


def _audio_label(
    item: dict[str, Any],
) -> str:
    text = _audio_text(item)

    language = (
        str(
            item.get(
                "language"
            )
        ).strip()
        if item.get("language")
        else ""
    )

    note = str(
        item.get(
            "format_note"
        )
        or ""
    ).strip()

    original = _is_original_audio(
        item
    )

    if original:
        language_name = ""

        match = re.search(
            r"\[[^\]]+\]\s*([^,]+?)\s+original",
            note,
            re.IGNORECASE,
        )

        if match:
            language_name = (
                match.group(1)
                .strip()
            )

        if not language_name:
            language_name = (
                language
                or "Original"
            )

        return (
            f"Original • "
            f"{language_name}"
        )

    if language:
        return (
            f"{language.upper()} • "
            "Alternate"
        )

    return "Alternate audio"


def _audio_bitrate(
    item: dict[str, Any],
) -> float:
    return float(
        item.get("abr")
        or item.get("tbr")
        or 0
    )


def _best_original_audio(
    formats: list[dict[str, Any]],
) -> dict[str, Any] | None:
    audio = [
        item
        for item in formats
        if item.get("vcodec")
        in (None, "none")
        and item.get("acodec")
        not in (None, "none")
        and _is_original_audio(item)
    ]

    if audio:
        return max(
            audio,
            key=_audio_rank,
        )

    # Current yt-dlp builds normally expose the original track
    # as the extractor-preferred/default audio stream. We use the
    # extractor's language preference before bitrate as a fallback.
    audio = [
        item
        for item in formats
        if item.get("vcodec")
        in (None, "none")
        and item.get("acodec")
        not in (None, "none")
    ]

    if not audio:
        return None

    return max(
        audio,
        key=lambda item: (
            float(
                item.get(
                    "language_preference"
                )
                if item.get(
                    "language_preference"
                ) is not None
                else -1000
            ),
            float(
                item.get("quality")
                or -1
            ),
            _audio_bitrate(item),
        ),
    )


def _original_audio_formats(
    formats: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    original = [
        item
        for item in formats
        if item.get("vcodec")
        in (None, "none")
        and item.get("acodec")
        not in (None, "none")
        and _is_original_audio(item)
    ]

    if original:
        return original

    # Some YouTube/yt-dlp combinations do not expose the word
    # "original" in the format metadata. Fall back to the
    # extractor-preferred language instead of blindly choosing
    # the highest bitrate dubbed stream.
    audio = [
        item
        for item in formats
        if item.get("vcodec")
        in (None, "none")
        and item.get("acodec")
        not in (None, "none")
    ]

    if not audio:
        return []

    preferred = max(
        (
            float(
                item.get(
                    "language_preference"
                )
                if item.get(
                    "language_preference"
                ) is not None
                else -1000
            )
            for item in audio
        ),
        default=-1000,
    )

    candidates = [
        item
        for item in audio
        if float(
            item.get(
                "language_preference"
            )
            if item.get(
                "language_preference"
            ) is not None
            else -1000
        ) == preferred
    ]

    return candidates or audio


def _best_video_for_height(
    formats: list[dict[str, Any]],
    height: int,
) -> dict[str, Any] | None:
    candidates = [
        item
        for item in formats
        if item.get("height") == height
        and item.get("vcodec")
        not in (None, "none")
    ]

    if not candidates:
        return None

    return max(
        candidates,
        key=_format_rank,
    )


def _best_progressive_for_height(
    formats: list[dict[str, Any]],
    height: int,
) -> dict[str, Any] | None:
    candidates = [
        item
        for item in formats
        if item.get("height") == height
        and item.get("vcodec")
        not in (None, "none")
        and item.get("acodec")
        not in (None, "none")
    ]

    if not candidates:
        return None

    return max(
        candidates,
        key=_format_rank,
    )


def _audio_option(
    item: dict[str, Any],
) -> dict[str, Any]:
    bitrate = _audio_bitrate(item)
    bitrate_text = (
        f"{round(bitrate)} kbps"
        if bitrate > 0
        else "Best available"
    )

    codec = _audio_codec_name(
        item.get("acodec")
    )

    language = (
        str(
            item.get(
                "language"
            )
        ).strip()
        if item.get("language")
        else ""
    )

    return {
        "id": (
            f"audio-{item.get('format_id')}"
        ),
        "label": _audio_label(item),
        "detail": (
            f"{bitrate_text} • "
            f"{codec}"
            + (
                f" • {language.upper()}"
                if language
                and not _is_original_audio(item)
                else ""
            )
        ),
        "selector": str(
            item.get("format_id")
        ),
        "format_id": str(
            item.get("format_id")
        ),
        "mode": "audio",
        "language": language,
        "original": _is_original_audio(item),
        "bitrate": bitrate,
        "container": str(
            item.get("ext")
            or ""
        ).upper(),
    }


def _video_option(
    height: int,
    video: dict[str, Any] | None,
    progressive: dict[str, Any] | None,
) -> dict[str, Any]:
    if video:
        selector = str(
            video.get("format_id")
        )

    elif progressive:
        selector = str(
            progressive.get(
                "format_id"
            )
        )

    else:
        selector = ""

    codec = _codec_name(
        video.get("vcodec")
        if video
        else progressive.get("vcodec")
    )

    size = ""

    if progressive:
        size = _size_text(
            progressive.get("filesize")
            or progressive.get(
                "filesize_approx"
            )
        )

    detail_parts = [
        "MP4",
        codec,
    ]

    if size:
        detail_parts.append(
            size
        )

    return {
        "id": f"video-{height}",
        "label": f"{height}p",
        "detail": " • ".join(
            detail_parts
        ),
        "format_id": selector,
        "mode": "video",
        "height": height,
        "fallback_selector": (
            str(
                progressive.get(
                    "format_id"
                )
            )
            if progressive
            else ""
        ),
    }


def get_video_formats(
    url: str,
) -> dict[str, Any]:
    data = _run_metadata_command(
        url.strip()
    )

    formats = data.get(
        "formats"
    ) or []

    original_audio = (
        _best_original_audio(
            formats
        )
    )

    original_audio_formats = (
        _original_audio_formats(
            formats
        )
    )

    heights = sorted(
        {
            int(item["height"])
            for item in formats
            if item.get("height")
            and item.get("vcodec")
            not in (None, "none")
        },
        reverse=True,
    )

    video_options: list[
        dict[str, Any]
    ] = [
        {
            "id": "video-best",
            "label": "Best available",
            "detail": (
                "Highest video quality available"
            ),
            "format_id": "bestvideo",
            "mode": "video",
            "height": None,
            "fallback_selector": "bestvideo",
        }
    ]

    preferred_heights = [
        4320,
        2160,
        1440,
        1080,
        720,
        480,
        360,
        240,
        144,
    ]

    seen: set[int] = set()

    ordered_heights = [
        height
        for height in preferred_heights
        if height in heights
    ]

    ordered_heights.extend(
        height
        for height in heights
        if height not in ordered_heights
    )

    for height in ordered_heights:
        seen.add(height)

        video = _best_video_for_height(
            formats,
            height,
        )

        progressive = (
            _best_progressive_for_height(
                formats,
                height,
            )
        )

        if not video and not progressive:
            continue

        video_options.append(
            _video_option(
                height,
                video,
                progressive,
            )
        )

    audio_options: list[
        dict[str, Any]
    ] = []

    audio_sorted = sorted(
        original_audio_formats,
        key=lambda item: (
            _is_original_audio(item),
            _audio_bitrate(item),
            float(
                item.get("quality")
                or -1
            ),
        ),
        reverse=True,
    )

    seen_audio_ids: set[str] = set()

    for item in audio_sorted:
        format_id = str(
            item.get("format_id")
            or ""
        )

        if (
            not format_id
            or format_id in seen_audio_ids
        ):
            continue

        seen_audio_ids.add(
            format_id
        )

        audio_options.append(
            _audio_option(item)
        )

    default_audio_id = (
        str(
            original_audio.get(
                "format_id"
            )
        )
        if original_audio
        else (
            audio_options[0]["format_id"]
            if audio_options
            else ""
        )
    )

    # Extra diagnostics are useful when YouTube exposes multiple audio
    # tracks but the extractor cannot label the original one.
    has_explicit_original = any(
        item.get("original")
        for item in audio_options
    )

    return {
        "video": video_options,
        "audio": audio_options,
        "default_audio": default_audio_id,
        "has_explicit_original": (
            has_explicit_original
        ),
        "title": data.get(
            "title"
        ),
        "id": data.get(
            "id"
        ),
    }


class DownloadEngine:
    def __init__(
        self,
        url: str,
        output_dir: str | Path,
        video_selector: str = "",
        audio_selector: str = "",
        mode: str = "video",
        progress_callback: ProgressCallback | None = None,
        cancel_event: Event | None = None,
    ):
        self.url = url.strip()
        self.output_dir = (
            Path(output_dir)
            .expanduser()
            .resolve()
        )

        self.video_selector = (
            video_selector.strip()
        )

        self.audio_selector = (
            audio_selector.strip()
        )

        self.mode = mode
        self.progress_callback = (
            progress_callback
        )

        self.cancel_event = (
            cancel_event or Event()
        )

    def cancel(self) -> None:
        self.cancel_event.set()

    def _emit(
        self,
        payload: dict[str, Any],
    ) -> None:
        if self.progress_callback:
            self.progress_callback(
                payload
            )

    def _progress_hook(
        self,
        data: dict[str, Any],
    ) -> None:
        if self.cancel_event.is_set():
            self._cleanup_partials()
            raise DownloadCancelled()

        status = data.get(
            "status"
        )

        if status == "downloading":
            downloaded = int(
                data.get(
                    "downloaded_bytes"
                )
                or 0
            )

            total = int(
                data.get(
                    "total_bytes"
                )
                or data.get(
                    "total_bytes_estimate"
                )
                or 0
            )

            percent = (
                downloaded
                / total
                * 100
                if total > 0
                else 0
            )

            self._emit(
                {
                    "status":
                        "downloading",
                    "percent":
                        max(
                            0,
                            min(
                                100,
                                percent,
                            ),
                        ),
                    "downloaded":
                        downloaded,
                    "total":
                        total,
                    "speed":
                        data.get(
                            "speed"
                        ),
                    "eta":
                        data.get(
                            "eta"
                        ),
                    "filename":
                        data.get(
                            "filename"
                        )
                        or "",
                }
            )

        elif status == "finished":
            self._emit(
                {
                    "status":
                        "processing",
                    "percent":
                        100,
                    "filename":
                        data.get(
                            "filename"
                        )
                        or "",
                }
            )

    def _postprocessor_hook(
        self,
        data: dict[str, Any],
    ) -> None:
        if self.cancel_event.is_set():
            raise DownloadCancelled()

        self._emit(
            {
                "status":
                    "processing",
                "percent":
                    100,
                "postprocessor":
                    data.get(
                        "postprocessor"
                    )
                    or "",
            }
        )

    def _cleanup_partials(self) -> None:
        try:
            for partial in (
                self.output_dir.glob(
                    "*.part"
                )
            ):
                partial.unlink(
                    missing_ok=True
                )

            for temporary in (
                self.output_dir.glob(
                    "*.ytdl"
                )
            ):
                temporary.unlink(
                    missing_ok=True
                )

        except OSError:
            pass

    def _find_final_file(
        self,
        info: dict[str, Any],
        fallback: str | Path | None,
    ) -> Path:
        candidates: list[Path] = []

        video_id = str(
            info.get("id")
            or ""
        ).strip()

        if video_id:
            marker = (
                f"[{video_id}]"
            )

            candidates.extend(
                item
                for item in self.output_dir.iterdir()
                if item.is_file()
                and marker.lower()
                in item.name.lower()
                and not item.name.endswith(
                    (
                        ".part",
                        ".ytdl",
                    )
                )
            )

        if candidates:
            return max(
                candidates,
                key=lambda item:
                    item.stat().st_mtime,
            )

        if fallback:
            return Path(
                fallback
            )

        return self.output_dir

    def _build_format_selector(
        self,
    ) -> str:
        if self.mode == "audio":
            if not self.audio_selector:
                raise ValueError(
                    "Choose an audio quality first."
                )

            return self.audio_selector

        if (
            self.video_selector == ""
            and self.audio_selector
        ):
            return (
                f"bestvideo*+"
                f"{self.audio_selector}/best"
            )

        if (
            not self.video_selector
        ):
            raise ValueError(
                "Choose a video quality first."
            )

        if not self.audio_selector:
            return self.video_selector

        return (
            f"{self.video_selector}+"
            f"{self.audio_selector}/"
            f"{self.video_selector}"
        )

    def run(self) -> dict[str, Any]:
        if not self.url:
            raise ValueError(
                "Paste a YouTube URL first."
            )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        ffmpeg = find_ffmpeg()
        selector = (
            self._build_format_selector()
        )

        outtmpl = str(
            self.output_dir
            / "%(title).180s [%(id)s].%(ext)s"
        )

        import yt_dlp

        options: dict[str, Any] = {
            "format": selector,
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": False,
            "windowsfilenames": True,
            "progress_hooks": [
                self._progress_hook
            ],
            "postprocessor_hooks": [
                self._postprocessor_hook
            ],
            "retries": 10,
            "fragment_retries": 10,
            "concurrent_fragment_downloads": 4,
            "socket_timeout": 30,
            "overwrites": False,
            "continuedl": True,
        }

        if ffmpeg:
            options[
                "ffmpeg_location"
            ] = str(
                Path(ffmpeg).parent
            )

        if self.mode == "video":
            options[
                "merge_output_format"
            ] = "mp4"

        self._emit(
            {
                "status":
                    "starting",
                "percent":
                    0,
            }
        )

        try:
            with yt_dlp.YoutubeDL(
                options
            ) as ydl:
                info = ydl.extract_info(
                    self.url,
                    download=True,
                )

        except DownloadCancelled:
            self._cleanup_partials()
            raise

        except Exception as exc:
            raise RuntimeError(
                str(exc)
            ) from exc

        if self.cancel_event.is_set():
            raise DownloadCancelled()

        if not info:
            raise RuntimeError(
                "yt-dlp did not return download information."
            )

        requested = (
            info.get(
                "requested_downloads"
            )
            or []
        )

        filepath = (
            info.get(
                "filepath"
            )
            or info.get(
                "_filename"
            )
        )

        if not filepath:
            for requested_file in requested:
                filepath = (
                    requested_file.get(
                        "filepath"
                    )
                    or filepath
                )

        if not filepath:
            filepath = ydl.prepare_filename(
                info
            )

        final_path = (
            self._find_final_file(
                info,
                filepath,
            )
        )

        self._emit(
            {
                "status":
                    "finished",
                "percent":
                    100,
                "filename":
                    str(final_path),
            }
        )

        return {
            "title":
                info.get("title")
                or "",
            "id":
                info.get("id")
                or "",
            "path":
                str(final_path),
            "mode":
                self.mode,
        }
