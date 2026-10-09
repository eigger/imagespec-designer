"""Optional Home Assistant value and template adapter.

This module is intentionally absent from core imports and the base dependency
set. The host passes resulting values into previews; it owns service calls.
"""

from __future__ import annotations

from typing import Any


def evaluate_template(hass: Any, source: str, variables: dict[str, Any] | None = None) -> Any:
    """Render a Home Assistant template using the host's current state."""
    from homeassistant.helpers.template import Template

    template = Template(source, hass)
    return template.async_render(variables or {}, parse_result=True)


def resolve_value(hass: Any, value: Any, variables: dict[str, Any] | None = None) -> Any:
    """Resolve nested document templates for a host-controlled preview."""
    from imagespec_designer import resolve_templates

    return resolve_templates(value, lambda source: evaluate_template(hass, source, variables))


def resolve_font(hass: Any, name: str) -> str | None:
    """Look up a host font under its www/fonts directory when available."""
    from pathlib import Path

    candidate = Path(hass.config.path("www", "fonts", name))
    return str(candidate) if candidate.is_file() else None
