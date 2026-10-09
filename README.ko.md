# imagespec-designer

[CI](https://github.com/eigger/imagespec-designer/actions/workflows/ci.yml) · [PyPI](https://pypi.org/project/imagespec-designer/)

`imagespec`용 독립 시각 편집기와 Python 렌더링 API입니다. YAML 가져오기/내보내기와 디자인 템플릿을 제공합니다. Python 3.13 이상과 `imagespec>=1.0.1`이 필요하며, 0.1.0은 imagespec 1.0.1에서 테스트했습니다. 설치된 패키지 버전은 `imagespec_designer.__version__`으로 확인할 수 있습니다.

## 설치 및 실행

```sh
python -m pip install imagespec-designer
imagespec-designer-demo
```

`http://127.0.0.1:8765`에서 편집기를 엽니다. Data Matrix 렌더링에는 `imagespec-designer[datamatrix]`를 설치하세요.

## Python API

```python
from imagespec_designer import CanvasProfile, render_image

profile = CanvasProfile(width=296, height=128, palette="bwr")
payload = [
    {"type": "rectangle", "x_start": 8, "y_start": 8, "x_end": 287, "y_end": 120, "fill": "black"}
]
render_image(payload, profile).save("preview.png")
```

삽입 방법과 개발 명령은 [영문 README](https://github.com/eigger/imagespec-designer/blob/main/README.md), [개발 안내](https://github.com/eigger/imagespec-designer/blob/main/docs/development.md)를 참고하세요. 템플릿 값은 호스트가 평가한 뒤 렌더링해야 합니다. Home Assistant 센서/날씨와 통합별 서비스 워크플로는 이 패키지의 범위에 포함되지 않습니다.

코드와 BLE ESL에서 가져온 geometry는 MIT, 수정된 Material Design Icons glyph map은 Apache-2.0 라이선스입니다. 자세한 내용은 [NOTICE](https://github.com/eigger/imagespec-designer/blob/main/NOTICE)와 [Apache-2.0 라이선스](https://github.com/eigger/imagespec-designer/blob/main/licenses/Apache-2.0.txt)를 확인하세요. [릴리스 안내](https://github.com/eigger/imagespec-designer/blob/main/docs/releasing.md)에는 첫 PyPI 게시 설정이 있습니다.
