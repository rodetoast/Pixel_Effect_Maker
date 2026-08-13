# Effect System Foundation

## Particle motion pipeline

Spawn state is deterministic and cached independently from Motion metadata. A live particle is evaluated as `spawn point + local Orbit/Helix`, projected and stably sorted by particle-local Z, rendered as a nearest-neighbor billboard, then passed through Resource Layer 2.5D and stable Effect Layer Z composition. Linear retains the legacy `start + velocity * age` path and generation-order composite. See `PARTICLE_ORBIT_HELIX_MOTION.md`.

## 목적

Single과 Particle Renderer는 Canvas 크기 RGBA 결과에서 합류한 뒤 공통 Resource Layer 2.5D Transform을 거친다. 이 후처리는 Nearest-Neighbor 역매핑, 프레임별 Track 평가, Resource Layer끼리의 Stable Z 정렬을 사용한다. Particle 개별 인스턴스는 계속 2D다.

이 시스템은 특정 초승달, 검기, 불꽃 형태를 판별하거나 파일명에 따라 특수 처리하지 않습니다. 임의의 투명 RGBA Source Asset을 여러 위치와 시간에 인스턴스화하고 동일한 Transform 파이프라인으로 Generated Layer를 만드는 범용 기반입니다.

## 데이터 흐름

외부 PNG/GIF/Aseprite는 Imported Asset이 된 뒤 Resource Editor에서 Resource Composition으로 비파괴 애니메이션화됩니다. Effect Editor에는 Resource Layer 하나로 추가하고 Placement Mode에서 Single 또는 Particle Emission을 선택합니다.

Effect Library의 `Add Resource Layer` 메뉴는 추가할 Resource Composition을 명시적으로 선택한다. 같은 Resource를 여러 번 추가할 수 있으며 각 Effect Resource Layer는 독립 ID, 사용자 이름, Visibility, 포함형 Start/End, Placement Mode, Single/Particle 설정, 2.5D Transform, Motion과 Keyframe Track을 가진다. Effect Layer 이름 변경은 Resource 원본 이름을 바꾸지 않는다.

Effect Library 목록의 위쪽은 Canvas Front다. `Move Front`/`Move Back`은 Effect Resource Layer 모델과 생성 출력 슬롯을 함께 이동하며 Undo/Redo 한 번으로 복원된다. Resource Composition을 삭제할 때 이를 참조하는 Effect Layer가 하나라도 있으면 삭제를 거부하고, Effect Layer 삭제는 Resource Composition 원본을 보존한다.

```text
Imported Asset
→ Resource Composition
→ Resource Layer (Single 또는 Particle Emission)
→ deterministic Particle Instances
→ non-destructive Preview
→ Bake / Preview Sequence Export
```

Source 편집은 원본 리소스 관리, Clip 제작은 짧은 재사용 애니메이션 확정, Particle 합성은 Clip 인스턴스의 시간·공간 배치, Bake는 최종 프로젝트 프레임 적용입니다. Preview Sequence Export는 Bake 없이 현재 revision의 미리보기만 기록합니다.

Source Asset은 일반 프레임 레이어와 분리됩니다. 가져올 때 RGBA NumPy 배열을 복사해 프로젝트 JSON 안에 저장하므로 이후 외부 PNG가 없어도 동작합니다. 기본 피벗은 이미지 중앙이며 현재 UI에서는 읽기 전용입니다. 여러 Emitter가 같은 Source를 공유할 수 있습니다.

## 현재 구현

- Distribution: Point, Line, Circle 및 각도 범위를 이용한 호
- Timing: output frames, instance count, start frame, emission interval, lifetime
- Transform: Position, Rotation Z, signed Scale X/Y, Opacity
- Pseudo-3D: Horizontal Tilt, Vertical Tilt, Perspective
- Easing: Linear, Ease In, Ease Out
- Determinism: 저장된 seed와 안정된 instance 순서

Pseudo-3D는 실제 카메라나 3D 모델이 아닙니다. Source를 네 모서리의 사각형으로 보고 목적지 사변형을 만든 뒤 역방향 좌표 매핑으로 변형합니다. 샘플 좌표는 정수에 반올림하며 Bilinear/Bicubic을 사용하지 않습니다. Opacity는 Source alpha에 곱하고 인스턴스 겹침은 straight-alpha source-over 순서로 합성합니다.

## 비파괴 재생성

Generate는 언제나 원본 Source Asset과 현재 settings에서 전체 출력 버퍼를 새로 계산합니다. 이전 Generated Layer를 다시 변형하지 않습니다. 계산을 완료한 뒤 해당 Emitter의 전용 레이어만 교체하며 일반 레이어, 다른 Emitter 결과와 Source 원본은 바꾸지 않습니다. 출력 프레임이 부족하면 확장하지만 기존 프레임은 삭제하지 않습니다.

통합 Resource Layer에서는 콘텐츠 생성과 공통 2.5D 후처리를 분리한다. Particle/Single 설정, Resource revision, Canvas 크기와 FPS가 바뀌면 Base RGBA를 무효화한다. 공통 2.5D Transform만 바뀌면 Base는 유지하고 현재 프레임의 Nearest-Neighbor 후처리만 다시 계산한다. 고주파 입력은 Transform revision으로 병합하며 오래된 결과를 적용하지 않는다. 전체 Sequence는 재생·Bake·Export가 요구할 때 캐시된 Base에서 지연 생성한다. 일반 Save는 Motion metadata와 기존 Pixel Payload만 원자적으로 직렬화하며 렌더러를 호출하지 않는다.

편집 중에는 현재 프레임의 정확한 Project Buffer를 쓰지 않는다. Canvas가 Base RGBA의 Alpha Bounds Crop을 QPixmap으로 한 번 변환하고, 정확 Renderer와 공유하는 `projected_quad()` 결과에 QPainter Projective Transform을 적용한다. 다른 레이어 합성은 Underlay/Overlay로 고정되며 Depth signature가 달라질 때만 다시 만든다. 이 프록시는 모델 직렬화, Preview/Bake/Export 서비스와 분리된 UI 상태다.

생성 출력의 활성 UI 이름은 사용자 Resource Layer 이름을 보존하고 현재 모드를 덧붙인 `이름 · Single/Particle Emission` 형식이다. Legacy 모델과 Migration 내부 식별자는 호환성을 위해 유지한다.

## Live Preview와 Draft

Properties 입력은 committed Generator settings를 직접 바꾸지 않습니다. Generator별 Draft 복사본이 revision과 dirty 상태를 보유하고, 250ms debounce 후 Source·Draft·캔버스 메타데이터 snapshot만 worker에서 렌더합니다. 결과는 메인 스레드가 수거하며 현재 revision과 Generator/project context가 일치할 때만 PreviewSession에 반영합니다.

Canvas는 Preview 활성 Generator의 실제 Generated Layer를 transient Preview buffer로 대체해 표시합니다. 다른 레이어와 Source 원본은 공유하되 수정하지 않습니다. Preview frame count는 프로젝트와 독립적이며 재생, Enter와 이전·다음 프레임 이동이 Preview 범위를 사용합니다. Save, 프로젝트 JSON과 PNG Export에는 Preview가 포함되지 않습니다.

`Apply to Frames`만 Preview/Draft를 실제 Generator settings와 Generated Layer에 원자적으로 확정합니다. 같은 revision의 Preview가 있으면 재사용하고 없으면 최종 snapshot을 렌더합니다. `Revert Changes`는 committed settings를 Draft로 복원하고, `Reset to Defaults`는 초기값 Draft만 만들기 때문에 다시 Apply해야 확정됩니다.

## 파일 형식

애플리케이션 버전은 `0.0.04`, 최신 프로젝트 `FORMAT_VERSION`은 `9`입니다. 형식 9는 compact `rgba8-zlib-base64` Payload를 유지하고 Resource Layer의 새 Layer Space Transform과 호환 Surface Transform을 분리합니다. 형식 1~8은 메모리에서 마이그레이션하며 원본 파일은 사용자가 저장하기 전까지 다시 쓰지 않습니다. Legacy Transform Generator는 별도 호환 모델로 유지합니다.

## Particle 규칙

모든 범위 난수는 Seed 기반 Instance 생성 시 한 번 확정합니다. Burst는 같은 시점, Over Time은 emission duration에 분산합니다. Point/Line/Circle 표면/Box 내부 생성과 Fixed Direction/Spread, Radial Outward를 지원합니다. 위치는 `start + velocity × age`, 회전은 `initial + angular velocity × age`입니다. Once는 Clip 종료 후 숨고 Loop는 순환하며 Hold는 마지막 프레임을 유지합니다.

Resource Composition 재생 시간은 Effect 프레임 번호를 Composition FPS로 직접 해석하지 않습니다. `particle age / Effect Project FPS`로 실제 초를 계산하고 `Composition FPS × Playback Speed`를 적용해 내부 프레임을 선택합니다. 이 규칙은 12↔24 FPS 조합, 0.5×/2× 속도와 Random Start에서도 동일합니다.

Particle의 Clip Speed Min/Max는 인스턴스 생성 시 Seed 기반 재생 배수를 정한다. UI 범위는 중앙 Numeric 정책의 0.01×~16×(0.1 step, 소수 3자리)이며 2×, 3×와 fractional speed를 정상 값으로 취급한다. Min을 Max 위로 올리면 Max가 Min을 따르고, Max를 Min 아래로 내리면 Min이 Max를 따른다. 이 보정은 Draft와 Undo 한 번으로 적용된다. Model 생성·검증·직렬화도 항상 `clip_speed_min <= clip_speed_max`를 보장하며 legacy 역전 값은 Min을 우선해 Max를 맞춘다. 음수는 Reverse 의미로 사용하지 않는다.

## 후속 확장 지점

현재 deformation 값은 `none`만 허용하며 작동하지 않는 컨트롤은 표시하지 않습니다. 수명 기반 Scale curve, Spread 드래그 핸들, 실행 중 worker 강제 취소는 후속 확장입니다. Bend, Twist, Mesh Deform, Custom Path, 별도 Orbit spawn distribution과 힘장은 아직 구현되지 않았습니다. Particle lifetime Orbit/Helix Motion과 전용 Canvas 기즈모는 구현되어 있습니다.
# Stabilization boundary

Interactive proxy and prewarm results are display-only. Exact playback, Bake,
PNG, and sequence output continue through the exact renderer. Worker exceptions
are logged and failed/stale prewarm results are not installed. Linear, Orbit,
and Helix equations and deterministic output are unchanged by this hardening.
