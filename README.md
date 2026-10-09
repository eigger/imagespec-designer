# imagespec-designer

[![CI](https://github.com/eigger/imagespec-designer/actions/workflows/ci.yml/badge.svg)](https://github.com/eigger/imagespec-designer/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/imagespec-designer)](https://pypi.org/project/imagespec-designer/)

A portable visual editor and Python facade for [`imagespec`](https://github.com/eigger/imagespec). It provides a browser editor, YAML import and export, templates, and rendering helpers. The package requires Python 3.13+ and `imagespec>=1.0.1`; version 0.1.0 was tested with imagespec 1.0.1. Check the installed package version with `imagespec_designer.__version__`.

## Install and run

```sh
python -m pip install imagespec-designer
imagespec-designer-demo
```

Open <http://127.0.0.1:8765>. Install `imagespec-designer[datamatrix]` to render Data Matrix elements.

## Python API

```python
from imagespec_designer import CanvasProfile, render_image

profile = CanvasProfile(width=296, height=128, palette="bwr")
payload = [
    {"type": "rectangle", "x_start": 8, "y_start": 8, "x_end": 287, "y_end": 120, "fill": "black"}
]
render_image(payload, profile).save("preview.png")
```

`CanvasProfile` describes dimensions, rotation, and palette. `RenderContext` accepts host callbacks for fonts, images, and history. The public API also provides document validation, frame compilation, YAML conversion, and pixel-difference helpers.

## Embed the editor

Serve the package's `web` assets and mount an editor instance:

```js
import { mount } from "/assets/embed.js";

await mount(document.querySelector("#designer"), {
  title: "Shelf label",
  apiBase: "/api",
  profile: { width: 296, height: 128, palette: "bwr" },
});
```

The host supplies rendering, profile, transport, and any dynamic values. Unresolved templates can be imported and exported, but the host must evaluate them before rendering. This package covers portable imagespec frame documents; Home Assistant sensor/weather components and integration-specific service workflows remain host responsibilities. See [the embedding API](https://github.com/eigger/imagespec-designer/blob/main/imagespec_designer/web/embed.js) and [development guide](https://github.com/eigger/imagespec-designer/blob/main/docs/development.md).

Code and adapted BLE ESL geometry are MIT licensed. The modified Material Design Icons glyph map is Apache-2.0 licensed. See [NOTICE](NOTICE) and [licenses/Apache-2.0.txt](licenses/Apache-2.0.txt). See [release instructions](https://github.com/eigger/imagespec-designer/blob/main/docs/releasing.md) for PyPI Trusted Publishing setup.
