# Editor Interaction Policy

## Particle Motion direct manipulation

Orbit/Helix guides expose Motion Center, Radius Start/End, Start Angle, and Helix Axis End. Shift snaps Start Angle to 15 degrees. Press captures one snapshot; moves update only the latest current frame on a 33 ms cadence; release creates one undo command and an exact final render; Escape restores without undo. Middle-drag pan and wheel zoom remain available.

## 감사 결과와 입력 동기화

Effect Editor의 Resource Layer Inspector는 기본 약 300px, 최소 실사용 280px을 기준으로 한다. 내부 ScrollArea 콘텐츠는 Viewport 폭을 따르고 가로 Scroll은 사용하지 않으며, 긴 설정은 세로 Scroll로 접근한다. Transform 조작 모드는 2열 Grid, 숫자와 Keyframe/Easing은 폭을 합산하지 않는 2단 필드로 배치한다.

Resource Layer 2.5D 숫자 입력도 일반 Wheel은 Inspector Scroll, Ctrl+Wheel은 `singleStep` 값 변경 정책을 따른다. Inspector 변경, 명시적 Keyframe, 완료된 Gizmo Drag는 Undo 대상이며 UI Refresh는 Keyframe을 만들지 않는다.

기존 `NewResourceDialog`는 FPS 변경을 Duration 변경으로 처리하고, 소수점 3자리로 표시된 Duration을 다시 Frames 계산에 사용했다. `valueChanged → 다른 SpinBox 변경 → 반올림된 값 재입력` 경로가 반복 Step을 덮어썼다. 현재는 `_duration_seconds`와 `_syncing`을 사용하고 `QSignalBlocker`로 재진입을 막는다. Frames 변경은 `duration=frames/fps`, FPS 변경은 이전 Duration을 보존한 새 Frames, Duration 완료는 `frames=round(duration×fps)`로 정규화한다. Duration의 최소값과 Step은 항상 한 프레임이며 4자리로 표시한다.

현재 Dialog는 Duration과 Frames를 동시에 노출하지 않고 `Length + Unit`으로 통합한다. Frames 단위에서는 FPS 변경 시 정수 frame count를 유지하고, Seconds 단위에서는 입력 초를 유지한 채 `max(1, round(seconds × fps))`로 frame count를 다시 계산한다. 단위 왕복은 항상 정수 frame count를 기준으로 정규화한다.

Loop는 Form의 늘어나는 필드가 아니라 내용 폭의 `QCheckBox`다. 체크 표시와 한국어·영어 텍스트만 Hit Area이며 행 오른쪽 빈 공간은 값을 바꾸지 않는다. Tab 포커스, Space 토글과 Dialog의 Enter/Cancel 동작은 Qt 기본 접근성을 유지한다.

Effect Inspector의 각 활성 입력은 화면에 직접 보이는 Form Label을 가진다. 약 280~320px 또는 큰 글꼴에서 2열이 맞지 않으면 `WrapLongRows`가 Label을 입력 위로 옮긴다. Label은 비어 있거나 0폭이 되지 않으며 Tooltip은 추가 설명에만 사용한다. Boolean의 Random Start는 Form Label 하나만 표시해 문구 중복을 피한다.

Project Canvas 크기가 바뀔 때는 재생을 멈추고 Effect·Particle Preview Manager의 Context revision을 올린 뒤 Canvas Preview를 지운다. 이전 Context에서 완료된 Worker 결과는 거부한다. Canvas 합성도 source와 destination의 높이·폭이 다르면 오래된 Preview를 표시하지 않고 적용된 Project Frame으로 fallback한다.

## Windows Native SpinBox

`_FocusWheelMixin.focusInEvent()`가 Mouse Focus 시 `setStyleSheet()`로 전체 SpinBox를 다시 polish하고 있었다. Windows 네이티브 Up/Down SubControl을 누르는 도중 스타일과 geometry가 재생성되어 Mouse Press/Release가 같은 SubControl에서 끝나지 않을 수 있는 구조였다. 포커스 StyleSheet, 내부 LineEdit event filter, Mouse Press override를 제거했다. Up/Down 버튼, 키보드, 텍스트 선택과 포커스 표시는 Qt 기본 구현이 담당한다.

`ScrollSafeSpinBox`와 `ScrollSafeDoubleSpinBox`는 포커스, 내부 LineEdit 포커스와 텍스트 선택 여부에 관계없이 일반 Wheel을 `event.ignore()`로 상위 ScrollArea에 넘긴다. Ctrl+Wheel은 명시적인 수치 조작으로 받아들이며 120 angle-delta마다 현재 `singleStep` 한 단계를 적용한다. 고해상도 장치의 부분 delta는 누적하고, 방향 전환·일반 Wheel 전환에서도 의도하지 않은 값 변경이 생기지 않게 관리한다. 직접 입력, Native Up/Down과 키보드 Up/Down은 Qt 기본 구현을 그대로 사용한다. 이전 `FocusWheelSpinBox` 이름은 외부 import 호환 Alias로 유지한다.

## UI 설정과 메뉴

`ui/timeline_frame_width`는 프로젝트가 아닌 QSettings에 저장하며 20~96, 기본 36으로 Clamp한다. Effect와 Resource Composition Timeline이 같은 값을 즉시 적용한다. File은 프로젝트·가져오기, Edit는 Undo/Redo·Project Settings·Shortcuts, View는 표시, Export는 실제 출력, Settings는 언어·Interface·External Tools 역할을 갖는다.

## Localization과 Tooltip

활성 MainWindow, Timeline, Particle Panel, Resource Editor와 Interface Settings의 고정 문자열은 `LocalizationService`를 사용한다. FPS, PNG, GIF, Aseprite, X/Y, RGBA와 사용자 입력 이름은 번역하지 않는다. 아이콘·기호 버튼과 Undo/Redo에는 결과와 단축키를 설명하는 한국어·영어 Tooltip을 둔다.

아이콘·기호 전용 버튼은 Tooltip을 필수로 하며, 텍스트 버튼도 이름을 반복하는 대신 동작 결과와 필요한 선택 조건을 설명한다. `tooltip_helper.apply_tooltip()`은 Qt 기본 `setToolTip()`과 주요 Action·Button의 `setStatusTip()`만 사용하며 Mouse/Hover Event를 가로채지 않는다. QAction이나 사용자 설정 명령의 현재 `QKeySequence`를 NativeText로 조합하므로 Keyboard Shortcut 변경 직후 이미 생성된 Tooltip도 갱신된다.

Play/Pause와 Layer Show/Hide처럼 실제 역할이 바뀌는 조작은 상태 전환 경로에서 Tooltip을 다시 적용한다. 언어 변경은 각 화면의 기존 `retranslate` 경로를 통해 이미 생성된 Widget과 QAction까지 갱신한다. Tooltip 누락 감사 테스트는 모든 앱 소유 `QAbstractButton`을 검사하며, Qt가 내부 생성하는 MenuBar overflow와 Table corner 버튼만 구현 세부사항으로 명시적으로 제외한다.

## Undo/Redo

MainWindow의 단일 `application_undo_stack`을 모든 Workspace가 공유한다. 새 프로젝트와 열기에서 Clear하고 저장 성공에서 Clean으로 표시한다. `EditorValueCommand`는 대상 ID·필드·이전값·새값만 보관하며 같은 Editor 변경을 600ms까지 병합한다. Gizmo는 Drag 중 모델을 실시간 갱신하고 Release에서 Command 하나를 만들며 Escape는 시작값을 복원한다.

지원 범위는 Resource Position/Rotation/Scale/Opacity, Keyframe 추가·삭제, Full Rotation, Layer 이름·범위·가시성·Pivot, Asset/Output Pivot과 Gizmo, Effect Frame 추가·복제·삭제, Layer 추가·삭제·가시성, Composition Layer 경로와 Particle System Draft Settings다. Effect Canvas Handle은 Mouse Move 동안 임시 모델을 갱신하고 Release에서 Command 하나만 만들며 Escape는 Command 없이 시작값을 복원한다. Import, 프로젝트 열기, Bake, Export, Composition 생성·삭제와 Transform Generator Draft는 의도적으로 Undo 대상이 아니다.

Full Rotation은 Loop Resource에서 마지막 프레임을 `±360 × turns × (N - 1) / N`으로 만들고, Non-loop에서는 `±360 × turns` 종점을 유지한다. 1프레임 Loop는 0° 키 하나만, 2프레임 Loop는 0°와 ±180°를 사용한다. 선택한 Effect Layer 삭제는 생성 모델과 렌더 출력 레이어를 한 명령으로 제거하며 Resource Composition 원본은 보존한다. 마지막 생성 레이어를 지우면 프로젝트 불변식을 위한 빈 일반 레이어를 두고 Undo 시 원래 모델·픽셀·선택을 복원한다.

Effect Editor의 활성 레이어는 Resource Layer로 통일한다. Resource Editor의 `Add as Layer to Effect`는 Single 모드 레이어를 즉시 만들며, Inspector의 Placement Mode가 Single/Particle Emission을 Undo 가능한 값으로 전환한다. 전환은 ID·순서·Visibility·Resource 참조와 양쪽 설정을 유지한다.

공통 2.5D 값과 Canvas Gizmo는 Inspector나 Timeline 모델을 재구성하지 않는다. 입력은 Layer Transform revision만 갱신하며 오래된 Layer ID/revision 요청은 버린다. 재생, Bake와 PNG/Sequence Export처럼 정확 출력이 필요한 경계에서만 캐시된 원본 RGBA에 최종 Transform을 materialize한다. 일반 Save/Save As는 metadata와 이미 존재하는 Project Pixel만 직렬화한다.

현재 인터랙티브 경로는 33ms 단일 Shot Scheduler를 사용한다. Gizmo Press에서 Particle Base의 Alpha Crop과 QPixmap, 선택 레이어를 제외한 Underlay/Overlay를 한 번 준비한다. Move와 연속 SpinBox 입력은 모델의 정확한 Float를 유지하면서 최신 Projected Quad만 Canvas Proxy에 전달한다. Inspector는 변경된 필드만 동기화하며 상세 Particle Guide와 Ghost는 세션 동안 유예된다.

Resource Layer 선택, 단일 Frame 이동, Preview 종료, Undo/Redo와 정확 렌더 완료 뒤에는 80ms Idle Prewarm을 예약한다. Timeline Drag Scrubbing의 중간 Frame과 Playback 중에는 예약하지 않고, 마지막 Frame 또는 Playback 정지 위치만 준비한다. 새 선택·Frame·Project·Canvas·Placement·Base/Resource/Transform revision·Visibility·Depth signature가 들어오면 request revision을 올려 이전 Worker 결과를 설치하지 않는다. Gizmo Press는 대기 중 요청을 취소하고 이미 설치된 일치 결과를 즉시 활성화하므로 사용자 입력이 Worker 완료를 기다리지 않는다.

Underlay/Overlay 키는 선택 Resource Layer 자체의 Position/Rotation/Scale/Pivot/Perspective를 제외한다. 선택 레이어 앞뒤의 ID, 정확 RGBA 배열 identity, Opacity, Visibility와 stable Z order가 같으면 Transform 확정 뒤에도 재사용한다. 다른 레이어의 정확 결과나 실제 앞뒤 순서가 바뀐 경우에만 새 prefix/suffix pair를 만든다. Composite Pixmap LRU는 64MB, Base Crop LRU는 32MB 상한이며 Project 교체 시 모두 비운다. Prewarm 완료는 Canvas repaint를 요청하지 않는다.

Gizmo Release·Escape, SpinBox `editingFinished` 또는 마지막 입력 120ms 뒤에는 검증된 NumPy Nearest-Neighbor Renderer를 현재 프레임에 한 번 적용하고 Proxy를 제거한다. Playback·Bake·PNG/Sequence Export는 필요한 정확 Frame/Sequence를 materialize한다. Save는 Motion metadata만 기록하며 Renderer를 호출하지 않는다. Proxy Pixmap은 Project나 출력 데이터에 접근하지 않는다.

## Gizmo

Move의 이미지/중앙 영역은 Free, 빨간 X Handle은 X만, 초록 Y Handle은 Y만 정수 픽셀로 변경한다. Scale 모서리는 균등, X/Y Handle은 해당 축만 변경하며 최소 0.01이다. Rotate는 2D Z 회전만 제공하고 Shift는 15°로 스냅한다. Pivot→Rotate→Scale→Axis Move→Free Area 순으로 Hit-test하며 Handle 크기는 zoom과 무관한 화면 기준 픽셀이다.

Effect Canvas는 선택된 Composition Layer의 Start/End와 선택된 Particle System의 Emission Origin, Direction, Expected Endpoint, Emission Shape를 직접 편집한다. Expected Endpoint는 Particle Renderer와 공유하는 degree·pixel/frame 단위 및 Speed/Lifetime 중간값으로 계산한다. Endpoint Drag는 Lifetime을 유지하고 Speed Range 폭을 보존하면서 중심 속도를 바꾼다. 가이드와 Ghost는 Canvas paint overlay이므로 Project compose, Bake와 Export 버퍼에 들어가지 않는다.
