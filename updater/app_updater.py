from __future__ import annotations

import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Any


USER_AGENT = "YouLoad-Updater/0.4"
TIMEOUT = 60


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
        timeout=15,
    ) as response:
        import json

        return json.loads(
            response.read().decode("utf-8")
        )


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


def _version(value: str | None) -> str | None:
    if not value:
        return None

    match = re.search(
        r"\d+(?:\.\d+)+",
        value,
    )

    return (
        match.group(0)
        if match
        else None
    )


def update_application(
    owner: str,
    repository: str,
) -> dict[str, Any]:
    if not getattr(
        __import__("sys"),
        "frozen",
        False,
    ):
        raise RuntimeError(
            "Application updates are available "
            "only in a packaged YouLoad build."
        )

    releases = _request_json(
        f"https://api.github.com/repos/"
        f"{owner}/{repository}/releases"
    )

    release = None

    for item in releases:
        if item.get("draft"):
            continue

        if item.get("prerelease"):
            continue

        release = item
        break

    if not release:
        raise RuntimeError(
            "No stable YouLoad release was found."
        )

    asset = None

    for candidate in release.get(
        "assets",
        [],
    ):
        name = str(
            candidate.get(
                "name",
                "",
            )
        )

        if (
            name.lower().endswith(".exe")
            and (
                "setup" in name.lower()
                or name.lower().startswith(
                    "youload"
                )
            )
        ):
            asset = candidate
            break

    if not asset:
        raise RuntimeError(
            "The latest YouLoad release does not "
            "contain a Windows installer executable."
        )

    version = _version(
        release.get("tag_name")
    )

    temporary = tempfile.NamedTemporaryFile(
        prefix="YouLoad-Update-",
        suffix=".exe",
        delete=False,
    )

    temporary_path = Path(
        temporary.name
    )

    temporary.close()

    _download(
        asset[
            "browser_download_url"
        ],
        temporary_path,
    )

    try:
        subprocess.Popen(
            [str(temporary_path)],
            close_fds=True,
        )
    except Exception:
        try:
            temporary_path.unlink(
                missing_ok=True
            )
        except Exception:
            pass

        raise

    return {
        "name": "YouLoad",
        "version": version,
        "path": str(
            temporary_path
        ),
        "message": (
            "The YouLoad installer has been "
            "downloaded and opened."
        ),
    }
