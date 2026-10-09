"""Validate the built imagespec-designer archives and their bundled assets."""

from __future__ import annotations

import argparse
import tarfile
import tomllib
import zipfile
from pathlib import Path

REQUIRED_WHEEL_ASSETS = {
    "imagespec_designer/web/index.html",
    "imagespec_designer/web/style.css",
    "imagespec_designer/web/designer.js",
    "imagespec_designer/web/embed.js",
    "imagespec_designer/web/icons.json",
    "imagespec_designer/web/locales/en.json",
    "imagespec_designer/web/locales/ko.json",
    "imagespec_designer/templates/simple-card.yaml",
    "imagespec_designer/templates/price-tag.yaml",
}
REQUIRED_LICENSES = {
    "LICENSE",
    "LICENSE-APACHE-2.0",
    "LICENSE-BLE-ESL-DESIGNER",
    "LICENSE-MATERIAL-DESIGN-ICONS",
    "NOTICE",
}


def check_dist(directory: Path) -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text())["project"]
    version = project["version"]
    wheels = list(directory.glob(f"imagespec_designer-{version}-*.whl"))
    sdists = list(directory.glob(f"imagespec_designer-{version}.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit(
            f"expected one wheel and sdist for {version}; found {len(wheels)} and {len(sdists)}"
        )

    with zipfile.ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
        missing_assets = REQUIRED_WHEEL_ASSETS - names
        if missing_assets:
            raise SystemExit(f"wheel is missing assets: {sorted(missing_assets)}")
        bundled_licenses = {name.rsplit("/", 1)[-1] for name in names if "/licenses/" in name}
        missing_licenses = REQUIRED_LICENSES - bundled_licenses
        if missing_licenses:
            raise SystemExit(f"wheel is missing license files: {sorted(missing_licenses)}")
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        metadata = archive.read(metadata_name).decode()
        requirements = [
            line.removeprefix("Requires-Dist: ")
            for line in metadata.splitlines()
            if line.startswith("Requires-Dist: imagespec")
        ]
        if not any(line.startswith("imagespec>=1.0.1") for line in requirements):
            raise SystemExit(f"wheel metadata lacks the imagespec minimum: {requirements}")
        if not any(line.startswith("imagespec[datamatrix]>=1.0.1") for line in requirements):
            raise SystemExit(f"wheel metadata lacks the datamatrix extra minimum: {requirements}")

    with tarfile.open(sdists[0], "r:gz") as archive:
        source_names = {Path(member.name).name for member in archive.getmembers()}
        missing_sources = (REQUIRED_LICENSES | {"pyproject.toml", "README.md"}) - source_names
        if missing_sources:
            raise SystemExit(f"sdist is missing project files: {sorted(missing_sources)}")

    print(f"Validated {wheels[0].name} and {sdists[0].name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=Path("dist"))
    check_dist(parser.parse_args().directory)


if __name__ == "__main__":
    main()
