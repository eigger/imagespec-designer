"""Stable imagespec_designer boundary around the imagespec renderer.

Only this module imports imagespec. Consumers depend on these owned names and
plain profile/context values, so a future imagespec API migration stays local.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

try:
    import imagespec as _engine
    from imagespec.exceptions import RenderError as _EngineError
    from imagespec.spec import UNSET as _UNSET
except ImportError as exc:  # friendly error for an incomplete installation
    raise ImportError("imagespec-designer requires imagespec>=1.0.1") from exc

ENGINE_VERSION = _engine.__version__
MIN_IMAGESPEC_VERSION = "1.0.1"
TESTED_IMAGESPEC = "1.0.1"


class DesignerError(Exception):
    """Base error raised by the public designer API."""


class ValidationError(DesignerError):
    """Invalid document or renderer payload."""


class RenderFailure(DesignerError):
    """An imagespec element could not be rendered."""


_TEMPLATE = re.compile(r"\{[{%#]")


def _template_paths(value: Any, path: str = "") -> set[str]:
    if isinstance(value, str):
        return {path} if _TEMPLATE.search(value) else set()
    if isinstance(value, dict):
        return {
            found for key, item in value.items() for found in _template_paths(item, f"{path}.{key}")
        }
    if isinstance(value, (list, tuple)):
        return {
            found
            for index, item in enumerate(value)
            for found in _template_paths(item, f"{path}[{index}]")
        }
    return set()


def resolve_templates(value: Any, resolver: Callable[[str], Any]) -> Any:
    """Copy a JSON-like value and resolve strings containing template syntax.

    The host owns template syntax and evaluation. The resolver's return type is
    retained, so numeric and boolean values can be restored before rendering.
    """
    if isinstance(value, str) and _TEMPLATE.search(value):
        return resolver(value)
    if isinstance(value, dict):
        return {key: resolve_templates(item, resolver) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_templates(item, resolver) for item in value]
    if isinstance(value, tuple):
        return tuple(resolve_templates(item, resolver) for item in value)
    return value


@dataclass(frozen=True)
class CanvasProfile:
    """Host supplied display characteristics."""

    width: int
    height: int
    rotate: int = 0
    rotate_mode: str = "canvas"
    palette: str | int | Sequence[Sequence[int]] = "bw"
    background: str = "white"
    name: str = "Custom display"


@dataclass
class RenderContext:
    """Host callbacks and renderer options, represented in our own API."""

    font_resolver: Callable[[str], str | None] | None = None
    history_provider: Callable[[Sequence[str], Any, Any], dict[str, Any]] | None = None
    image_fetcher: Callable[[str], bytes] | None = None
    palette: Any = None
    default_font: str = "NotoSansKR-Regular.ttf"
    icons_dir: str | None = None
    allow_local_images: bool = False
    max_image_bytes: int = 20 * 1024 * 1024
    image_cache_ttl: float = 0.0
    layout_engine: Any = None
    _engine_context: Any = field(default=None, init=False, repr=False)


def known_types() -> tuple[str, ...]:
    return tuple(sorted(_engine.known_types()))


def starter_types() -> tuple[str, ...]:
    """Types for which the editor supplies a usable starter frame."""
    from .document import _EXAMPLES

    return tuple(sorted(_EXAMPLES))


def element_specs() -> list[dict[str, Any]]:
    """Return JSON-ready metadata for the visual inspector."""

    def field_metadata(f):
        return {
            "name": f.name,
            "kind": f.kind,
            "required": f.required,
            "default": None if f.default is _UNSET else f.default,
            "enum": list(f.enum) if f.enum else None,
            "doc": f.doc,
            "fields": [field_metadata(nested) for nested in f.fields],
            "items": f.items,
            "alt": f.alt,
            "required_when": [[key, list(values)] for key, values in f.required_when],
            "positioned": f.positioned,
            "nullable": f.nullable,
        }

    result = []
    for spec in _engine.specs():
        result.append(
            {
                "types": list(spec.names),
                "type": spec.names[0],
                "category": spec.category,
                "doc": spec.doc,
                "fields": [field_metadata(f) for f in spec.fields],
            }
        )
    return result


def validate_payload(payload: Any, *, positioned: bool = True) -> list[str]:
    issues = _engine.validate(payload, positioned=positioned)
    templates = set()
    if isinstance(payload, (list, tuple)):
        for index, item in enumerate(payload):
            templates.update(_template_paths(item, f"[{index}]"))
    return [
        str(issue)
        for issue in issues
        if issue.message.startswith(("unknown key", "unknown type", "missing required"))
        or not any(
            issue.path == path
            or issue.path.startswith(path + ".")
            or issue.path.startswith(path + "[")
            for path in templates
        )
    ]


def render_image(
    payload: Sequence[dict],
    profile: CanvasProfile,
    *,
    context: RenderContext | None = None,
    background: str | None = None,
    dither: bool | str | int | None = False,
    strict: bool = False,
):
    """Render to a Pillow RGB image through the stable designer facade."""
    if profile.width < 1 or profile.height < 1:
        raise ValidationError("Canvas dimensions must be positive")
    if profile.rotate not in (0, 90, 180, 270):
        raise ValidationError("Canvas rotation must be 0, 90, 180, or 270")
    context = context or RenderContext()
    if _template_paths(payload):
        raise RenderFailure(
            "Payload has unresolved template values; evaluate them in the host before rendering"
        )
    try:
        selected_palette = context.palette if context.palette is not None else profile.palette
        if isinstance(selected_palette, str):
            aliases = {"BW": "bw", "BWR": "bwr", "BWY": "bwy", "BWRY": "4", "ACeP": "7"}
            selected_palette = aliases.get(selected_palette, selected_palette)
        engine_context = context._engine_context
        if engine_context is None:
            engine_context = context._engine_context = _engine.RenderContext()
        engine_context.font_resolver = context.font_resolver
        engine_context.history_provider = context.history_provider
        engine_context.image_fetcher = context.image_fetcher
        engine_context.palette = _engine.get_palette(selected_palette)
        engine_context.default_font = context.default_font
        engine_context.icons_dir = context.icons_dir or engine_context.icons_dir
        engine_context.allow_local_images = context.allow_local_images
        engine_context.max_image_bytes = context.max_image_bytes
        engine_context.image_cache_ttl = context.image_cache_ttl
        engine_context.layout_engine = context.layout_engine
        return _engine.render(
            payload,
            profile.width,
            profile.height,
            rotate=profile.rotate,
            rotate_mode=profile.rotate_mode,
            background=background or profile.background,
            dither=dither,
            context=engine_context,
            strict=strict,
        )
    except _EngineError as exc:
        raise RenderFailure(str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise ValidationError(str(exc)) from exc
    except Exception as exc:
        raise RenderFailure(str(exc)) from exc


def palette_names() -> tuple[str, ...]:
    return tuple(sorted(_engine.PALETTES))


def dither_methods() -> tuple[str, ...]:
    return tuple(sorted(_engine.DITHER_METHODS))
