"""JSON file storage helpers for backend data files."""

import json
from pathlib import Path
from typing import Any

from config import Config

DATA_DIR: Path = Config.DATA_DIR


def load_json(filepath: str | Path) -> dict[str, Any]:
    """Load JSON from a file, creating it with {} if missing."""
    path = Path(filepath)

    try:
        if not path.exists():
            save_json(path, {})
            return {}

        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return {}

        data = json.loads(content)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}


def save_json(filepath: str | Path, data: dict[str, Any]) -> bool:
    """Save JSON to a file, creating parent directories if needed."""
    path = Path(filepath)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return True
    except (OSError, TypeError, ValueError):
        return False
