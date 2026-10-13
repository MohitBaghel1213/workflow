from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_workflow(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        definition = yaml.safe_load(handle)

    if not isinstance(definition, dict):
        raise ValueError("Workflow YAML root must be an object")

    return definition
