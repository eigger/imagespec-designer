"""A tiny HTTP host used to try the designer without an application framework."""

from __future__ import annotations

import argparse
import base64
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from . import (
    ENGINE_VERSION,
    MIN_IMAGESPEC_VERSION,
    TESTED_IMAGESPEC,
    CanvasProfile,
    ValidationError,
    __version__,
    compile_document,
    element_specs,
    geometry_metadata,
    new_element,
    render_image,
    starter_types,
    validate_document,
)
from .document import dump_yaml, import_payload, load_yaml
from .templates import apply_template, design_templates

WEB = Path(__file__).parent / "web"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def log_message(self, format, *args):
        print("[designer] " + format % args)

    def send_json(self, value, status=200):
        data = json.dumps(value, ensure_ascii=False, default=str).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/api/"):
            self.send_json({"error": "POST JSON to this endpoint"}, 405)
            return
        if self.path.startswith("/assets/"):
            self.path = self.path.removeprefix("/assets")
        if self.path in ("/", "/index.html"):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", "0"))
            if length > 2 * 1024 * 1024:
                raise ValidationError("Request is too large")
            data = json.loads(self.rfile.read(length) or b"{}")
            profile = make_profile(data.get("profile"))
            route = urlparse(self.path).path
            if route == "/api/metadata":
                result = {
                    "elements": element_specs(),
                    "starters": starter_types(),
                    "geometry": geometry_metadata(),
                    "designer_version": __version__,
                    "imagespec_version": ENGINE_VERSION,
                    "imagespec_minimum_version": MIN_IMAGESPEC_VERSION,
                    "imagespec_tested_version": TESTED_IMAGESPEC,
                }
            elif route == "/api/new-element":
                result = {"element": new_element(data.get("type", "text"))}
            elif route == "/api/templates":
                result = design_templates()
            elif route == "/api/render":
                doc = validate_document(data.get("document"), profile)
                payload = compile_document(doc)
                image = render_image(payload, profile, background=doc.get("background"))
                buffer = BytesIO()
                image.save(buffer, "PNG")
                result = {
                    "data_url": "data:image/png;base64,"
                    + base64.b64encode(buffer.getvalue()).decode()
                }
            elif route == "/api/validate":
                result = {"valid": bool(validate_document(data.get("document"), profile))}
            elif route == "/api/dump-yaml":
                result = {"yaml": dump_yaml(data.get("document"))}
            elif route == "/api/dump-payload":
                doc = validate_document(data.get("document"), profile)
                result = {"yaml": dump_yaml(compile_document(doc))}
            elif route == "/api/parse-yaml":
                value = load_yaml(data.get("text", ""))
                if isinstance(value, dict) and value.get("version") == 1:
                    doc = validate_document(value, profile)
                    issues = []
                else:
                    if (
                        isinstance(value, dict)
                        and "data" in value
                        and isinstance(value["data"], dict)
                    ):
                        value = value["data"]
                    if isinstance(value, dict):
                        bg = value.get("background")
                        value = value.get("payload", value.get("elements"))
                    else:
                        bg = None
                    doc, issues = import_payload(value, profile, background=bg)
                result = {"document": doc, "issues": issues}
            elif route == "/api/apply-template":
                result = {
                    "document": apply_template(data.get("id", ""), profile, data.get("values"))
                }
            else:
                self.send_json({"error": "Unknown endpoint"}, 404)
                return
            self.send_json(result)
        except Exception as exc:  # noqa: BLE001 - HTTP boundary returns errors to the UI.
            self.send_json({"error": str(exc)}, 400)


def make_profile(value):
    if not isinstance(value, dict):
        value = {}
    allowed = {
        k: value[k]
        for k in (
            "width",
            "height",
            "rotate",
            "rotate_mode",
            "palette",
            "background",
            "name",
        )
        if k in value
    }
    return (
        CanvasProfile(**allowed)
        if "width" in allowed and "height" in allowed
        else CanvasProfile(200, 120, name="Demo display")
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    print(f"imagespec designer demo: http://{args.host}:{args.port}")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
