# UX-1 — Inspector Design System & Component Foundation

## 1. Baseline / Audit Checkpoint

2026-10-02, 실제 작업 루트 `C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker`.
Source of truth는 working tree의 UI_UX_ARCHITECTURE_AUDIT / UI_UX_PRINCIPLES /
POST_V0_0_25_EFFECT_CAPABILITY_RECHECK / EFFECT_AUTHORING_CAPABILITY_AUDIT다.

시작 HEAD `01797ec946ec39c90de34c60253b7802c386c054`, main ahead44,
v0.0.25 / FORMAT_VERSION22 / staged0. Baseline pytest: **1732 passed in 101.69s**
(`C:\Dev\pem_ux1_baseline`). 승인된 Audit 파일 6개만 explicit stage하여
`Document capability and editor UX audits` local checkpoint를 만들었다.

Checkpoint full hash: **`d5aaad2c7787c86b6f7d969fec6bc3547ca3fb1d`**.
그 직후 staged0, main ahead45. 아래 UX-1 변경은 이 commit에 포함되지 않는다.

## 2. Existing UI Foundation Audit

기존 foundation은 부재가 아니라 부분적으로 이미 존재했다. `layout_metrics.py`는
column minima/defaults, compact30, Timeline 높이의 source of truth다.
`timeline_command_bar.command_group`에는 commandGroup/commandRole가 있고,
palette 기반 highlight/border, tooltip_helper, ScrollSafe/RotationSpinBox,
NUMERIC_PROPERTY_SPECS와 기존 value command를 유지해야 한다.
Particle section의 개별 QGroupBox/QFormLayout과 status/enable 패턴만 pilot으로 바꿨다.

QSettings는 shortcut/language/workspace 등 project-independent preference에 이미
사용된다. 이번 접기 상태는 그와도 분리된 작은 세션 메모리를 선택했다.
`ResourceLayerTransformPanel`의 advanced check state는 기능 bypass이며
새 disclosure API로 치환하지 않았다.

## 3. New Tokens / Components

기존 `layout_metrics.py`에 SPACING_XS/SM/MD/LG, section margin/spacing,
row spacing, inline/tool/primary control height, section header height를 추가했다.
`inspector_color(role, palette)`는 primary/secondary/muted text,
info/warning/error/danger, focus/border/disabled를 현재 QPalette에서 해석한다.
새 RGB theme나 swatch 데이터 변환은 없다. 높이는 font metric과 함께 쓰는 최소값이다.

`app/ui/inspector_components.py`의 작은 공통 grammar:

- InspectorSection: 별도 disclosure 버튼, title, word-wrapped read-only summary,
  info/warning/error badge와 body. feature enable checkbox는 caller의 기존 editor다.
- InspectorViewState: `(kind, selection ID, section ID)`별 세션 dict.
  기본 펼침, 선택 A→B→A 복원. Project JSON/Undo/revision/QSettings에 기록하지 않는다.
- InspectorRow/NumericRow/ComboRow: 기존 editor를 그대로 감싸며 label/buddy,
  suffix, tooltip, disabled reason, local validation과 좁은 폭을 지원한다.
- InspectorWarning: severity/message/accessible description을 공통화한다.
- InspectorForm: pilot row collection이며 기존 labelForField 호출도 지원한다.

별도 ToggleSection/ColorRow/EmptyState abstraction은 필요하지 않아 만들지 않았다.
공통 원칙은 짧은 `UI_UX_PRINCIPLES.md`에 반영했다.

## 4. Trail & Sub-emitter Pilot Migration

`particle_properties_panel.py`의 두 section만 migration했다. 기존 배치 순서는 그대로다.
Trail OFF는 Duration/Sample Every/Opacity row를 숨기되 값과 enable 입구는 보존한다.
ON summary는 `duration f · every interval f · opacity`이고 KO 문구도 제공한다.
Sub-emitter는 Birth/Death 입구를 유지하고 OFF target 상세를 숨긴다.
활성 summary는 현재 target 표시 이름으로 `Birth → … · Death → …`를 만든다.
Target 데이터는 기존 stable ID이며 rename/delete/Undo 구현을 바꾸지 않았다.

기존 bounded validation과 거부 복원, editor 신호, draft_changed와 Undo command는 유지했다.
안전 한계 정보는 info, 설정 거부는 error로 local status에 표시한다.
접어도 header summary와 badge/상세 tooltip은 남는다. 중요한 오류를 statusbar로 옮기지 않았다.

## 5. Tests / Layout Evidence

새 `tests/test_inspector_components.py`: **29 passed in 4.32s**.
기존 Trail/Sub-emitter UI, responsive, numeric commit, Ctrl-wheel과 함께
focused **115 passed in 12.47s** (`C:\Dev\pem_ux1_focused_verified`).
model/Undo/dirty/revision snapshot, feature/disclosure 독립, OFF 보존,
요약 갱신, collapsed warning, accepted Undo1 + redo, invalid Undo0,
선택 왕복과 wrapper editor identity를 검증했다.

EN/KO × 280/320/360px × font100/125/150%의 18조건에서 두 pilot을 검사했다.
Malgun Gothic 실제 glyph를 사용했지만 **synthetic offscreen**이다.
header/summary/badge 가로 bounds, summary 줄바꿈 높이, badge overlap,
editor bounds, Space toggle/Tab body 도달을 검사했다.

기존 `tools/audit_editor_ux.py`를 변경 없이 재사용: 36 matrix rows / 14 panels.
Before `C:\Dev\pem_editor_ux_20261002_evidence\inventory.json`,
after `C:\Dev\pem_ux1_after_verified\inventory.json`. 모든 matrix 가로 bounds flag0.
320px 전체 Particle content height 비교(100 / 125 / 150% 순서):

| 조건 | Before | After |
|---|---|---|
| EN Linear/OFF | 6478 / 7516 / 8504 | 6235 / 7233 / 8181 |
| KO Linear/OFF | 6488 / 7484 / 8632 | 6245 / 7201 / 8309 |
| EN Helix/ON | 7785 / 9067 / 10267 | 7841 / 9095 / 10347 |
| KO Helix/ON | 7795 / 8995 / 10371 | 7851 / 9063 / 10451 |

OFF visible controls136→133、ON158→160(disclosure2개 추가).
ON은 header/summary가 추가되어 높이가 늘었다. 높이 감소만으로 UX 성공을 주장하지 않는다.
전체 property wall/IA는 UX-2 범위로 남긴다.
합성 pilot 280px/13pt expanded/collapsed PNG는 `C:\Dev\pem_ux1_pilot_visuals`에
생성했으며 Trail expanded와 Sub-emitter collapsed를 직접 이미지 검사했다.
사용자 asset/project를 열거나 변경하지 않았다.

## 6. Regression / Semantics

최종 full pytest: **1761 passed in 110.20s (0:01:50)**,
`--basetemp=C:\Dev\pem_ux1_final_verified`. 첫 final run의 추가 pending-text 검사 실패는
Qt가 마우스 이동으로 먼저 기존 focus-out commit을 수행하는 경계를 확인한 뒤,
view API와 정상 numeric commit을 분리하여 검증했다.

Disclosure API는 미확정 숫자가 있는 body를 숨기지 않고 안내하며,
입력을 강제 확정/폐기하지 않는다. 기존 mouse/Tab focus-out이 먼저 입력을 확정하면
그 accepted numeric edit의 Undo1은 유지한다. 이는 disclosure command가 아니다.
기존 numeric 정책을 바꾸거나 focus event를 전역 가로채지 않았다.
확정된 입력 상태의 disclosure는 model/Undo/dirty/revision mutation0이다.

compileall(app/tests/tools), git diff --check: exit0.
`python -m app.main --version`: **Pixel Effect Maker v0.0.25**,
`app/models/project.py`: **FORMAT_VERSION = 22**.
직접 `--check`, 지정 Python으로 `run_app.bat --check`: 각각 exit0.
두 check에서 sandbox 밖 AppData log 경로 PermissionError / logging_unavailable가
출력됐다. 이를 정상 로깅 검증으로 주장하지 않으며 권한/로그 경로를 수정하지 않았다.

Model/Renderer/schema/save/serialization/Auto-Key/Timeline/Canvas/Gizmo/Resource
production 변경0. QML/Qt Quick/QQuickWidget, 신규 Effect 기능, Contact 구현0.

## 7. Git / Native Manual Boundary

UX-1 tracked 변경: `app/ui/layout_metrics.py`, `app/ui/particle_properties_panel.py`,
`docs/UI_UX_PRINCIPLES.md`.
새 파일: `app/ui/inspector_components.py`, `tests/test_inspector_components.py`,
이 `docs/UX1_INSPECTOR_FOUNDATION.md`.
모두 **unstaged/uncommitted**, 최종 staged0, main ahead45, HEAD는 위 Audit checkpoint다.
Tag/Push/Build/PyInstaller/ZIP을 수행하지 않았다.

보호 파일 `테스트소스.png`는 untracked 상태 그대로이며 SHA256
**8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564** 일치.
수정/삭제/rename/stage하지 않았다.

Windows native GUI manual: **수행하지 않음**.
실제 Windows DPI/theme/IME/mouse/키보드 감각은 offscreen 검사와 구별하며
추후 native QA가 필요하다. 전체 Particle category migration은 이번 범위가 아니다.
