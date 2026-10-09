# imagespec-designer

[![CI](https://github.com/eigger/imagespec-designer/actions/workflows/ci.yml/badge.svg)](https://github.com/eigger/imagespec-designer/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/imagespec-designer)](https://pypi.org/project/imagespec-designer/)

A standalone visual editor, portable document format, and stable rendering facade for [`imagespec`](https://github.com/eigger/imagespec). The package includes an interactive browser editor, YAML interchange, starter designs, frame and layer helpers, and a small Python demo host. It does not require Home Assistant. The package declares `imagespec>=1.0.1`; this release has been tested with imagespec 1.0.1, and newer versions are allowed but have not been verified here. The package version is available as `imagespec_designer.__version__` and appears in the editor header. Integrations can depend on `imagespec-designer` and use its public API without importing imagespec internals.

```sh
python -m pip install -e .
imagespec-designer-demo
```

Open <http://127.0.0.1:8765>. The demo supports a 200×120 monochrome display and persists its working document in the browser. Install `imagespec-designer[datamatrix]` when designs may include Data Matrix codes. The optional `ha` extra is for applications that want the Home Assistant template/font adapter; core imports and rendering do not load Home Assistant.

## Current scope

The shared editor handles portable imagespec frame documents, renderer metadata, imported imagespec payloads, and generic host callbacks. The BLE ESL manager, Home Assistant sensor/weather components, stored automation workflows, and integration-specific write services remain in the existing integrations. Those host workflows can use the editor API and optional evaluator boundary, but are not part of this first standalone package. Existing integration source trees are unchanged.

## Python API

```python
from imagespec_designer import CanvasProfile, RenderContext, render_image
from imagespec_designer import empty_document, compile_document, validate_document

profile = CanvasProfile(
    width=296,
    height=128,
    rotate=90,
    rotate_mode="canvas",
    palette="bwr",
    background="white",
    name="Shelf tag",
)
document = empty_document(profile)
document["elements"].append(
    {
        "id": "title",
        "type": "imagespec",
        "x": 12,
        "y": 8,
        "width": 250,
        "height": 32,
        "spec": {"type": "text_fit", "value": "Coffee", "size": 24},
    }
)
document = validate_document(document, profile)
payload = compile_document(document)
image = render_image(payload, profile, context=RenderContext())
image.save("preview.png")
```

`CanvasProfile` owns display dimensions, palette and rotation. `RenderContext` accepts host callbacks for `font_resolver`, `history_provider` and `image_fetcher`, along with renderer options. Calls to `render_image` return a Pillow RGB image. `validate_payload`, `known_types`, `element_specs`, `palette_names`, and `dither_methods` expose stable JSON friendly metadata and validation results. `__version__` reports this package's version. `ENGINE_VERSION` reports the installed imagespec version; `MIN_IMAGESPEC_VERSION` and `TESTED_IMAGESPEC` report the declared minimum and the version tested for this release.

A v1 document stores canvas metadata, a background, and movable frames. Each frame holds one regular imagespec element under `spec`. `compile_document` maps frame geometry to the engine payload. `import_payload` accepts payload lists and reports items that cannot be placed. `load_yaml` and `dump_yaml` handle safe YAML interchange; YAML aliases are rejected and input is bounded. `design_templates` lists bundled designs, and `imagespec_designer.templates.apply_template(id, profile, values)` creates one with parameter substitution. `resolve_templates(value, resolver)` keeps host evaluation outside the document model while preserving typed results. Payload validation permits unresolved field templates for import/export, while `render_image` returns a clear error until the host resolves them. Templated placement coordinates are reported as unplaceable because frames need numeric coordinates.

## Embedding the editor

The UI is an ES module at `imagespec_designer/web/designer.js`. Serve the `web` directory and provide `window.imageSpecDesignerHost` before loading `designer.js`. The host object can set:

```js
window.imageSpecDesignerHost = {
  title: "Label layout",
  profile: {width: 296, height: 128, rotate: 0, rotate_mode: "canvas",
            palette: "bwr", background: "white", name: "Shelf label"},
  messages: {"Import YAML": "Import layout"},
  async render({document, profile}) { /* return {data_url: "data:image/png;base64,..."} */ },
  async saveDocument({document}) { /* store through the host */ },
  async loadDocument() { /* return {document} or null */ },
};
```

The optional `web/embed.js` module exports `mount(root, host)`. It creates one isolated frame per instance, so hosts can mount independent editors. Set `host.api` or `host.apiBase` to choose the host transport. The editor displays the package version returned in metadata; hosts with a custom metadata API can instead pass `host.packageVersion`. Without host callbacks, the editor uses its JSON HTTP API (`/api/metadata`, `/api/render`, `/api/validate`, `/api/parse-yaml`, `/api/dump-yaml`, `/api/templates`, `/api/apply-template`) and browser local storage for saving. A host with entities or templating can evaluate document values through `resolve_templates` and provide `RenderContext` callbacks on its server; the UI only sees host-injected results and wording. Pointer dragging and resizing, keyboard undo/redo, layer ordering, duplicate/delete, schema-driven property controls with an advanced JSON editor, template parameters and design/payload YAML import/export are part of the shared editor.

`imagespec_designer.integrations.homeassistant` is an explicit optional boundary. It imports Home Assistant only when its helper functions are called; integrations remain responsible for their service actions and persistence.

## Development

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -e ../imagespec -e '.[dev]'
.venv/bin/python -m pytest
.venv/bin/python -m build
npm install
npx playwright install chromium
npm run test:ui
node --check imagespec_designer/web/designer.js
```

## Release

Update `project.version` in `pyproject.toml`, merge the change, and publish a GitHub Release whose tag is `v<version>` (for example, `v0.1.0`). The release workflow checks that the tag matches the package version, runs the same complete CI workflow, and publishes the resulting wheel and source archive to PyPI only after all checks pass.

Before the first release, add a pending GitHub Trusted Publisher from your [PyPI account Publishing settings](https://pypi.org/manage/account/publishing/). Use project name `imagespec-designer`, owner `eigger`, repository `imagespec-designer`, workflow `release.yml`, and environment `pypi`. PyPI creates the project on the first successful upload; a pending publisher does not reserve the project name until then. The GitHub `pypi` environment is configured for `v*` tags. Publishing uses OIDC and needs no PyPI API token. See [PyPI's guide to creating a project through OIDC](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) for the setup steps.

`imagespec` is MIT and Apache-2.0 with upstream notices and bundled asset license files. This package retains those license and notice files. Its new adapter, document, demo, and UI code use MIT; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
