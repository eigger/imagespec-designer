# Release

Update `project.version` in `pyproject.toml`, merge the change, and create a GitHub Release from the matching `v<version>` tag, such as `v0.1.0`. The release workflow verifies the tag, runs the full CI workflow, then publishes its wheel and source archive to PyPI through OpenID Connect. The GitHub `pypi` environment permits `v*` tags.

Before the first release, register a pending GitHub Trusted Publisher on the [PyPI account Publishing page](https://pypi.org/manage/account/publishing/):

- Project name: `imagespec-designer`
- Owner: `eigger`
- Repository: `imagespec-designer`
- Workflow: `release.yml`
- Environment: `pypi`

PyPI creates the project after the first successful upload. A pending publisher does not reserve the project name before then. No PyPI API token is needed. Follow [PyPI's guide to creating a project through OIDC](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) for the account settings steps.
