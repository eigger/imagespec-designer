# Development

Create an environment and install the package with its development tools:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,datamatrix]'
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -q
```

On Windows, use `.venv\Scripts\python.exe` and `.venv\Scripts\ruff.exe`.

For browser tests, install the locked Node dependencies and Playwright Chromium:

```sh
npm ci
npx playwright install chromium
```

Set `PYTHON` to the environment interpreter before running Playwright so its demo server uses the same installation. On macOS or Linux:

```sh
PYTHON=.venv/bin/python npm run test:ui
```

In PowerShell:

```powershell
$env:PYTHON = ".venv/Scripts/python.exe"
npm run test:ui
```

To build and inspect distributions:

```sh
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*
.venv/bin/python scripts/check_dist.py
```

GitHub Actions runs these checks, tests the lowest allowed direct dependency versions, and smoke-tests an isolated wheel install.
