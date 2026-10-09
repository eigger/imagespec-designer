"""Bundled design templates with safe parameter substitution."""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from .document import load_yaml, validate_document
from .facade import CanvasProfile, ValidationError

_REF = re.compile(r"\$\{([a-zA-Z][a-zA-Z0-9_]*)\}")


def design_templates() -> list[dict[str, Any]]:
    rows = []
    for path in sorted((Path(__file__).parent / "templates").glob("*.yaml")):
        raw = load_yaml(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "id": path.stem,
                "name": raw["name"],
                "description": raw.get("description", ""),
                "parameters": raw.get("parameters", {}),
            }
        )
    return rows


def apply_template(
    template_id: str, profile: CanvasProfile, values: dict[str, Any] | None = None
) -> dict[str, Any]:
    path = Path(__file__).parent / "templates" / f"{template_id}.yaml"
    if not path.is_file() or path.name != f"{template_id}.yaml":
        raise ValidationError(f"Unknown design template: {template_id}")
    raw = load_yaml(path.read_text(encoding="utf-8"))
    values = values or {}
    params = raw.get("parameters", {})
    merged = {key: values.get(key, desc.get("default", "")) for key, desc in params.items()}
    if any(not isinstance(value, (str, int, float, bool)) for value in merged.values()):
        raise ValidationError("Template parameters must be scalar values")
    document = deepcopy(raw["document"])

    def replace(value):
        if isinstance(value, str):

            def sub(match):
                key = match.group(1)
                if key not in merged:
                    raise ValidationError(f"Unknown template parameter: {key}")
                return str(merged[key])

            return _REF.sub(sub, value)
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, dict):
            return {k: replace(v) for k, v in value.items()}
        return value

    document = replace(document)
    document["canvas"] = {
        "width": profile.width,
        "height": profile.height,
        "rotate": profile.rotate,
        "rotate_mode": profile.rotate_mode,
        "palette": profile.palette,
        "name": profile.name,
    }
    # Templates scale from their reference dimensions while preserving text sizes.
    base_w, base_h = 200, 120
    sx, sy = profile.width / base_w, profile.height / base_h
    for element in document["elements"]:
        element["x"] = round(element["x"] * sx)
        element["y"] = round(element["y"] * sy)
        element["width"] = max(1, round(element["width"] * sx))
        element["height"] = max(1, round(element["height"] * sy))
    return validate_document(document, profile)
