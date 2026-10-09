import json
import sys
from datetime import UTC, datetime
from types import SimpleNamespace

import imagespec
import pytest
from PIL import ImageChops

import imagespec_designer as designer
from imagespec_designer.document import (
    dump_yaml,
    import_payload,
    load_yaml,
    new_element,
)
from imagespec_designer.templates import apply_template


def test_facade_pixel_matches_pinned_imagespec_with_rotation_and_palette():
    profile = designer.CanvasProfile(
        40, 28, rotate=90, rotate_mode="canvas", palette="bwr", background="white"
    )
    payload = [
        {
            "type": "rectangle",
            "x_start": 2,
            "y_start": 3,
            "x_end": 25,
            "y_end": 16,
            "fill": "red",
        },
        {"type": "text", "x": 4, "y": 5, "value": "A", "size": 12, "color": "black"},
    ]
    public = designer.render_image(payload, profile)
    reference = imagespec.render(
        payload,
        40,
        28,
        rotate=90,
        rotate_mode="canvas",
        background="white",
        context=imagespec.RenderContext(palette="bwr"),
    )
    assert ImageChops.difference(public, reference).getbbox() is None
    assert public.size == (40, 28)


@pytest.mark.parametrize(
    "mode,rotation,expected_size",
    [
        ("canvas", 90, (40, 28)),
        ("canvas", 270, (40, 28)),
        ("image", 90, (28, 40)),
        ("image", 270, (28, 40)),
    ],
)
def test_facade_rotation_modes_and_dither_match_pinned_engine(mode, rotation, expected_size):
    profile = designer.CanvasProfile(
        40, 28, rotate=rotation, rotate_mode=mode, palette="4", background="white"
    )
    payload = [
        {
            "type": "rectangle",
            "x_start": 1,
            "y_start": 2,
            "x_end": 30,
            "y_end": 20,
            "fill": "#cc582a",
            "outline": "black",
        }
    ]
    actual = designer.render_image(payload, profile, dither="bayer4")
    reference = imagespec.render(
        payload,
        40,
        28,
        rotate=rotation,
        rotate_mode=mode,
        background="white",
        dither="bayer4",
        context=imagespec.RenderContext(palette="4"),
    )
    assert actual.size == expected_size
    assert ImageChops.difference(actual, reference).getbbox() is None


def test_document_compile_and_import_preserve_rendered_pixels():
    profile = designer.CanvasProfile(80, 50, palette="bw")
    payload = [
        {
            "type": "rectangle",
            "x_start": 2,
            "y_start": 3,
            "x_end": 30,
            "y_end": 24,
            "fill": "black",
            "outline": "black",
            "width": 1,
        },
        {
            "type": "text",
            "x": 5,
            "y": 8,
            "value": "Hello",
            "size": 12,
            "color": "black",
        },
        {
            "type": "qrcode",
            "x": 48,
            "y": 5,
            "width": 22,
            "height": 22,
            "data": "https://example.com",
        },
    ]
    document, issues = import_payload(payload, profile, background="white")
    assert issues == []
    rebuilt = designer.compile_document(document)
    assert designer.validate_payload(rebuilt) == []
    before = designer.render_image(payload, profile)
    after = designer.render_image(rebuilt, profile)
    assert ImageChops.difference(before, after).getbbox() is None
    assert len(document["elements"]) == len(payload)
    assert designer.count_pixel_differences(payload, rebuilt, profile) == 0


def test_yaml_document_and_payload_round_trip():
    profile = designer.CanvasProfile(200, 120)
    document = designer.empty_document(profile)
    document["elements"].append(new_element("text", 12, 10, "title"))
    text = dump_yaml(document)
    loaded = load_yaml(text)
    assert designer.validate_document(loaded, profile) == document
    imported, issues = import_payload({"payload": designer.compile_document(document)}, profile)
    assert not issues
    assert designer.compile_document(imported)[0]["value"] == "Text"
    with pytest.raises(designer.ValidationError, match="aliases"):
        load_yaml("x: &x [1, 2]\ny: *x\n")


def test_template_parameters_and_profile_adaptation():
    profile = designer.CanvasProfile(400, 240, palette="4", name="Large display")
    document = apply_template("price-tag", profile, {"product": "Tea", "price": "$4.50"})
    assert document["canvas"]["width"] == 400
    payload = designer.compile_document(document)
    assert payload[0]["value"] == "Tea"
    assert payload[-1]["value"] == "$4.50"


def test_all_starter_types_compile_and_render_or_report_optional_datamatrix():
    profile = designer.CanvasProfile(200, 120, palette="4")
    now = datetime.now(UTC).isoformat()
    context = designer.RenderContext(
        history_provider=lambda entity_ids, start, end: {
            entity_id: [SimpleNamespace(state="1", last_changed=now)] for entity_id in entity_ids
        }
    )
    skipped_optional = []
    for type_ in designer.starter_types():
        document = designer.empty_document(profile)
        document["elements"].append(designer.new_element(type_, 4, 4))
        payload = designer.compile_document(document)
        assert designer.validate_payload(payload) == []
        if type_ == "datamatrix":
            try:
                designer.render_image(payload, profile, context=context)
            except designer.RenderFailure as error:
                assert "pyStrich" in str(error) or "pystrich" in str(error)
                skipped_optional.append(type_)
        else:
            designer.render_image(payload, profile, context=context)
        imported, issues = designer.import_payload(payload, profile)
        assert not issues, (type_, issues)
        assert designer.compile_document(imported) == payload, type_
    assert skipped_optional in ([], ["datamatrix"])


def test_image_callback_and_legacy_action_yaml_import():
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (2, 2), "black").save(buffer, "PNG")
    fetched = []
    context = designer.RenderContext(
        image_fetcher=lambda url: fetched.append(url) or buffer.getvalue()
    )
    context.image_cache_ttl = 60
    profile = designer.CanvasProfile(24, 24)
    payload = [
        {
            "type": "dlimg",
            "x": 0,
            "y": 0,
            "xsize": 20,
            "ysize": 20,
            "url": "https://host.invalid/a.png",
        }
    ]
    designer.render_image(payload, profile, context=context)
    designer.render_image(payload, profile, context=context)
    assert fetched == ["https://host.invalid/a.png"]
    action = {
        "action": "imagespec.render",
        "data": {
            "background": "white",
            "payload": [{"type": "text", "x": 2, "y": 3, "value": "Imported", "size": 10}],
        },
    }
    document, issues = designer.import_payload(action, profile)
    assert not issues
    assert designer.compile_document(document)[0]["value"] == "Imported"


@pytest.mark.parametrize(
    "payload",
    [
        [{"type": "circle", "x": 35, "y": 26, "radius": 9, "fill": "black"}],
        [{"type": "polygon", "points": "2,3;22,3;12,18", "fill": "black"}],
        [
            {
                "type": "rectangle",
                "x_start": 4,
                "y_start": 5,
                "x_end": 42,
                "y_end": 26,
                "width": 2,
                "outline": "black",
                "fill": "white",
            }
        ],
        [
            {
                "type": "line",
                "x_start": 2,
                "y_start": 6,
                "x_end": 36,
                "y_end": 6,
                "fill": "black",
                "width": 3,
            }
        ],
    ],
)
def test_import_geometry_round_trip_is_pixel_exact(payload):
    profile = designer.CanvasProfile(64, 48, palette="bw")
    imported, issues = designer.import_payload(payload, profile)
    assert not issues
    rebuilt = designer.compile_document(imported)
    assert rebuilt == payload
    assert designer.count_pixel_differences(payload, rebuilt, profile) == 0


def test_import_reports_unplaceable_items_without_losing_valid_entries():
    profile = designer.CanvasProfile(50, 40)
    document, issues = designer.import_payload(
        [
            {"type": "text", "x": 2, "y": 3, "value": "Good"},
            {"type": "text", "x": 4, "value": "Missing y"},
            {"type": "unknown", "x": 0, "y": 0},
        ],
        profile,
    )
    assert len(document["elements"]) == 1
    assert len(issues) == 2
    assert "y" in issues[0]


def test_template_values_survive_import_and_validate_until_host_resolution():
    profile = designer.CanvasProfile(80, 40)
    payload = [
        {"type": "text", "x": 2, "y": 3, "value": "{{ item }}", "size": "{{ text_size }}"},
        {
            "type": "rectangle",
            "x_start": 1,
            "y_start": 1,
            "x_end": 30,
            "y_end": 25,
            "fill": "{{ color }}",
        },
    ]
    assert designer.validate_payload(payload) == []
    document, issues = designer.import_payload(payload, profile)
    assert not issues
    compiled = designer.compile_document(document)
    assert compiled[0]["size"] == "{{ text_size }}"
    with pytest.raises(designer.RenderFailure, match="unresolved template"):
        designer.render_image(compiled, profile)
    resolved = designer.resolve_templates(
        compiled,
        lambda value: {"{{ item }}": "Dynamic", "{{ text_size }}": 14, "{{ color }}": "red"}[value],
    )
    assert isinstance(resolved[0]["size"], int)
    assert designer.validate_payload(resolved) == []
    designer.render_image(resolved, profile)


def test_template_values_do_not_hide_unknown_keys():
    payload = [
        {
            "type": "rectangle",
            "x_start": 1,
            "y_start": 1,
            "x_end": 10,
            "y_end": 10,
            "fil": "{{ color }}",
        }
    ]
    issues = designer.validate_payload(payload)
    assert len(issues) == 1
    assert "unknown key" in issues[0]


def test_template_values_do_not_hide_nested_unknown_keys():
    payload = [
        {
            "type": "rich_text",
            "x": 1,
            "y": 1,
            "spans": [{"text": "Hello", "typo": "{{ value }}"}],
        }
    ]
    issues = designer.validate_payload(payload)
    assert any("unknown key" in issue for issue in issues)


def test_core_import_is_homeassistant_free_and_facade_metadata_is_json_ready():
    from importlib.metadata import version

    assert "homeassistant" not in sys.modules
    json.dumps(designer.element_specs())
    assert designer.__version__ == version("imagespec-designer")
    assert designer.ENGINE_VERSION == imagespec.__version__
    assert designer.MIN_IMAGESPEC_VERSION == "1.0.1"
    assert designer.TESTED_IMAGESPEC == "1.0.1"
