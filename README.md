# Pixel Effect Maker

Effect Editor direct manipulation uses transient, latest-wins current-frame previews so 2.5D and Particle Motion gizmos remain responsive without changing saved Project pixels until release. See [Effect Gizmo Performance](docs/EFFECT_GIZMO_PERFORMANCE.md) for scheduling and exact-output boundaries.

Particle Emission supports deterministic `Linear`, `Orbit`, and `Helix` motion. Orbit provides radius, ellipse, angle, turns, direction, phase spread, and plane rotation; Helix adds X/Y/Z axis travel and particle-local perspective. Local motion is evaluated through the shared Layer Space transform and fixed camera before camera-facing billboard rasterization; ordinary project Save writes metadata without rendering pixels.

Paused Effect Timeline clicks treat persisted Generated Layer pixels as cache/bake artifacts: each visible Particle Resource Layer is evaluated directly for the requested 0-based frame before Canvas composition. This keeps manual scrub output bit-exact with full-sequence, Playback, Bake, and PNG output even after reopening a metadata-only Motion save. See [Particle Current-frame Consistency](docs/PARTICLE_CURRENT_FRAME_CONSISTENCY.md).

New saves use project format v19. Older supported projects load without rewriting the source file. The application identifies itself as `Pixel Effect Maker v0.0.22`.

Particle Emission adds **One Shot / Cyclic Steady** and **Cycle Period** (1..512 frames, default 24). One Shot preserves the v0.0.21 sampled slots and pixels. Cyclic Steady repeats the same seeded burst/over-time schedule, including surviving negative-cycle copies at the first visible frame; it does not simulate history or resample each cycle. Count means total particles per cycle, not a particles/sec API. Birth offsets must fit inside the period and the worst-case simultaneous count must not exceed 4096; invalid edits are rejected without dropping particles. Short periods intentionally repeat the same visual pattern.

Local/static cyclic output satisfies `F(t+P)=F(t)`. Whole-effect seamless loops also require layer, parent and global animation to be periodic. For N output frames with N a period multiple, virtual frame N equals frame 0; the last exported PNG (N-1) need not equal the first. See [Cyclic Emission report](docs/V0_0_22_CYCLIC_EMISSION_REPORT.md) for evidence, limits and manual QA checklist.

Particle Emission now has a localized **Natural Motion** section with signed constant Gravity. Gravity is evaluated analytically from each particle's 0-based age as `0.5 × strength × age²` in the existing particle/system-local frame unit: positive values move down and negative values move up. Linear, Orbit, and Helix remain the base paths; Gravity adds Y displacement before the existing local perspective, Layer/Parent 2.5D, and Surface pipeline. It consumes no random draws and remains exact for Timeline direct seek, full playback, Bake, and PNG export.

Natural Motion also offers **Drag**, an analytic slowdown of the Linear/Orbit/Helix base motion. For actual particle age `t` in frames and non-negative strength `d` in `1/frame`, effective motion age is `-expm1(-d × t) / d` (or exactly `t` when Drag is off or `d = 0`). Linear travel, Orbit angular phase, and Helix phase/axial progress use this effective age; Orbit/Helix radius, center, axis, and initial phase retain their geometry. Gravity remains the independent `0.5 × g × actual_age²` contribution: Drag is not physical air resistance on Gravity. Particle death, sprite animation, and Scale/Color/Alpha over Lifetime also continue to use actual age. Format v16 and older projects default to Drag off/zero without an automatic rewrite.

**Noise** adds deterministic smooth XY positional variation after the base motion and Gravity. Each particle has a distinct path derived from the emitter seed and stable particle ID using fixed 64-bit integer mixing—not Python `hash()` or per-frame random draws. Independent X/Y smooth value-noise channels use quintic interpolation at `actual_age × frequency`; lattice index zero is exactly zero, so a particle never jumps at birth. Strength is the maximum offset on each local axis in pixels, and Frequency controls lattice intervals per frame. Drag affects only the base motion clock: Noise and Gravity both use actual age. Noise is not physical turbulence, velocity integration, or Perlin noise. Format v17 and older projects load Noise disabled without an automatic rewrite.

Particle Emission Resource Layers support `Normal` and `Additive` Blend Modes in the Inspector's Rendering section. Additive uses clamped premultiplied RGB and Alpha contributions while storing valid straight-alpha RGBA, and it applies both between particles in one emitter and between that logical Effect Layer and lower layers. Source alpha, particle opacity, generated-layer opacity, ordering, Color over Lifetime, and Scale over Lifetime remain active. PNG export contains the already baked RGBA result; PNG does not retain a reusable blend-mode instruction for another engine.

Resource and Effect Timelines support runtime-only multi-key editing. Click a key for a single selection, use `Ctrl+Click` to toggle keys, `Shift+Click` for a same-track key range, or drag a marquee across visible Property rows. Drag selected keys horizontally, use `Alt+Left/Right` to nudge, Delete to remove, or the key context menu to batch easing. Timing edits preserve relative spacing and reject the entire operation when an unselected key occupies any destination frame.

Hold `Alt` as a selected-key drag begins to duplicate the complete visible key selection horizontally. Sources remain unchanged and the duplicates become the new selection for fast repeated duplication. The drop is one Undo step and is rejected atomically for source/existing-key collisions or timeline overflow; it never overwrites keys, extends duration, remaps tracks, or touches the clipboard.

Timeline Snap is on by default and can be disabled with the compact toolbar toggle. Normal Move and Alt-drag Duplicate snap one shared batch delta to visible keys, the playhead, or Timeline start/end within an 8-logical-pixel screen threshold. A vertical guide and target label appear only for a valid candidate; invalid candidates are skipped so they cannot block an otherwise valid unsnapped edit. Snap is runtime-only and does not affect keyboard nudge, Copy/Paste, or playhead scrub.

With a Timeline table focused, `Ctrl+C` copies the selected keys and `Ctrl+V` places their earliest key at the current playhead. Copy/Paste preserves original logical Layer/Property tracks, relative timing, values, mixed easing and rotation revolutions. Paste is one Undo step and is rejected atomically for collisions, range overflow, stale projects, missing tracks, or Resource/Effect cross-type payloads; text fields retain native clipboard shortcuts.

Timeline navigation supports cursor-anchored `Ctrl+Wheel` time zoom, middle-drag horizontal pan, Fit Timeline/Visible Keys/Selected Keys, and `Ctrl+Alt+Left/Right` previous/next visible-key navigation. All, Animated, and Selected Layer reveal modes reduce row density without changing Layer selection or project data; hidden key selections are repaired for safe editing.

Resource and Effect editors now support one-level Layer Groups. Select contiguous layers at the same hierarchy level to group them, then collapse, rename, duplicate, reorder, lock, Solo, hide, delete, or ungroup them as one unit. Groups are organization metadata only: they add no transform, keyframe, parent-space math, or Generated Layer, and preserve the existing `List Top = Canvas Front` render order. See [Layer Group Hierarchy](docs/LAYER_GROUP_HIERARCHY.md).

Hierarchy rows now use indentation and disclosure only for Group membership, while Transform Parenting is shown with a separate `[P: Parent]` badge. Primary and additional selections, Visibility, own/inherited Lock, Solo, and empty Groups are readable directly in the list. Long names are elided without displacing state markers and retain their full tooltip. Drag feedback distinguishes moving Before, After, or Into a Group, and hierarchy context menus provide runtime-only Expand All / Collapse All actions.

Resource and Effect Layer lists support **Lock** and multi-select **Solo**. Lock protects transforms, properties, keyframes, direct manipulation, reorder, and deletion while preserving selection, visibility, inspection, Solo, unlock, and duplication. Solo isolates visible soloed layers in the editor Canvas only; PNG, PNG Sequence, and Bake keep the normal Visibility-based final output.

Resource and Effect editors support stable-ID Layer multi-select. Use `Ctrl+Click` to add or remove individual layers, `Shift+Click` for a continuous range, and list-focused `Ctrl+A` for all layers. Duplicate, drag reorder, delete, Lock/Unlock, Solo/Unsolo, Show/Hide, Front, and Back operate on the selection as one Undo step. Position X/Y, Rotation Z, and Scale X/Y support the v0.0.09 multi-transform workflow; other Inspector properties, direct keyframe controls, and unsupported gizmos remain Primary-layer-only.

New projects start at 600×600, 12 FPS, and 12 frames (one second). Until Frames is edited directly, changing FPS keeps the default duration at one second. Blank Resource Compositions start at 300×300 and inherit the project FPS with the same one-second/manual-unlink policy.

Effect playback prepares deterministic exact RGBA frames off the UI thread and displays them from a bounded runtime-only QPixmap cache. Sequences up to 30 frames are fully prebuffered when they fit the 256MB budget, so their first loop starts only after every frame is ready; longer sequences begin after a bounded half-second buffer and retain elapsed-time frame dropping. Direct render, Bake, PNG export, and Save keep their exact existing paths. See [Effect Playback Prebuffer](docs/EFFECT_PLAYBACK_PREBUFFER.md).

The exact Effect renderer composites only each layer's non-zero-alpha ROI, skips transparent results, reuses conservatively static Single layers during one preparation, and keeps Particle/2.5D work bounded to sprite or projected-quad rectangles. These paths remain RGBA bit-exact with the reference renderer. See [Effect Renderer Throughput](docs/EFFECT_RENDERER_THROUGHPUT.md).

This source currently identifies itself as an **Early Preview Build**. Normal startup—including an explicit `.peffect.json` path—shows a bilingual risk and project-overview notice before loading work. Acceptance can be remembered only for the current app version, project format, and notice revision through QSettings; it is never written to project JSON. The overview remains available from **Help > Project Overview and Development Status…**. `--version` and `--check` bypass the notice for diagnostics.

현재 버전은 **v0.0.21**이며 프로젝트 형식은 v18입니다. Particle Inspector의 **자연스러운 움직임 / Natural Motion**에서 Gravity, **움직임 감쇠 / Drag**, **노이즈 / Noise**를 설정할 수 있습니다. Noise는 각 파티클의 고정 ID와 Seed로 정해지는 서로 다른 부드러운 XY 위치 변위를 더합니다. 생성 순간의 변위는 정확히 0이며, 강도는 로컬 X/Y 각 축의 최대 픽셀 변위, 변화 속도는 프레임당 노이즈 구간 수입니다. Drag는 기본 움직임만 느리게 하고 Gravity와 Noise는 실제 age를 사용합니다. 이는 유체 난류나 물리 힘 시뮬레이션이 아닙니다.

Resource Editor의 **Sprite 2.5D**는 리소스 외형을 만드는 기본 흐름입니다. Effect Editor의 **System Space Transform**은 파티클 생성 위치와 Motion 경로를 포함한 전체 좌표계를 바꾸는 Advanced 기능이며, **Surface Transform**은 기존 최종 RGBA 결과를 보존하는 Compatibility 기능입니다. Particle은 변환된 view Z로 안정 정렬하고 카메라를 향하는 Billboard로 래스터화됩니다. 세 단계의 구분은 `docs/2_5D_TRANSFORM_ARCHITECTURE.md`, 수학적 평가 순서는 `docs/LAYER_SPACE_2_5D_TRANSFORM.md`를 참고합니다.

Pixel Effect Maker의 장기적인 목적은 Aseprite를 대체하는 범용 픽셀 편집기가 되는 것이 아닙니다. 사용자가 만든 임의의 투명 PNG를 비파괴 Source Asset으로 가져오고, 범용 Emitter와 시간 기반 Transform으로 여러 프레임의 픽셀 이펙트를 반자동 생성하는 도구를 목표로 합니다. 파일명이나 특정 실루엣에 따른 특수 처리는 사용하지 않습니다.

## 현재 구현 기능

- PySide6 기반 1280 × 800 반응형 메인 창
- 정수 배율·최근접 이웃 렌더링과 투명 체커보드가 있는 중앙 캔버스
- 레이어 추가/삭제 및 프레임 추가/복제/삭제
- 전역 Undo/Redo(`Ctrl+Z`, `Ctrl+Shift+Z`, `Ctrl+Y`)와 축 제한 Move/Scale·2D Rotate 기즈모
- 설정에서 20~96px로 조절하고 재시작 후 복원되는 공통 Timeline Frame Width
- 레이어를 행, 프레임 번호를 열로 표시하고 클릭 드래그 스크러빙을 지원하는 통합 타임라인
- Ctrl/Shift/Marquee 선택, 수평 Drag, Alt+Arrow Nudge, Delete, Batch Easing과 Playhead 기준 Ctrl+C/V를 지원하는 Timeline Multi-Key 편집
- 통합 타임라인 안에서 레이어·프레임 추가 및 삭제
- 프레임 애니메이션 재생/정지와 1–120 FPS 설정
- 일반 실행 시 먼저 표시되며 이름, 캔버스 크기, FPS, 초기 프레임 수, 반복 재생 또는 기존 프로젝트 열기를 선택하는 시작 대화상자
- Aseprite 기준 기본 단축키와 사용자 단축키 설정
- `File > Project Settings…`에서 이름, FPS, Loop, 캔버스 크기 변경
- 9개 anchor 기반 Canvas Only resize와 최근접 이웃 Scale
- 메인/숫자 키패드 `Enter` 또는 타임라인 재생 버튼을 통한 애니메이션 재생·정지
- 빈 캔버스에서도 보이는 Playing/Stopped, 현재 프레임, 전체 프레임 수, FPS 상태 표시
- 현재 프레임 열 강조와 자동 스크롤
- RGBA/RGB/인덱스/그레이스케일 PNG의 독립 Source Asset 가져오기와 프로젝트 내부 픽셀 저장
- Imported Assets, Resource Compositions, Resource Layers와 Legacy Clip Generators를 구분하는 편집 흐름
- Point, Line, Circle 배치의 범용 Transform Emitter
- Position, Rotation Z, 독립 Scale X/Y, 반전, Opacity의 수명 기반 보간
- Horizontal Tilt, Vertical Tilt, Perspective의 최근접 사각형 변형
- Linear, Ease In, Ease Out 공통 easing
- 생성기별 전용 Generated Layer와 비파괴·원자적 재생성
- Generator별 Draft와 실제 프로젝트를 분리한 비파괴 Live Preview
- 250ms Auto Preview, 수동 Refresh, Apply to Frames와 Revert Changes
- Preview 전체 프레임 재생 및 현재 표시 대상 배지
- `Left`/`<`, `Right`/`>` 이전·다음 프레임 이동
- 한국어·English 런타임 UI 전환과 QSettings 유지
- 저장 가능한 3분할 Splitter, 스크롤 가능한 우측 패널과 클릭 포커스 기반 Wheel 입력
- Move/Rotate/Scale/Distribution Clip Generator 캔버스 기즈모
- 독립 RGBA Animation Clip 생성·명시적 업데이트 및 공유
- Seed 결정적 Particle Emitter와 Animated Particle Preview, Bake, PNG 시퀀스 출력
- Particle별 normalized lifetime을 사용하는 uniform Scale over Lifetime Start/End/Easing과 기존 Alpha easing의 무손실 Inspector 편집
- PNG/GIF Embedded Resource, GIF 프레임 duration과 정적 Resource Particle 재생
- 프로젝트 레이어별 표시 전환과 형식 8 compact Pixel/Resource Layer 저장
- Effect Editor/Resource Editor Workspace 전환과 통합 Resource Library
- PNG/GIF/Aseprite 다중 Drag and Drop, 전용 Preview·duration Timeline·Pivot 편집
- 비어 있는 Resource Editor에서 에셋 가져오기 또는 빈 Resource Composition 생성을 선택하는 시작 패널
- 정적/애니메이션 Resource 공통 Particle Picker와 Resource→Emitter 생성
- QSettings 기반 External Tools Aseprite 경로 탐색·검증
- 움직이는 8프레임 `Playback Test Project`
- `.peffect.json` 형식 8 저장/불러오기와 형식 1~7 프로젝트 자동 마이그레이션
- 합성 프레임의 투명 PNG 순차 내보내기
- 미저장 변경 표시와 닫기/새 프로젝트/불러오기 시 확인

## 폴더 구조

```text
app/          PySide6 UI, 모델, 저장·내보내기 서비스
tests/        데이터 모델, 파일 입출력, 버전 테스트
projects/     사용자 프로젝트 파일(기본 Git 제외)
exports/      PNG 내보내기 결과(기본 Git 제외)
docs/         개발 문서, 로드맵, 수동 테스트 체크리스트
assets/       향후 정적 에셋
```

## 설치

Python 3.13 기준입니다. 프로젝트 루트에서 다음 명령을 실행합니다.

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 실행과 진단

일반 실행:

```bat
run_app.bat
```

또는:

```bat
.venv\Scripts\python.exe -m app.main
```

메인 창을 생성한 뒤 즉시 정상 종료하는 시작 점검:

```bat
.venv\Scripts\python.exe -m app.main --check
run_app.bat --check
```

GUI를 생성하지 않고 버전 확인:

```bat
.venv\Scripts\python.exe -m app.main --version
```

임시 공유 빌드는 `Pixel_Effect_Maker.spec`과 `build_preview.bat`의 one-folder 구성을 사용합니다. 빌드 환경에는 `requirements.txt`와 별도 `requirements-build.txt`를 설치하며, 사용자 `projects`, `exports`, Archive, Snapshot, 테스트와 캐시는 포함하지 않습니다.

## 키보드 단축키

| 명령 | 기본 단축키 | 동작 |
|---|---|---|
| New Layer | `Shift+N` | 충돌하지 않는 기본 이름으로 새 레이어 생성 |
| New Frame | `Alt+N` | 현재 프레임을 독립 복사해 바로 다음에 삽입 |
| New Empty Frame | `Alt+B` | 투명 프레임을 현재 프레임 다음에 삽입 |
| Play / Stop Animation | `Enter` | 애니메이션 재생과 정지 전환 |

`Edit > Keyboard Shortcuts…`에서 변경, 비활성화, 기본값 복원이 가능합니다. 사용자 설정은 QSettings에 저장되며 프로젝트 JSON에는 포함되지 않습니다. 동일한 단축키를 여러 명령에 지정할 수 없습니다. 기본 `Enter`는 메인 편집기의 일반 선택 상태에서 메인 Return과 숫자 키패드 Enter를 모두 지원하며, 텍스트·숫자·단축키 입력 중이거나 모달 대화상자 또는 메뉴가 열린 동안에는 재생을 전환하지 않습니다.

`File > Project Settings…`에서 프로젝트 이름, FPS, 반복 재생과 캔버스 크기를 변경합니다. Canvas Only는 픽셀 크기를 유지한 채 9개 anchor를 기준으로 공간을 추가하거나 자르고, Scale은 모든 프레임·레이어를 최근접 이웃으로 변환합니다. 축소와 Scale처럼 되돌릴 수 없는 변경은 적용 전에 확인합니다.

`File > Import Source Asset…` 또는 왼쪽 Effect Library에서 PNG를 가져온 뒤 `Add Transform Emitter`를 누릅니다. 오른쪽 Effect Properties의 값을 바꾸면 기본 250ms debounce 후 중앙 캔버스에 비파괴 Live Preview가 나타납니다. Preview는 프로젝트 저장·내보내기 대상이 아니며 `Apply to Frames`를 눌러야 `Generated: <이름>` 레이어에 확정됩니다. `Revert Changes`는 마지막 적용값으로, `Reset to Defaults`는 초기 Draft로 돌아가며 둘 다 적용 전에는 프로젝트를 변경하지 않습니다.

`Settings > Language`에서 한국어와 English를 즉시 전환할 수 있습니다. 언어와 Auto Preview 설정은 프로젝트가 아닌 QSettings에 저장됩니다.

## Resource Composition 빠른 흐름

`Resource Editor`가 비어 있으면 시작 패널에서 PNG/GIF/Aseprite를 가져오거나 300×300, 현재 프로젝트 FPS, 1초 길이를 기본값으로 빈 리소스를 만들 수 있습니다. 에셋 기반 리소스는 원본 크기를 유지하면서 프로젝트 FPS와 1초 길이를 상속합니다. 에셋을 선택하고 `Create Resource from This Asset`을 누르면 리소스와 첫 Layer가 한 번에 생성됩니다. 이어서 `Full Rotation`을 누르면 전체 구간에 0°→360° 키프레임이 만들어져 바로 재생할 수 있습니다. Asset 검사 중에는 Composition Timeline과 기즈모가 숨겨지고, Resource와 Layer를 편집할 때만 관련 Canvas·Inspector·Timeline이 표시됩니다.

완성한 Composition은 `Use This Resource in Effect`으로 Particle Emitter를 생성하고 Effect Editor에서 바로 Preview할 수 있습니다. Particle 시간은 Effect Project FPS를 초 단위로 변환한 뒤 Composition FPS와 Playback Speed를 적용합니다. 자세한 구조는 [Resource Editor](docs/RESOURCE_EDITOR.md)와 [Resource Compositions](docs/RESOURCE_COMPOSITIONS.md)를 참고합니다.

브러시 없이도 재생을 확인하려면 `File > Create Playback Test Project`를 사용합니다. 투명 배경 위의 8×8 사각형이 8프레임 동안 좌우로 이동하며 일반 프로젝트와 동일하게 저장·불러오기·PNG 내보내기가 가능합니다.

## 테스트

```bat
.venv\Scripts\python.exe -m pytest -q
```

Early Preview 오류 보고에는 `Help > Copy Diagnostic Information`을 사용합니다.
회전 로그는 OS 사용자 데이터 영역에 저장되며 Project JSON, Pixel Payload,
Asset 내용은 기록하지 않습니다. 손상 프로젝트와 더 새로운 형식은 현재
프로젝트를 교체하지 않고 안전하게 거부합니다. 자세한 정책은
[Stability and Diagnostics](docs/STABILITY_AND_DIAGNOSTICS.md)를 참고합니다.

## 기본 파일 위치

- 프로젝트: `projects/*.peffect.json`
- PNG 내보내기: `exports/*.png`

파일 대화상자에서 다른 위치도 선택할 수 있습니다. 생성된 프로젝트와 내보내기 결과는 기본적으로 Git에서 제외됩니다.

프로젝트 형식 8은 형식 7의 compact Pixel Payload를 유지하면서 Particle Motion metadata를 추가합니다. 일반 Canvas Frame, PNG Source Asset과 GIF/Aseprite Animated Resource의 RGBA를 프로젝트 안에 무손실로 내장합니다. `source_path`는 Reimport 위치일 뿐이므로 원본 파일이 이동하거나 삭제돼도 저장된 픽셀과 Resource Composition은 계속 편집할 수 있습니다. 기존 형식 1~7도 읽으며 다음 Save에서 형식 8로 기록합니다.

저장은 대상과 같은 폴더에 Temporary File을 완성하고 flush/fsync한 뒤 atomic replace합니다. 일반 Save/Save As는 Motion metadata와 이미 존재하는 Project Pixel만 기록하고 Particle current/full sequence, Bake 또는 Export를 실행하지 않습니다. 실패하면 기존 파일, Dirty 표시와 이전 Save As 경로가 유지됩니다. Preview, QImage/QPixmap, Interactive Proxy와 Prewarm Cache는 프로젝트에 저장되지 않습니다.

## Parenting

Resource 및 Effect의 Leaf Layer를 같은 Composition 안의 다른 Leaf에 연결하면 부모의 Position X/Y, Rotation Z, Scale X/Y를 따라갑니다. 부모를 설정·해제·변경해도 현재 재생 프레임의 화면상 Transform은 유지되며 기존 Local Keyframe은 다시 쓰지 않습니다. Rotation X/Y, Position Z와 Perspective는 각 Leaf의 Local visual deformation으로 유지됩니다. Group은 목록 정리용이며 Parenting 및 Transform과 독립적입니다.

## Multi-Transform

Resource Editor와 Effect Editor에서 Leaf Layer를 여러 개 선택하면 하나의 Selection Pivot을 기준으로 Canvas에서 함께 이동하고 Rotation Z를 회전하거나 Scale X/Y를 조절할 수 있습니다. Canvas 조작은 World 공간에서 계산되며, Parenting된 레이어는 각 Parent 공간의 Local Position으로 정확히 역변환됩니다. 선택된 Parent와 Child는 Canvas에서 중복 변형되지 않습니다.

Inspector의 Position X/Y, Rotation Z, Scale X/Y는 각 선택 Layer의 Local Transform을 절대값으로 일괄 편집합니다. 서로 다른 값은 `—`로 표시되고, 애니메이션 중인 각 Track에는 기존 conditional Auto-Key 규칙이 적용됩니다. Group Transform과 Position Z, Rotation X/Y, Perspective, Opacity의 다중 편집은 지원하지 않습니다.

## 현재 지원하지 않는 기능

- 브러시, 지우개, 스포이트, 채우기, 선택
- Custom Path, Spiral, 별도 Orbit spawn distribution (Orbit/Helix lifetime motion은 지원)
- Bend, Twist, Wave, Bulge, Pinch, 자유 Mesh Deform
- 그래프 기반 속성 커브 편집, 다중 키프레임 선택·드래그
- Resource Composition 레이어 재정렬과 중첩 Composition
- 스프라이트 시트, GIF, Unity, Godot 내보내기
- PyInstaller 실행 파일 배포

프레임은 타임라인에서 현재 배열 순서를 기준으로 `1`, `2`, `3`처럼 표시됩니다. 프로젝트 파일 호환성을 위해 프레임의 기존 `name` 필드는 유지하지만 타임라인 번호에는 사용하지 않습니다. 새 프로젝트의 캔버스 범위는 현재 모델 제약에 맞춘 `1–1024`, FPS 범위는 `1–120`입니다.

기본 화면은 왼쪽 `Effect Library`, 중앙 캔버스, 오른쪽 `Effect Properties`, 하단 통합 타임라인으로 구성됩니다. 구현되지 않은 Bend, Twist, Mesh 등의 컨트롤은 표시하지 않습니다. 상단 `Animation` 메뉴는 향후 명령을 위한 자리로 유지하지만 현재는 비어 있으며, 재생은 타임라인 버튼 또는 단축키로 조작합니다. 자세한 생성 규칙은 [Effect System](docs/EFFECT_SYSTEM.md)을 참고합니다.
