"""Portable design documents, coordinate transforms, and payload interchange."""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any
from uuid import uuid4

import yaml

from .facade import CanvasProfile, ValidationError, validate_payload

# Frame strategy and the payload geometry supplied by the editor. Kept here so
# editor documents remain independent of Home Assistant or a device manager.
_GEOMETRY = {
    "rectangle": ("box", ("x_start", "y_start", "x_end", "y_end")),
    "ellipse": ("box", ("x_start", "y_start", "x_end", "y_end")),
    "arc": ("box", ("x_start", "y_start", "x_end", "y_end")),
    "progress_bar": ("box", ("x_start", "y_start", "x_end", "y_end")),
    "plot": ("box", ("x_start", "y_start", "x_end", "y_end")),
    "line": ("line", ("x_start", "y_start", "x_end", "y_end")),
    "circle": ("circle", ("x", "y", "radius")),
    "gauge": ("circle", ("x", "y", "radius")),
    "pie": ("circle", ("x", "y", "radius")),
    "text_fit": ("rect", ("x", "y", "width", "height")),
    "battery": ("rect", ("x", "y", "width", "height")),
    "sparkline": ("rect", ("x", "y", "width", "height")),
    "new_multiline": ("rect", ("x", "y", "width", "height")),
    "group": ("rect", ("x", "y", "width", "height")),
    "stack": ("rect", ("x", "y", "width", "height")),
    "diagram": ("rect", ("x", "y", "width", "height")),
    "dlimg": ("rect", ("x", "y", "xsize", "ysize")),
    "text": ("origin", ("x", "y")),
    "text_box": ("origin", ("x", "y")),
    "multiline": ("origin", ("x", "start_y")),
    "table": ("origin", ("x", "y")),
    "rich_text": ("midline", ("x", "y")),
    "icon": ("icon", ("x", "y", "size")),
    "qrcode": ("rect", ("x", "y", "width", "height")),
    "barcode": ("rect", ("x", "y", "width", "height")),
    "datamatrix": ("rect", ("x", "y", "width", "height")),
    "legend": ("origin", ("x", "y")),
    "star_rating": ("origin", ("x", "y")),
    "rectangle_pattern": ("origin", ("x_start", "y_start")),
    "polygon": ("points", ("points",)),
}
_EXAMPLES = {
    "line": ({"fill": "black", "width": 2}, 100, 4),
    "rectangle": ({"fill": "black", "outline": "black", "width": 1}, 80, 40),
    "ellipse": ({"fill": "black", "outline": "black", "width": 1}, 80, 50),
    "arc": (
        {"start_angle": 0, "end_angle": 270, "outline": "black", "width": 4},
        60,
        60,
    ),
    "circle": ({"fill": "black", "outline": "black", "width": 1}, 60, 60),
    "polygon": (
        {
            "points": "50,0;100,100;0,100",
            "fill": "black",
            "outline": "black",
            "width": 1,
        },
        60,
        52,
    ),
    "rectangle_pattern": (
        {
            "x_size": 8,
            "y_size": 8,
            "x_repeat": 5,
            "y_repeat": 3,
            "x_offset": 4,
            "y_offset": 4,
            "fill": "black",
        },
        60,
        40,
    ),
    "gauge": ({"progress": 65, "width": 8, "show_value": True, "size": 16}, 80, 80),
    "pie": ({"values": "A,30;B,50;C,20"}, 80, 80),
    "progress_bar": (
        {"progress": 65, "fill": "black", "show_percentage": True},
        120,
        20,
    ),
    "plot": ({"data": [{"entity": "sensor.example", "color": "black"}]}, 140, 70),
    "sparkline": ({"values": [1, 3, 2, 5, 4, 6], "color": "black"}, 100, 40),
    "diagram": ({"bars": {"values": "A,10;B,20;C,15", "color": "black"}}, 120, 60),
    "text": ({"value": "Text", "size": 20}, 100, 30),
    "text_box": (
        {"value": "Text", "size": 20, "fill": "black", "color": "white"},
        100,
        36,
    ),
    "multiline": (
        {
            "value": "Line 1|Line 2",
            "delimiter": "|",
            "offset_y": 22,
            "size": 18,
            "anchor": "la",
        },
        100,
        50,
    ),
    "new_multiline": ({"value": "Several lines\nof text", "size": 18}, 110, 60),
    "text_fit": ({"value": "Fit this text", "size": 24}, 120, 40),
    "table": (
        {"columns": [60, 60], "rows": [["A", "B"], ["1", "2"]], "font_size": 14},
        120,
        60,
    ),
    "rich_text": (
        {"spans": [{"text": "Hello "}, {"text": "world", "color": "red"}], "size": 20},
        140,
        30,
    ),
    "icon": ({"value": "mdi:home", "size": 32}, 32, 32),
    "dlimg": (
        {
            "url": (
                "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAKklEQVR42r2NMQ4A"
                "IBCDwP//GQcTB5NbZWKgqQBQAer1xUR1ksfHhR8+NtY6I+1HmsaCAAAAAElFTkSuQmCC"
            )
        },
        60,
        60,
    ),
    "qrcode": ({"data": "https://example.com"}, 60, 60),
    "barcode": ({"data": "123456789012", "code": "code128"}, 120, 50),
    "datamatrix": ({"data": "ESL"}, 40, 40),
    "legend": ({"items": "A,black;B,red"}, 80, 40),
    "star_rating": ({"rating": 3.5}, 100, 20),
    "battery": ({"level": 70}, 40, 20),
    "group": (
        {"elements": [{"type": "text", "x": 0, "y": 0, "value": "Group", "size": 20}]},
        100,
        50,
    ),
    "stack": (
        {
            "direction": "horizontal",
            "gap": 6,
            "elements": [
                {"type": "icon", "value": "mdi:home", "size": 24},
                {"type": "text", "value": "Stack", "size": 20},
            ],
        },
        120,
        30,
    ),
}


def empty_document(profile: CanvasProfile, *, background: str | None = None) -> dict[str, Any]:
    return {
        "version": 1,
        "canvas": {
            "width": profile.width,
            "height": profile.height,
            "rotate": profile.rotate,
            "rotate_mode": profile.rotate_mode,
            "palette": profile.palette,
            "name": profile.name,
        },
        "background": background or profile.background,
        "elements": [],
    }


def new_element(
    type_: str, x: int = 8, y: int = 8, element_id: str | None = None
) -> dict[str, Any]:
    if type_ not in _EXAMPLES:
        raise ValidationError(f"No starter definition for element type {type_!r}")
    spec, width, height = _EXAMPLES[type_]
    return {
        "id": element_id or uuid4().hex,
        "type": "imagespec",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "spec": {"type": type_, **deepcopy(spec)},
    }


def geometry_metadata() -> dict[str, dict[str, Any]]:
    """Frame-supplied fields for schema-driven inspectors."""
    return {name: {"role": role, "keys": list(keys)} for name, (role, keys) in _GEOMETRY.items()}


def validate_document(document: Any, profile: CanvasProfile | None = None) -> dict[str, Any]:
    if not isinstance(document, dict) or document.get("version") != 1:
        raise ValidationError("Document must be an object with version: 1")
    elements = document.get("elements")
    if not isinstance(elements, list) or len(elements) > 100:
        raise ValidationError("Document elements must be a list of at most 100 entries")
    ids = set()
    clean = deepcopy(document)
    for i, item in enumerate(clean["elements"]):
        if not isinstance(item, dict) or item.get("type") != "imagespec":
            raise ValidationError(f"elements[{i}] must be an imagespec frame")
        if not isinstance(item.get("id"), str) or not item["id"] or item["id"] in ids:
            raise ValidationError(f"elements[{i}].id must be a unique non-empty string")
        ids.add(item["id"])
        for key in ("x", "y", "width", "height"):
            if isinstance(item.get(key), bool) or not isinstance(item.get(key), int):
                raise ValidationError(f"elements[{i}].{key} must be an integer")
        if (
            item["width"] < 1
            or item["height"] < 1
            or abs(item["x"]) > 100000
            or abs(item["y"]) > 100000
        ):
            raise ValidationError(f"elements[{i}] has an invalid frame")
        if not isinstance(item.get("spec"), dict) or item["spec"].get("type") not in _GEOMETRY:
            raise ValidationError(f"elements[{i}].spec has an unsupported type")
    compile_document(clean)
    return clean


def frame_spec(element: dict[str, Any]) -> dict[str, Any]:
    spec = deepcopy(element["spec"])
    type_ = spec["type"]
    if type_ not in _GEOMETRY:
        return spec
    strategy, keys = _GEOMETRY[type_]
    payload = {key: value for key, value in spec.items() if key not in keys}
    x, y, width, height = (
        element["x"],
        element["y"],
        max(1, element["width"]),
        max(1, element["height"]),
    )
    if strategy == "box":
        values = (x, y, x + width - 1, y + height - 1)
    elif strategy == "line":
        values = (
            (x + width // 2, y, x + width // 2, y + height - 1)
            if height > width
            else (x, y + height // 2, x + width - 1, y + height // 2)
        )
    elif strategy == "circle":
        values = (x + width // 2, y + height // 2, max(1, min(width, height) // 2 - 1))
    elif strategy == "rect":
        values = (x, y, width, height)
    elif strategy == "icon":
        values = (x, y, min(width, height))
    elif strategy == "midline":
        values = (x, y + height // 2)
    elif strategy == "points":
        return {
            **payload,
            "points": _points(spec.get("points", ""), x, y, width, height),
        }
    else:
        values = (x, y)
    return {**payload, **dict(zip(keys, values, strict=True))}


def _points(value: Any, x: int, y: int, width: int, height: int) -> str:
    try:
        pairs = [pair.split(",") for pair in str(value).split(";") if pair.strip()]
        return ";".join(
            f"{x + round(float(px) * (width - 1) / 100)},"
            f"{y + round(float(py) * (height - 1) / 100)}"
            for px, py in pairs
        )
    except (ValueError, TypeError) as exc:
        raise ValidationError("polygon points must use x,y;x,y coordinates") from exc


def compile_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(document, dict) or not isinstance(document.get("elements"), list):
        raise ValidationError("Document requires an elements list")
    payload = [frame_spec(item) for item in document["elements"]]
    issues = validate_payload(payload)
    if issues:
        raise ValidationError("; ".join(issues))
    return payload


def _finite_number(item: dict[str, Any], key: str) -> int:
    if key not in item:
        raise ValidationError(f"'{key}' is required to place this element")
    value = item[key]
    if isinstance(value, bool):
        raise ValidationError(f"'{key}' must be a finite number")
    try:
        number = float(value)
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"'{key}' must be a finite number") from exc
    if not math.isfinite(number):
        raise ValidationError(f"'{key}' must be a finite number")
    return round(number)


def _from_payload(item: dict[str, Any]) -> tuple[dict[str, Any], int, int, int, int]:
    name = item.get("type")
    if name in ("row", "column"):
        name = "stack"
    if name not in _GEOMETRY or name not in _EXAMPLES:
        raise ValidationError(f"{name!r} is not a placeable imagespec element")
    role, keys = _GEOMETRY[name]
    _, default_width, default_height = _EXAMPLES[name]
    spec = deepcopy(item)
    spec["type"] = name
    if item.get("type") in ("row", "column"):
        spec.setdefault("direction", "horizontal" if item["type"] == "row" else "vertical")
    for key in keys:
        spec.pop(key, None)
    if role == "box":
        x0, y0, x1, y1 = (_finite_number(item, key) for key in keys)
        return spec, min(x0, x1), min(y0, y1), abs(x1 - x0) + 1, abs(y1 - y0) + 1
    if role == "line":
        x0, x1 = _finite_number(item, "x_start"), _finite_number(item, "x_end")
        y0, y1 = _finite_number(item, "y_start"), _finite_number(item, "y_end")
        try:
            stroke = max(1, round(float(item.get("width", 1))))
        except (ValueError, TypeError):
            stroke = 1
        if y0 == y1:
            length = abs(x1 - x0) + 1
            height = max(1, min(stroke, length - 1))
            return spec, min(x0, x1), y0 - height // 2, length, height
        if x0 == x1:
            length = abs(y1 - y0) + 1
            width = max(1, min(stroke, length - 1))
            return spec, x0 - width // 2, min(y0, y1), width, length
        raise ValidationError("a line must be horizontal or vertical")
    if role == "circle":
        cx, cy, radius = (_finite_number(item, key) for key in keys)
        radius = max(1, radius)
        return spec, cx - radius - 1, cy - radius - 1, 2 * radius + 2, 2 * radius + 2
    if role == "icon":
        x, y = _finite_number(item, keys[0]), _finite_number(item, keys[1])
        size = max(1, _finite_number(item, "size")) if "size" in item else default_width
        return spec, x, y, size, size
    if role == "rect":
        x, y = _finite_number(item, keys[0]), _finite_number(item, keys[1])
        width = max(1, _finite_number(item, keys[2])) if keys[2] in item else default_width
        height = max(1, _finite_number(item, keys[3])) if keys[3] in item else default_height
        return spec, x, y, width, height
    if role == "midline":
        x, mid = _finite_number(item, keys[0]), _finite_number(item, keys[1])
        return spec, x, mid - default_height // 2, default_width, default_height
    if role == "points":
        try:
            corners = [
                (float(px), float(py))
                for px, py in (
                    pair.split(",")
                    for pair in str(item.get("points", "")).split(";")
                    if pair.strip()
                )
            ]
        except (ValueError, TypeError) as exc:
            raise ValidationError("polygon points must use x,y;x,y coordinates") from exc
        if len(corners) < 3 or not all(math.isfinite(v) for pair in corners for v in pair):
            raise ValidationError("a polygon needs at least three finite points")
        x, y = round(min(px for px, _ in corners)), round(min(py for _, py in corners))
        width = max(1, round(max(px for px, _ in corners)) - x + 1)
        height = max(1, round(max(py for _, py in corners)) - y + 1)
        spec["points"] = ";".join(
            f"{round((px - x) * 100 / max(1, width - 1), 4):g},"
            f"{round((py - y) * 100 / max(1, height - 1), 4):g}"
            for px, py in corners
        )
        return spec, x, y, width, height
    x, y = _finite_number(item, keys[0]), _finite_number(item, keys[1])
    return spec, x, y, default_width, default_height


def import_payload(
    payload: Any, profile: CanvasProfile, *, background: str | None = None
) -> tuple[dict[str, Any], list[str]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), dict):
            payload = payload["data"]
        background = payload.get("background", background)
        payload = payload.get("payload", payload.get("elements"))
    if not isinstance(payload, list):
        raise ValidationError("Import expects an imagespec payload list or an object with payload")
    document = empty_document(profile, background=background)
    skipped = []
    for i, raw in enumerate(payload[:100]):
        if not isinstance(raw, dict) or raw.get("type") not in (
            *_GEOMETRY,
            "row",
            "column",
        ):
            skipped.append(f"#{i + 1}: unsupported element type")
            continue
        try:
            spec, x, y, width, height = _from_payload(raw)
            candidate = {
                "id": uuid4().hex,
                "type": "imagespec",
                "x": x,
                "y": y,
                "width": max(1, width),
                "height": max(1, height),
                "spec": spec,
            }
            if validate_payload([frame_spec(candidate)]):
                raise ValidationError("element failed imagespec validation")
        except (ValidationError, ValueError, OverflowError) as exc:
            skipped.append(f"#{i + 1} {raw.get('type', '?')}: {exc}")
            continue
        document["elements"].append(candidate)
        if x >= profile.width or y >= profile.height or x + width < 0 or y + height < 0:
            skipped.append(
                f"#{i + 1} {raw.get('type')}: frame is outside the canvas and will be clipped"
            )
    if len(payload) > 100:
        skipped.append("Additional elements were omitted (100 element limit)")
    # A payload may contain elements outside this particular display. Keep the
    # import reviewable and let the editor show those frames off-canvas.
    return document, skipped


def count_pixel_differences(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    profile: CanvasProfile,
    *,
    context=None,
    background: str | None = None,
) -> int:
    """Count differing rendered pixels between two regular payloads."""
    from PIL import ImageChops

    from .facade import render_image

    first = render_image(before, profile, context=context, background=background)
    second = render_image(after, profile, context=context, background=background)
    mask = (
        ImageChops.difference(first, second).convert("L").point(lambda value: 255 if value else 0)
    )
    return mask.histogram()[255]


def load_yaml(text: str) -> Any:
    if len(text.encode("utf-8")) > 512 * 1024:
        raise ValidationError("YAML input exceeds 512 KiB")

    class NoAliasLoader(yaml.SafeLoader):
        def compose_node(self, parent, index):
            if self.check_event(yaml.AliasEvent):
                raise yaml.YAMLError("YAML aliases are disabled")
            return super().compose_node(parent, index)

    try:
        return yaml.load(text, Loader=NoAliasLoader)
    except yaml.YAMLError as exc:
        raise ValidationError(f"Invalid YAML: {exc}") from exc


def dump_yaml(value: Any) -> str:
    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True, width=100)
