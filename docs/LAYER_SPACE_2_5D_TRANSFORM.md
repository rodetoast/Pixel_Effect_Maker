# Layer Space 2.5D Transform

Pixel Effect Maker v0.0.04의 프로젝트 형식 v9는 Resource Layer의 2.5D 의미를 두 단계로 분리한다.

## 평가 순서

1. Resource Composition 또는 Particle Motion을 로컬 좌표에서 평가한다.
2. `layer_space_transform`을 `Scale → Rotation X → Rotation Y → Rotation Z → Position` 순서로 적용한다.
3. 고정 카메라로 투영하고 RGBA를 래스터화한다. Particle Sprite는 카메라를 향하는 Billboard이며 자체 Rotation Z는 유지한다.
4. 완성된 Layer RGBA에 `surface_transform`을 적용한다.
5. Effect Layer 순서와 Opacity로 합성한다.

Particle Motion의 `Local Perspective`는 v8 결과 호환을 위해 Motion 로컬 단계에서 먼저 적용된다. 이후 Layer Space의 Perspective Strength가 부모 공간의 최종 고정 시점 투영을 담당한다. Layer Space Scale은 Particle 중심·Motion 경로와 Billboard 크기에 함께 상속된다. Particle 합성 순서는 변환된 view Z와 안정적인 생성 순서로 결정한다.

## Gizmo와 Guide

Canvas의 X/Y/Z 축, Rotation X/Y/Z 링, Particle Motion Guide는 렌더러와 `layer_space_transform_service.py`를 공유한다. 축은 현재 회전·스케일·깊이·Perspective가 반영된 로컬 축의 화면 투영이며 각 축에 X/Y/Z 라벨을 표시한다. Gizmo와 Guide는 마우스 입력 즉시 갱신되고, Particle의 정확한 현재 프레임은 latest-wins 백그라운드 작업으로 따라온다.

## v8 마이그레이션

v8의 `effect_resource_layers[].layer_transform`은 이미 래스터화된 레이어 전체를 변형하던 값이다. v9 로드 시 이 값을 `surface_transform`으로 그대로 옮기고 `layer_space_transform`은 Identity로 만든다. 따라서 원본 v8 파일을 덮어쓰지 않으며, 저장 전후의 기존 렌더 결과를 보존한다. Inspector에서 비 Identity Surface Transform은 호환성 경고와 함께 표시된다.

v9 저장은 `layer_space_transform`과 `surface_transform`을 명시적으로 기록하며 구형 `layer_transform` 키를 쓰지 않는다. 미래 형식은 계속 거부한다.

## 이번 범위에서 제외한 항목

카메라 편집 도구, Local/World 전환, Billboard X/Y 기울기, GPU 또는 네이티브 렌더러 전환은 이번 형식과 UI 범위에 포함하지 않는다.
