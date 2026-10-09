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
REQUIRED_LICENSE_FILES = {"LICENSE", "NOTICE", "licenses/Apache-2.0.txt"}
OBSOLETE_LICENSE_FILES = {
    "LICENSE-APACHE-2.0",
    "LICENSE-BLE-ESL-DESIGNER",
    "LICENSE-MATERIAL-DESIGN-ICONS",
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
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        dist_info = metadata_name.removesuffix("METADATA")
        bundled_licenses = {
            name.removeprefix(dist_info + "licenses/")
            for name in names
            if name.startswith(dist_info + "licenses/")
        }
        missing_licenses = REQUIRED_LICENSE_FILES - bundled_licenses
        if missing_licenses:
            raise SystemExit(f"wheel is missing license files: {sorted(missing_licenses)}")
        unexpected_licenses = bundled_licenses - REQUIRED_LICENSE_FILES
        if unexpected_licenses:
            raise SystemExit(
                f"wheel includes unexpected license files: {sorted(unexpected_licenses)}"
            )
        present_obsolete = {Path(name).name for name in names} & OBSOLETE_LICENSE_FILES
        if present_obsolete:
            raise SystemExit(
                f"wheel includes obsolete duplicate licenses: {sorted(present_obsolete)}"
            )
        metadata = archive.read(metadata_name).decode()
        expected_license = project["license"]
        if f"License-Expression: {expected_license}" not in metadata.splitlines():
            raise SystemExit(f"wheel metadata does not declare {expected_license!r}")
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
        source_paths = {
            "/".join(Path(member.name).parts[1:])
            for member in archive.getmembers()
            if len(Path(member.name).parts) > 1
        }
        required_sources = REQUIRED_LICENSE_FILES | {
            "pyproject.toml",
            "README.md",
            "README.ko.md",
            "MANIFEST.in",
            "docs/development.md",
            "docs/releasing.md",
        }
        missing_sources = required_sources - source_paths
        if missing_sources:
            raise SystemExit(f"sdist is missing project files: {sorted(missing_sources)}")
        present_obsolete = {Path(name).name for name in source_paths} & OBSOLETE_LICENSE_FILES
        if present_obsolete:
            raise SystemExit(
                f"sdist includes obsolete duplicate licenses: {sorted(present_obsolete)}"
            )

    print(f"Validated {wheels[0].name} and {sdists[0].name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=Path("dist"))
    check_dist(parser.parse_args().directory)


if __name__ == "__main__":
    main()
