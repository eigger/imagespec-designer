# imagespec-designer

`imagespec` 레이아웃을 편집하고 미리 볼 수 있는 독립 패키지입니다. Python 3.13 이상과 `imagespec>=1.0.1`이 필요하며 Home Assistant 없이 실행할 수 있습니다. 현재 패키지 버전은 `imagespec_designer.__version__`으로 확인할 수 있고 편집기 헤더에도 표시됩니다. 이 릴리스는 imagespec 1.0.1로 테스트했으며 이후 버전도 설치할 수 있지만 아직 검증하지 않았습니다.

```sh
python -m pip install -e .
imagespec-designer-demo
```

브라우저에서 `http://127.0.0.1:8765`를 엽니다. 요소 추가, 드래그 및 크기 조절, 속성 편집, 레이어 순서 변경, 실행 취소/다시 실행, 디자인 템플릿, YAML 문서 가져오기/내보내기를 지원합니다.

Python API는 `__version__`, `CanvasProfile`, `RenderContext`, `render_image`, `validate_document`, `compile_document`, `import_payload`를 제공합니다. 세부사항은 [README.md](README.md)를 참고하세요.

## 릴리스

`pyproject.toml`의 `project.version`을 변경하고 `v<버전>` 태그(예: `v0.1.0`)로 GitHub Release를 게시하면 릴리스 워크플로가 태그와 패키지 버전을 비교하고 전체 CI를 실행합니다. 검증을 통과한 빌드만 PyPI에 게시합니다.

첫 릴리스 전에 [PyPI 계정의 Publishing 설정](https://pypi.org/manage/account/publishing/)에서 pending GitHub Trusted Publisher를 등록해야 합니다. 프로젝트 이름은 `imagespec-designer`, owner는 `eigger`, repository는 `imagespec-designer`, workflow는 `release.yml`, environment는 `pypi`로 설정합니다. 첫 업로드가 성공하면 PyPI 프로젝트가 생성됩니다. pending publisher는 첫 게시 전까지 프로젝트 이름을 예약하지 않습니다. GitHub의 `pypi` environment는 `v*` 태그만 허용하도록 설정되어 있습니다. 게시에는 OIDC를 사용하므로 PyPI API 토큰이 필요하지 않습니다. 자세한 절차는 [PyPI OIDC 프로젝트 생성 안내](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)를 참고하세요.
