from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class UserDataStore:
    """Atomic JSON storage for YouLoad user data."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _default(self) -> dict[str, Any]:
        return {
            "history": [],
            "queue": [],
        }

    def load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return self._default()

        try:
            with self.path.open(
                "r",
                encoding="utf-8",
            ) as handle:
                data = json.load(handle)
        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
        ):
            return self._default()

        if not isinstance(data, dict):
            return self._default()

        history = data.get("history", [])
        queue = data.get("queue", [])

        return {
            "history": history if isinstance(history, list) else [],
            "queue": queue if isinstance(queue, list) else [],
        }

    def save(
        self,
        history: list[Any],
        queue: list[Any],
    ) -> None:
        payload = {
            "history": history,
            "queue": queue,
        }

        temp = self.path.with_suffix(".json.tmp")

        with temp.open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                indent=2,
            )
            handle.write("\n")

        os.replace(
            temp,
            self.path,
        )
