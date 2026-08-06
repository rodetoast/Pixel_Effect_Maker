# Project Format v7

애플리케이션 버전은 `0.0.04`를 유지하고, 호환되지 않는 Pixel 디스크 표현 교체를 명시하기 위해 `FORMAT_VERSION`을 7로 올린다. 형식 6의 Resource Layer 모델 의미는 바뀌지 않는다.

## Compact RGBA Payload

일반 Project Frame, PNG `SourceAsset.pixels`, GIF/Aseprite `AnimationClipAsset.frames`는 다음 구조를 공통 사용한다.

```json
{"encoding":"rgba8-zlib-base64","width":64,"height":64,"channels":4,"dtype":"uint8","byte_length":16384,"checksum":"sha256-hex","data":"..."}
```

원본 C-order RGBA8 bytes를 zlib level 1로 압축하고 Base64 ASCII로 기록한다. 동일 입력은 동일 Payload를 만든다. Loader는 크기·4 channels·dtype·예상 byte length·Base64·zlib 종료·SHA-256을 검증하며 64MB를 넘는 decoded frame을 거부한다. 오류를 투명 Frame으로 대체하지 않는다.

## 호환성과 영구 데이터

Loader는 형식 1~6의 Nested List와 형식 7 Payload를 모두 읽는다. 구형 파일 Open은 디스크를 바꾸지 않으며 Save/Save As 때만 형식 7로 기록한다. PNG는 `source_assets`, GIF/Aseprite는 다중 Frame `animation_clips`에 저장된다. ID, 이름, Pivot, `source_path`, `source_format`, GIF Duration/Loop, Aseprite Tag와 모든 Composition/Effect 참조가 영구 데이터다.

`source_path`는 Reimport 정보이며 내장 Pixel의 생존 조건이 아니다. Thumbnail, Preview, Particle/Transform Cache, QImage/QPixmap, Ghost, Interactive Proxy, Prewarm Worker 상태는 파생 UI 데이터이므로 저장하지 않는다.

## Encoded Payload Cache

런타임 64MB LRU는 owner ID/frame, 크기, SHA-256, Encoding과 압축 수준으로 Payload를 재사용한다. 이름·Pivot·경로 변경은 재압축하지 않는다. Pixel checksum이 달라진 Frame만 새로 인코딩한다. Cache 자체는 JSON에 포함하지 않는다.
