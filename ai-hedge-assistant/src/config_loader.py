import json
from pathlib import Path
from typing import Any, Dict


BASE_DIR = Path(__file__).resolve().parents[1]


def load_yaml(relative_path: str) -> Dict[str, Any]:
    file_path = BASE_DIR / relative_path
    with file_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
