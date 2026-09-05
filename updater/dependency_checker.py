from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

from packaging.version import InvalidVersion, Version


USER_AGENT = "YouLoad-Updater/0.4"
TIMEOUT = 15


@dataclass
class CheckResult:
    name: str
    component_type: str
    current: str | None
    latest: str | None
    status: str
    detail: str = ""
    update_url: str | None = None
    source: str = ""
    can_update: bool = False
    update_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _updater_dir() -> Path:
    return Path(__file__).resolve().parent


def _manifest_path() -> Path:
    return _updater_dir() / "components.json"


def load_manifest() -> dict[str, Any]:
    with _manifest_path().open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def _request_json(url: str) -> Any:
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
            response.read().decode("utf-8")
        )


def _clean_version(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    match = re.search(
        r"(?<!\d)(\d+(?:\.\d+){1,3})(?!\d)",
        text,
    )

    if not match:
        return None

    return match.group(1)


def _ffmpeg_runtime_version(
    value: str,
) -> str | None:
    match = re.search(
        r"ffmpeg\s+version\s+(\d+(?:\.\d+){1,3})",
        value,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    return _clean_version(value)


def _ffmpeg_asset_version(
    asset_name: str,
) -> str | None:
    match = re.search(
        r"(?:^|-)n(\d+(?:\.\d+){1,3})(?:-|$)",
        asset_name,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    return None


def _compare_versions(
    current: str | None,
    latest: str | None,
) -> str:
    if not current:
        return "not_installed"

    if not latest:
        return "unavailable"

    try:
        current_version = Version(current)
        latest_version = Version(latest)

    except InvalidVersion:
        return "unknown"

    if current_version < latest_version:
        return "update_available"

    if current_version == latest_version:
        return "up_to_date"

    return "newer_installed"


def _installed_package_version(
    distribution: str,
) -> str | None:
    try:
        return metadata.version(
            distribution
        )

    except metadata.PackageNotFoundError:
        return None


def check_pypi_package(
    display_name: str,
    distribution: str,
    update_strategy: str,
    update_id: str | None = None,
) -> CheckResult:
    current = _installed_package_version(
        distribution
    )

    try:
        payload = _request_json(
            f"https://pypi.org/pypi/"
            f"{distribution}/json"
        )

        latest = _clean_version(
            payload["info"]["version"]
        )

        status = _compare_versions(
            current,
            latest,
        )

        can_update = (
            update_strategy == "binary"
            and status
            in {
                "update_available",
                "not_installed",
            }
        )

        if update_strategy == "app_release":
            detail = (
                "Update is supplied through the "
                "YouLoad application release."
            )
        elif current:
            detail = "Bundled runtime component."
        else:
            detail = "Component is not installed."

        return CheckResult(
            name=display_name,
            component_type="python-package",
            current=current,
            latest=latest,
            status=status,
            detail=detail,
            update_url=(
                f"https://pypi.org/project/"
                f"{distribution}/"
            ),
            source="PyPI",
            can_update=can_update,
            update_id=update_id,
        )

    except (
        urllib.error.URLError,
        TimeoutError,
        KeyError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        return CheckResult(
            name=display_name,
            component_type="python-package",
            current=current,
            latest=None,
            status="unavailable",
            detail=f"Could not check PyPI: {exc}",
            update_url=(
                f"https://pypi.org/project/"
                f"{distribution}/"
            ),
            source="PyPI",
            can_update=False,
            update_id=update_id,
        )


def _find_ffmpeg() -> str | None:
    root = (
        _updater_dir()
        .resolve()
        .parent
    )

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

    return None


def _tool_output(
    executable: str,
    argument: str,
) -> str | None:
    try:
        process = subprocess.run(
            [
                executable,
                argument,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0,
            ),
            check=False,
        )

    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return None

    return (
        process.stdout.strip()
        or process.stderr.strip()
    )


def _select_latest_ffmpeg_asset(
    releases: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    candidates: list[
        tuple[Version, str, str]
    ] = []

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
                or not lowered.endswith(
                    ".zip"
                )
                or "shared" in lowered
            ):
                continue

            version_text = _ffmpeg_asset_version(
                name
            )

            download_url = asset.get(
                "browser_download_url"
            )

            if not version_text or not download_url:
                continue

            try:
                version = Version(
                    version_text
                )
            except InvalidVersion:
                continue

            candidates.append(
                (
                    version,
                    version_text,
                    download_url,
                )
            )

    if not candidates:
        return None, None

    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    _, version_text, download_url = candidates[0]

    return version_text, download_url


def check_ffmpeg() -> CheckResult:
    executable = _find_ffmpeg()

    if not executable:
        return CheckResult(
            name="FFmpeg",
            component_type="tool",
            current=None,
            latest=None,
            status="not_installed",
            detail=(
                "FFmpeg was not found in the "
                "bundled runtime."
            ),
            update_url=(
                "https://github.com/"
                "BtbN/FFmpeg-Builds/releases"
            ),
            source="BtbN",
            can_update=True,
            update_id="ffmpeg",
        )

    raw_current = _tool_output(
        executable,
        "-version",
    )

    current = _ffmpeg_runtime_version(
        raw_current or ""
    )

    if not current:
        return CheckResult(
            name="FFmpeg",
            component_type="tool",
            current=None,
            latest=None,
            status="unknown",
            detail=(
                "FFmpeg was found but its "
                "version could not be read."
            ),
            update_url=(
                "https://github.com/"
                "BtbN/FFmpeg-Builds/releases"
            ),
            source="BtbN",
            can_update=False,
            update_id="ffmpeg",
        )

    try:
        releases = _request_json(
            "https://api.github.com/repos/"
            "BtbN/FFmpeg-Builds/releases"
        )

        if not isinstance(
            releases,
            list,
        ):
            raise ValueError(
                "GitHub returned an unexpected FFmpeg response."
            )

        latest, selected_url = (
            _select_latest_ffmpeg_asset(
                releases
            )
        )

        status = _compare_versions(
            current,
            latest,
        )

        return CheckResult(
            name="FFmpeg",
            component_type="tool",
            current=current,
            latest=latest,
            status=status,
            detail=(
                "Latest Windows x64 LGPL static build."
                if selected_url
                else (
                    "No suitable Windows LGPL FFmpeg "
                    "build was found."
                )
            ),
            update_url=(
                selected_url
                or (
                    "https://github.com/"
                    "BtbN/FFmpeg-Builds/releases"
                )
            ),
            source="BtbN",
            can_update=(
                bool(selected_url)
                and status
                == "update_available"
            ),
            update_id="ffmpeg",
        )

    except (
        urllib.error.URLError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        return CheckResult(
            name="FFmpeg",
            component_type="tool",
            current=current,
            latest=None,
            status="unavailable",
            detail=(
                f"Could not check FFmpeg: {exc}"
            ),
            update_url=(
                "https://github.com/"
                "BtbN/FFmpeg-Builds/releases"
            ),
            source="BtbN",
            can_update=False,
            update_id="ffmpeg",
        )


def check_application(
    owner: str,
    repository: str,
    current_version: str,
    include_prereleases: bool = False,
) -> CheckResult:
    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repository}/releases"
    )

    try:
        releases = _request_json(url)

        selected = None

        if isinstance(
            releases,
            list,
        ):
            for release in releases:
                if release.get("draft"):
                    continue

                if (
                    release.get(
                        "prerelease"
                    )
                    and not include_prereleases
                ):
                    continue

                selected = release
                break

        if selected is None:
            return CheckResult(
                name="YouLoad",
                component_type="application",
                current=current_version,
                latest=None,
                status="unavailable",
                detail=(
                    "No suitable GitHub "
                    "release was found."
                ),
                update_url=(
                    f"https://github.com/"
                    f"{owner}/{repository}/releases"
                ),
                source="GitHub",
                can_update=False,
                update_id="youload",
            )

        latest = _clean_version(
            selected.get(
                "tag_name"
            )
        )

        has_asset = any(
            str(
                asset.get(
                    "name",
                    "",
                )
            )
            .lower()
            .endswith(".exe")
            for asset in selected.get(
                "assets",
                [],
            )
        )

        status = _compare_versions(
            current_version,
            latest,
        )

        return CheckResult(
            name="YouLoad",
            component_type="application",
            current=current_version,
            latest=latest,
            status=status,
            detail=(
                selected.get(
                    "name"
                )
                or selected.get(
                    "tag_name"
                )
                or "Latest release"
            ),
            update_url=(
                selected.get(
                    "html_url"
                )
                or (
                    f"https://github.com/"
                    f"{owner}/{repository}/releases"
                )
            ),
            source="GitHub",
            can_update=(
                status
                == "update_available"
                and has_asset
            ),
            update_id="youload",
        )

    except (
        urllib.error.URLError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        return CheckResult(
            name="YouLoad",
            component_type="application",
            current=current_version,
            latest=None,
            status="unavailable",
            detail=(
                f"Could not check GitHub: {exc}"
            ),
            update_url=(
                f"https://github.com/"
                f"{owner}/{repository}/releases"
            ),
            source="GitHub",
            can_update=False,
            update_id="youload",
        )


def check_all(
    app_version: str,
) -> list[CheckResult]:
    manifest = load_manifest()

    results: list[CheckResult] = []

    application = manifest[
        "application"
    ]

    results.append(
        check_application(
            owner=application[
                "github_owner"
            ],
            repository=application[
                "github_repository"
            ],
            current_version=app_version,
            include_prereleases=application.get(
                "include_prereleases",
                False,
            ),
        )
    )

    for package in manifest.get(
        "packages",
        [],
    ):
        results.append(
            check_pypi_package(
                display_name=package[
                    "name"
                ],
                distribution=package[
                    "distribution"
                ],
                update_strategy=package.get(
                    "update_strategy",
                    "app_release",
                ),
                update_id=package.get(
                    "update_id"
                ),
            )
        )

    for tool in manifest.get(
        "tools",
        [],
    ):
        if tool.get(
            "name"
        ) == "FFmpeg":
            results.append(
                check_ffmpeg()
            )

    return results


def check_all_as_dicts(
    app_version: str,
) -> list[dict[str, Any]]:
    return [
        result.as_dict()
        for result in check_all(
            app_version
        )
    ]
