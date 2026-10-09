"""Framework-neutral visual design tools for imagespec."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("imagespec-designer")
except PackageNotFoundError:  # source checkout before installation
    __version__ = "0+unknown"

from .document import (
    compile_document,
    count_pixel_differences,
    dump_yaml,
    empty_document,
    geometry_metadata,
    import_payload,
    load_yaml,
    new_element,
    validate_document,
)
from .facade import (
    ENGINE_VERSION,
    MIN_IMAGESPEC_VERSION,
    TESTED_IMAGESPEC,
    CanvasProfile,
    DesignerError,
    RenderContext,
    RenderFailure,
    ValidationError,
    dither_methods,
    element_specs,
    known_types,
    palette_names,
    render_image,
    resolve_templates,
    starter_types,
    validate_payload,
)
from .templates import apply_template, design_templates

__all__ = [
    "ENGINE_VERSION",
    "MIN_IMAGESPEC_VERSION",
    "TESTED_IMAGESPEC",
    "CanvasProfile",
    "DesignerError",
    "RenderContext",
    "RenderFailure",
    "ValidationError",
    "__version__",
    "apply_template",
    "compile_document",
    "count_pixel_differences",
    "design_templates",
    "dither_methods",
    "dump_yaml",
    "element_specs",
    "empty_document",
    "geometry_metadata",
    "import_payload",
    "known_types",
    "load_yaml",
    "new_element",
    "palette_names",
    "render_image",
    "resolve_templates",
    "starter_types",
    "validate_document",
    "validate_payload",
]
