# Changelog

## Unreleased — v9 Integrated Production Workflow Stability QA

- Added deterministic PNG/animated Resource fixtures that connect Resource Sprite 2.5D, Single/Linear/Orbit/Helix, System and Surface transforms through frame-order access, metadata-only Save/Reload, Playback, Bake, PNG and PNG Sequence output.
- Fixed Transform cache byte accounting after a Resource revision and preserved warm Playback caches when selecting an Effect Resource Layer with no active preview.
- Added v8→v9 hash-preserving Save As, corruption, lifecycle, 20-switch, Undo/Redo and navigation-state integration coverage without changing app version 0.0.04 or FORMAT_VERSION 9.

## Unreleased — 2.5D Inspector Architecture Finalization

- Established Resource Editor Sprite 2.5D as the primary appearance workflow and moved Effect System Space plus compatibility Surface Transform into a default-collapsed Advanced section.
- Added distinct bilingual names and help for Sprite, Motion-local, System and post-raster Surface perspective without changing serializer keys, FORMAT_VERSION 9 or renderer math.
- Added a visible non-identity Surface compatibility status and verified that Advanced UI toggles do not dirty projects, invalidate playback or alter RGBA output.

## Unreleased — Asset Preview Navigation & Projective Raster Accuracy

- Added a pre-Resource Asset Preview pivot overlay, immediate source-local pivot updates, 32px-margin Fit, cursor-anchored 10%–3200% wheel zoom, middle-mouse pan, and Fit/100% controls while retaining nearest-neighbor pixels.
- Unified non-identity Resource 2.5D rasterization around half-open source outer edges and destination pixel centers; samples at `u/v == 1` or otherwise outside the inverse-mapped crop are transparent instead of clamped to the right/bottom border.
- Added independent X/Y orthographic references, perspective-footprint checks, transparent-margin and isolated right/bottom/corner fixtures, small-angle symmetry, and Asset Preview interaction regressions.

## Unreleased — Resource 2.5D Identity Accuracy & Gizmo Clarity

- Added an integer-aligned identity raster path that preserves every source RGBA byte, including transparent RGB, and prevents right/bottom edge duplication caused by mapping outer-edge coordinates through the projective sampler.
- Documented half-open source/alpha bounds and aligned Resource selection geometry with the exact rendered pixel footprint for even, odd, 1×1, full-edge, and transparent-margin assets.
- Clarified the Resource layer pivot with a projected crosshair, active Pivot ring and `P` marker, source-local outer-edge tooltips, and immediate Inspector/Canvas synchronization without baking overlays into output.
- Identified the Effect red X handle as Layer Space `position_x`, gave Resource transform handles priority over overlapping Motion Guide handles, and added localized hover help plus Drag/Inspector/Guide/Undo/Escape coverage.

## Unreleased — 2.5D Interaction & Stability Completion

- Kept Effect Gizmo and Motion Guide geometry in the final GUI overlay during exact/proxy frame replacement, and retried the newest exact revision when it arrived before composite prewarm instead of silently discarding it.
- Reorganized Motion into mode-aware Basic, Orbit Center, Orbit Shape, Helix, Interpolation, and Advanced groups with bilingual enum labels, help text, stable one-line labels, and localized units.
- Centralized bounded Opacity/Perspective metadata, aligned Effect and Resource UI ranges with model validation, and registered the MainWindow undo-index callback as a real Qt integer slot.
- Changed Resource canonical Z rotation to local-plane spin (`Ry @ Rx @ Rz` for column vectors), including renderer, projected axes/quad/ring gizmos, legacy XY-zero compatibility, and Particle-coordinate invariance coverage.

## Unreleased — Layer Space 2.5D Transform v9

- 프로젝트 형식을 v9로 올리고 새 `layer_space_transform`과 호환 `surface_transform`을 명시적으로 분리
- v8 `layer_transform`을 Surface Transform으로 정확히 이관하고 새 Layer Space Transform은 Identity로 초기화
- Single과 Particle의 로컬 좌표, Canvas Guide, XYZ 축 및 회전 링이 하나의 고정 카메라 투영 서비스를 공유
- Particle 중심·Motion·Billboard 크기에 Layer Space Scale/Rotation/Depth/Perspective를 적용하고 변환된 view Z로 안정 정렬
- Particle Transform 드래그는 전체 레이어 Projective Proxy 대신 latest-wins 정확 현재 프레임을 백그라운드에서 계산
- Inspector 기본 섹션을 Layer Space Transform으로 변경하고 비 Identity 호환 Surface Transform 경고 및 편집 영역 추가
- v1~v8 마이그레이션, v8 RGBA 보존, v9 Round-trip, Preview/Playback/Save Cache 회귀 테스트 추가

## Unreleased — 2.5D Rotation Gizmo Interaction

- Fixed Rotate X/Y/Z handles writing `rotate_*` dynamic attributes instead of the canonical `rotation_*` transform fields, which made Canvas and Inspector appear completely unresponsive.
- Preserved transient Proxy interaction, current-frame key editing, one-command release, and zero-render Escape behavior.
- Made edge-on X/Y proxy projection safe when Qt cannot construct an invertible quad transform, and added real QTest drag coverage across all axes, zoom, pan, release, Undo/Redo, Escape, and 100-move performance boundaries.

## Unreleased — Particle Current-frame Consistency

- Fixed paused Timeline access displaying stale persisted Particle layer buffers after metadata-only Motion saves; every requested paused frame now installs one direct deterministic Particle frame.
- Kept current-frame access independent of frame order and Playback cache state, with no full-sequence fallback or format/version change.
- Reject Gizmo worker results whose requested frame no longer matches the current Timeline frame, and added immutable per-particle diagnostics plus Linear/Orbit/Helix, scrub-order, round-trip, Canvas, and stale-result regressions.

## Unreleased — Effect Renderer Throughput

- Replaced full-canvas Effect layer composition with bit-exact non-zero-alpha ROI composition and transparent/empty-output skips.
- Added exact uint8 Particle sprite ROI and opaque fast paths while preserving stable ordering, motion, nearest sampling, and per-particle rounding.
- Added a conservative, preparation-lifetime 64MB cache that renders truly static Single Resource Layers once across a sequence.
- Reduced the representative 600×600/five-layer/Particle-100 12-frame Prebuffer from about 949.52ms to 348.18ms without changing exact output, app version 0.0.04, or format 8.

## Unreleased — Effect Playback Prebuffer

- Added explicit Stopped, Preparing, and Playing states; the playback clock now starts only after the required exact cache is ready.
- Fully prebuffered sequences up to 30 frames within the 256MB budget, and added a bounded half-second ready buffer for longer sequences.
- Added bilingual non-modal preparation progress, warm replay without rerendering, batched cache installation, and cooperative cancellation on Stop, edits, project transitions, close, and gizmo input.
- Selected two low-priority preparation workers after 600×600/five-layer 1/2/4-worker diagnostics, while preserving high-priority interactive gizmo work and exact Bake/Export/Save behavior.

## Unreleased — Effect Editor Gizmo Responsiveness

- Moved cold 2.5D Base rendering and depth-buffer preparation off the GUI thread and made transform/model mutation transient until release.
- Added a 33ms latest-wins, high-priority current-frame worker for Single and Particle Motion guides; drag never materializes a full sequence.
- Added cooperative cancellation for Playback and idle Prewarm work when direct manipulation begins, plus throttled inspector synchronization and partial dirty rectangles.
- Preserved one-command Undo, Escape cancellation, and one exact current-frame install on release without changing app version 0.0.04 or format 8.

## Unreleased — Project Defaults & Effect Playback Performance

- Changed New Project defaults to 600×600, 12 FPS, and 12 frames; FPS keeps the initial one-second frame count linked until Frames is manually edited.
- Changed blank Resource Composition defaults to 300×300 and one second at the current project FPS, while preserving independent editing after creation.
- Added background exact Effect frame preparation, a 256MB runtime-only RGBA/QPixmap LRU, elapsed-time playback with frame dropping, and non-blocking cache misses.
- Added exact cache/Bake/PNG parity, render-revision invalidation, elapsed-clock, byte eviction, and default-policy regression coverage without changing app version 0.0.04 or format 8.

## Unreleased — Project-wide Stabilization & QA Hardening

- Added bounded OS-user-data runtime logging, central exception reporting, worker failure logging, and bilingual Help > Copy Diagnostic Information.
- Hardened v8 load validation for non-finite JSON, future formats, missing payloads, duplicate frame/composition/generated-layer identities, and duplicate keyframes.
- Bounded PNG/GIF imports, normalized Aseprite CLI failures, preserved the current model after failed open, and added Save/Discard/Cancel close handling.
- Added failure-injection, corruption, runtime diagnostic, Dirty-state, editor-state, and LRU regression tests without changing app version 0.0.04 or format 8.

## Unreleased — Early Preview Build Notice

- Added a bilingual, scrollable Early Preview risk and project-overview dialog before normal and explicit-project startup.
- Added revision-scoped QSettings acceptance and a Help menu action that always reopens the overview without changing project JSON.
- Added diagnostic startup bypass coverage, responsive offscreen UI tests, and a reproducible one-folder PyInstaller build definition with a bilingual Preview README.

## Unreleased — Particle Orbit & Helix Motion

- Added deterministic Linear, Orbit, and X/Y/Z Helix motion for Particle Emission.
- Added easing, phase spread, local perspective, stable particle-local Z sorting, shared Canvas guides, and current-frame latest-wins rendering.
- Advanced saves to format v8; v1-v7 particles migrate to Linear while compact v7 frame payloads remain unchanged.
- Changed ordinary Save/Save As to serialize Motion metadata without rendering the current frame or materializing a particle sequence; Bake, playback, and exports retain their exact output boundaries.
- Reused prewarmed Underlay/Overlay composites while Orbit/Helix values change and limited repaint invalidation to the old/new particle, guide, and gizmo bounds.
- Fixed current-frame guide evaluation, Helix axis-end placement, Start Angle continuity across ±180°, Escape restoration, stable equal-depth ordering, and non-finite Motion serialization.
- Added direct/current/full/Bake/PNG output parity, v1-v7 migration, real compact-v8 smoke, save-regression, and composite-cache performance coverage.

## Unreleased

### Added

- 프로젝트 형식 7에 결정적·무손실 `rgba8-zlib-base64` Pixel Payload, SHA-256 검증, 64MB Encoded Payload LRU와 v1~v6 Nested List 로드 호환 추가
- PNG/GIF/Aseprite 내장 프레임·경로·Timing·Tag·Resource/Effect 참조 및 원본 파일 부재 Round-trip 테스트 추가
- Resource Layer 선택·최종 Frame 이동 뒤 80ms Idle에 Particle Base Crop, QImage/QPixmap, Underlay/Overlay를 미리 준비하는 latest-only Prewarm 추가
- 선택 레이어를 제외한 Layer/Frame/Visibility/Depth/Render signature 기반 Prefix/Suffix Composite Cache와 64MB LRU 상한 추가
- Particle Emission/Single 2.5D 연속 조작을 위한 Canvas 전용 QPainter Projective Proxy, Alpha Bounds Crop, Base QImage/QPixmap Cache와 Underlay/Overlay 고정 합성 추가
- Effect Editor 오른쪽 Resource Layer Inspector를 약 280~320px에서도 가로 Scroll 없이 사용할 수 있도록 반응형으로 변경하고, 2.5D 조작 버튼 2열 배치와 Transform/Path/Particle 입력 폭 및 한국어·영어·큰 글꼴 대응을 추가
- Resource Layer 공통 2.5D Transform(Position X/Y/Z, Rotation X/Y/Z, Scale X/Y, Opacity, Pivot, Perspective), Keyframe/Easing, Stable Z 정렬, 3축 Canvas 조작을 Single과 Particle Emission 최종 출력에 동일하게 적용
- FORMAT_VERSION 6을 유지하며 기존 v6과 v1~v5 마이그레이션에 Identity 기본값을 적용하고 Identity 출력은 기존 픽셀과 동일하게 보존
- Effect Editor의 직접 배치와 파티클 방출을 하나의 Resource Layer와 Undo 가능한 Single/Particle Emission Placement Mode로 통합
- 형식 1~5의 직접 배치·Particle 데이터를 ID·순서·Visibility·설정과 함께 형식 6 Resource Layer로 메모리 마이그레이션
- 활성 Editor, Timeline, Gizmo, Particle, Resource 작업과 주요 Dialog에 행동·조건을 설명하는 한국어·영어 Hover Tooltip 추가
- 현재 사용자 설정 단축키와 Play/Pause·Show/Hide 상태를 반영하는 공통 Tooltip 적용 구조 및 누락 자동 감사 테스트 추가
- Resource Composition을 컴포지션 레이어로 직접 배치하거나 파티클 시스템 리소스로 사용하는 두 가지 Effect 추가 경로
- 선택한 컴포지션 레이어의 시작·끝점과 파티클 시스템의 방출 원점·방향·예상 도달점·형태·퍼짐을 재생 전 표시하는 편집 가이드
- 화면 픽셀 크기가 일정한 Canvas Handle, Resource Ghost, Shift 15° 방향 Snap, Escape 취소와 Drag 단위 Undo

### Changed

- 프로젝트 저장을 compact JSON, 동일 디렉터리 Temporary File, flush/fsync, `os.replace` 순서로 강화하고 변경 없는 두 번째 저장과 Metadata-only 저장의 Pixel 재인코딩을 제거
- Save/Save As는 성공 후에만 경로·Dirty 상태를 갱신하고 중복 요청을 거부하며 Directory/Encoding/Temporary/Replace 실패를 한국어·영어로 구분
- Prewarm의 NumPy Alpha Scan과 Underlay/Overlay 합성을 기존 Qt 작업 풀에서 낮은 우선순위로 실행하고, GUI 스레드에는 최신 요청의 이미지 설치만 전달
- 첫 2.5D Gizmo Press가 유효한 Prewarm을 즉시 활성화하며 선택·Frame·Project·Visibility·Depth·Revision 변경 결과와 Scrub/Playback 중 요청을 폐기
- 2.5D 인터랙티브 화면 갱신을 최대 약 30FPS(33ms) latest-wins로 제한하고 SpinBox 종료·120ms Idle·Gizmo Release/Escape에서만 정확한 CPU 결과를 확정
- 작은 Projected Quad 이동은 이전·현재 Bounds와 Gizmo의 합집합 Dirty Rect만 갱신하며, 실제 Z 정렬 경계를 넘을 때만 고정 Depth Buffer를 재구성
- Particle Emission의 원본 RGBA와 공통 2.5D 후처리 캐시를 분리하고 Transform 변경이 Particle Simulation을 무효화하지 않도록 변경
- 좁은 Effect Inspector에서 모든 활성 Property Label을 입력 위로 줄바꿈할 수 있게 하고 한국어·영어 및 125%·150% 글꼴에서도 화면 라벨을 유지
- 통합 Resource Layer의 생성 레이어 표시 이름을 `사용자 이름 · Single/Particle Emission` 형식으로 정리
- Resource Editor의 Add to Effect 선택 메뉴를 `Add as Layer to Effect` 단일 흐름으로 변경하고 Effect Inspector에서 배치 방식을 선택하도록 단순화
- 프로젝트 `FORMAT_VERSION`을 6으로 올리고 새 저장에서 중복된 직접 배치·Particle 배열 대신 `effect_resource_layers`만 기록
- Resource Editor V2의 기본 우측 Inspector를 약 300px로 조정하고, 유효한 사용자 Splitter 저장값은 유지하되 과도하게 넓은 기존 값은 정규화
- SpinBox 일반 Wheel은 상위 패널 스크롤에 맡기고, 명시적인 Ctrl+Wheel만 현재 `singleStep` 단위로 값을 변경
- 사용자 용어를 Effect Composition, Resource Composition, Composition Layer, Particle System, Emission Origin/Shape로 정리
- Effect Timeline을 Visibility 전용 열, Layer Name 열, Frame 열로 분리하고 이름 클릭과 표시 전환을 독립화
- `ui/show_effect_editing_guides` QSettings 토글을 추가하고 기본값을 켬으로 설정

### Fixed

- New Resource의 Loop 체크박스가 행 전체를 차지해 오른쪽 빈 영역에서도 토글되던 Hit Area 문제 수정
- Particle Emission 2.5D 수치·기즈모 조작이 매 입력마다 Particle Simulation과 전체 Preview Sequence를 다시 만들던 문제 수정
- 반응형 Effect Inspector에서 Resource, Emission, Spawn, Motion/Random 및 2.5D 속성명이 사라지던 문제 수정
- Loop Resource의 Full Rotation 마지막 키를 `360 × (N - 1) / N`으로 생성해 루프 경계의 중복 자세를 제거하고 Non-loop는 360° 종점을 유지
- Composition Layer, Particle System 및 기존 Transform Emitter의 생성 출력 레이어를 공통 삭제하고 Resource 원본은 보존하는 Undo/Redo 경로 추가
- 포커스·텍스트 선택 상태와 무관하게 모든 활성 SpinBox의 Wheel 값 변경을 차단하고 상위 ScrollArea가 스크롤을 처리하도록 수정
- Visibility 열 추가 후에도 20/36/64/96px Frame 열 매핑과 Drag Scrubbing이 유지되도록 보정
- 직접 배치 필드가 없는 기존 v5 프로젝트를 기본 빈 목록으로 읽으며 `animation_clip`/`particle_emitter` 직렬화 식별자를 유지

## v0.0.04 - 2026-08-04

### Fixed

- Resource Editor V2의 PNG/GIF/ASE/Aseprite 공통 Drag and Drop Import 경로 복원
- Project Canvas 크기 변경 전 Effect·Particle Preview 무효화와 비동기 Context revision 검사 추가
- Canvas가 현재 Project와 Shape가 다른 오래된 Preview를 합성하다 예외를 내던 문제 수정
- Asset/Resource 및 Workspace 왕복 시 Composition별 Layer·Frame·Gizmo 선택 상태가 사라지던 문제 수정
- 새 Resource Dialog의 Duration·Frames 이중 입력을 Length + Frames/Seconds 단위 입력으로 통합
- Windows 네이티브 SpinBox 화살표 Mouse Press 중 Focus StyleSheet 재적용으로 SubControl 상태가 재생성되던 문제 수정
- Focus-Wheel 공통 위젯을 포커스된 Wheel 입력 제한에만 사용하고 Qt 기본 Up/Down·Mouse·Focus 처리를 복원
- 새 Resource의 FPS·Duration·Frames 신호 재진입과 표시 반올림으로 반복 Step이 되돌아가던 문제 수정
- 활성 Particle 속성, 메뉴, Tooltip의 한국어/영어 런타임 전환 누락 수정
- Resource Editor V2 Asset List의 숨겨진 빈 compatibility 항목과 실제 항목 밖 Hover 영역 제거
- Layer Inspector 속성을 반응형 세로 Property Card로 재배치해 한국어/영어 UI의 가로 잘림 제거
- 1024×720~1600×900에서 Asset Browser·Canvas·Inspector 최소 폭과 Timeline 높이 유지
- 투명 여백이 큰 에셋의 선택 경계와 Handle을 alpha union bounds에 맞춤

### Changed

- `ui/timeline_frame_width` 기반 20~96px 공통 Timeline 폭과 Interface Settings 추가
- Project Settings를 Edit로 이동하고 중복 Export 항목을 전용 Export 메뉴로 정리
- 전역 QUndoStack과 Resource/Effect/Particle 핵심 Command, 600ms 연속 변경 병합 추가
- Move X/Y, Scale X/Y·균등, Shift 15° Rotate 화면 고정 Handle 추가

- Resource Editor V2를 설정 저장형 Horizontal/Vertical Splitter 구조로 변경
- Layer Inspector를 세로 Scroll 전용으로 변경하고 기즈모 선택 버튼을 2×2 Grid로 배치

### Added

- Effect Timeline과 Resource Composition Timeline 공통 클릭 드래그 스크러빙
- 일반 실행용 새 프로젝트 설정·기존 프로젝트 열기 Startup Dialog
- 빈 Resource Editor의 에셋 가져오기·빈 Resource 만들기 시작 패널

- EMPTY/ASSET_INSPECT/COMPOSITION/LAYER_EDIT 상태와 단일 선택 Controller를 사용하는 Resource Editor V2
- 원본 이름·크기·재생 시간 기반 `Create Resource from This Asset` 원자적 생성 흐름
- Canvas 레이어 직접 선택, 선택 경계와 실제 Move/Rotate/Scale/Pivot Handle hit-test
- Asset Frame Strip과 분리된 Composition 전용 Layer × Time Timeline
- QTest 실제 클릭 기반 PNG→Resource→Full Rotation→재생→Particle Preview 회귀 테스트

- 타임라인 기반 Resource Composition, Composition Layer, Animation Track, Keyframe 모델
- Position/Rotation/Scale/Opacity 속성 검색·등록과 Linear/Ease In/Ease Out/Ease In/Out 평가
- 최근접 이웃 Composition Renderer, 레이어 범위·표시·피벗·source-over 합성 및 revision 캐시
- Composition Canvas의 Move/Rotate/Scale/Pivot 기즈모와 한 바퀴 회전 빠른 명령
- Resource Composition을 직접 사용하는 Particle Preview, Bake와 PNG Sequence Export 흐름
- 프로젝트 형식 5와 형식 4 Resource 데이터 보존 마이그레이션

- MainWindow의 기본 Resource Workspace를 모듈화된 Resource Editor V2로 교체
- Particle Composition 시간 계산을 Effect Project FPS 기준 초→Composition FPS 순서로 수정
- 새 프로젝트에서는 Legacy Transform Generator 생성 UI를 숨기고 기존 Generator가 있을 때만 호환 영역 표시

- Resource Editor를 Assets 검사와 Compositions 제작을 함께 제공하는 Resource Composition Editor로 재구성
- Transform Clip Generator를 새 프로젝트의 중심 개념에서 `Legacy Clip Generators` 호환 영역으로 이동

- Effect Editor와 Resource Editor Workspace 전환
- 통합 Resource Library, 다중 Drag and Drop과 공통 Import 명령
- Checkerboard/Nearest Resource Preview, 프레임 duration Timeline과 Workspace 단축키 라우팅
- Pivot 수치·캔버스 Gizmo·Center Pivot 및 Preview invalidation
- External Tools Aseprite Browse/Auto Detect/Validate/Clear 설정
- Resource Reimport, 참조 보호 삭제, Resource에서 Particle Emitter 생성
- 정적 Source와 Animated Clip을 함께 표시하는 Particle Resource Picker

- PNG/GIF 공통 Resource import와 프레임별 duration 보존
- Aseprite 탐색·검증 및 격리된 CLI import adapter
- 정적 Source와 Animation Clip의 Particle 공통 참조
- 한·영 태그 기반 Property Registry 검색 기반
- 타임라인 레이어 헤더를 통한 실제 Layer Visibility 변경
- 프로젝트 형식 4와 v1·v2·v3 마이그레이션

- 프로젝트 내부 독립 Animation Clip과 결정적 Particle Emitter 전체 흐름
- Burst/Over Time, Point/Line/Circle/Box, Fixed/Radial 방향과 Seed 기반 랜덤 범위
- Once/Loop/Hold Animated Particle Preview, 전용 Bake와 PNG Preview Sequence 출력
- Clip Generator Move/Rotate/Scale/Distribution 캔버스 기즈모
- 프로젝트 형식 3 및 형식 1·2 마이그레이션

- 임의 PNG를 프로젝트 내부 RGBA Source Asset으로 가져오는 비파괴 소스 관리
- Effect Library와 Transform Emitter용 Effect Properties 패널
- Point, Line, Circle distribution과 deterministic instance emission
- Position, Rotation, Scale X/Y, Opacity 및 세 가지 easing 렌더링
- Horizontal Tilt, Vertical Tilt, Perspective 최근접 사각형 변형
- 생성기별 전용 Generated Layer와 원자적 재생성
- 프로젝트 형식 2 Source/Generator 직렬화 및 형식 1 마이그레이션
- Generator Draft와 프로젝트 데이터를 분리한 비파괴 Live Preview
- 250ms Auto Preview, 수동 Refresh와 최신 revision 결과만 표시하는 비동기 렌더링
- 이전·다음 프레임 Primary/Alternate 단축키
- 한국어·English 런타임 전환과 언어 설정 유지
- Effect Properties 단위, Tooltip, Start → End 행과 접이식 섹션

- 메인 편집 영역을 저장·복원 가능한 3분할 QSplitter로 변경
- 우측 Properties를 최소 360px의 세로 스크롤 패널로 조정
- Wheel 값 변경은 입력을 실제 클릭해 포커스를 얻은 동안에만 허용

- Generate 버튼을 Apply to Frames로 명확화
- Reset Settings를 Revert Changes와 Reset to Defaults로 분리
- 숫자 및 ComboBox가 포커스 없이 Wheel 값 변경을 소비하지 않도록 개선

## v0.0.03 - 2026-08-03

### Fixed

- Enter 재생 단축키가 실제 메인 편집 화면에서 작동하지 않던 문제
- 재생 단축키가 입력 위젯 및 모달 대화상자와 충돌할 수 있던 문제

### Changed

- Animation 메뉴에서 불필요한 Play / Stop Animation 항목 제거
- 빈 캔버스에서도 재생 상태와 현재 프레임을 확인할 수 있도록 표시 개선

## v0.0.02 - 2026-08-03

### Added

- 편집 가능한 Project Settings 대화상자
- 캔버스 전용 크기 변경과 이미지 포함 스케일 변경
- 캔버스 전용 변경을 위한 9개 Anchor
- Enter 기반 애니메이션 재생·정지 단축키
- 재생 확인용 8프레임 Playback Test Project

### Changed

- Project Info를 Project Settings로 교체
- FPS와 Loop를 프로젝트 생성 후 변경 가능하도록 개선
- Scale 변환을 픽셀아트용 최근접 이웃으로 고정
- 타임라인의 `Layer × Frame Timeline` 제목과 여백 제거

## v0.0.01 - 2026-08-03

### Added

- PySide6 기반 기본 편집기 화면
- 정수 배율 픽셀 캔버스와 투명 체커보드
- 레이어 추가와 삭제
- 프레임 추가, 복제, 삭제
- 프로젝트 JSON 저장 및 불러오기
- 애니메이션 재생과 FPS 설정
- 투명 PNG 프레임 내보내기
- 초기 모델, 파일 입출력, PNG 내보내기 테스트
- 중앙 버전 정보와 `--version` 명령
- Aseprite 기준 `Shift+N`, `Alt+N`, `Alt+B` 기본 단축키
- QSettings 기반 사용자 단축키 설정, 충돌 검사, 기본값 복원
- 읽기 전용 프로젝트 정보 대화상자

### Fixed

- 프레임을 반복 복제할 때 이름에 `Copy`가 누적되던 문제
- 프레임 표시를 현재 순서 기반의 연속 번호로 정리
- 레이어 삭제 후 새 기본 레이어 이름이 기존 이름과 충돌할 수 있던 문제
- 새 프로젝트 설정이 여러 대화상자로 나뉘어 있던 문제

### Changed

- 레이어와 프레임을 교차 셀로 확인하고 선택하는 통합 타임라인 기초 UI 추가
- 새 프로젝트 이름, 캔버스 크기, FPS, 반복 재생을 한 대화상자에서 설정
- 중복된 별도 레이어 패널을 제거하고 통합 타임라인을 레이어 관리 중심으로 변경
- 상시 프로젝트 정보 패널을 `File > Project Info…` 대화상자로 이동
- 제거된 좌우 패널 공간을 중앙 캔버스에 반환
