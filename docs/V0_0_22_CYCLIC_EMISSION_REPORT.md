# v0.0.22 — Deterministic # Pixel Effect Maker v0.0.23
# Multi-point Lifetime Foundation
# Scale / Opacity / Color Lifetime Knots
# No Full Graph Editor

프로젝트:

```text
C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker
```

---

# 0. Roadmap Alignment

이번 작업은 기존 Effect Capability 계획과 재감사 결과를 이어가는 작업이다.

이미 완료:

```text
Scale over Lifetime
Color over Lifetime
Particle Opacity Start/End
Additive Blend
Gravity
Analytic Drag
Deterministic Smooth Noise
Deterministic Cyclic Steady Emission
```

현재 반복적으로 남은 Lifetime gap:

```text
Scale:
0 → 1 → 0

Opacity:
0 → 1 → 0

Color:
White → Yellow → Red

Mid-life peak
Pulse
Flash
Bell-shaped fade
Multi-stage color
Grow → shrink
```

현재 Start / End + 단일 Easing만으로는 위 형태를 하나의 Particle normalized lifetime에서 직접 표현할 수 없다.

이번 버전은 이 gap을 해결한다.

---

# 이번 v0.0.23에서 구현

```text
Multi-point Scale over Lifetime

Multi-point Opacity over Lifetime

Multi-point RGB Color over Lifetime

Per-segment Easing
```

---

# 이번 버전에서 구현하지 않음

```text
Free-form Graph Editor
Bezier handles
Custom easing curves
Tangent editing
Curve canvas
Animation timeline integration
Auto-Key lifetime points
Random curve variations
Per-axis Scale lifetime curves
HSV/HSL interpolation
Alpha-in-Color points
Gradient editor
Trail
Ribbon
Sub-emitter
Force Stack
New Spawn Shape
Rate API
```

---

# ============================================================
# PART A
# 실제 Baseline 재수집
# ============================================================

최근 보고 기준:

```text
HEAD:
d91f9582984b3d63904c0666d5d76c700bf40b5d

HEAD 내용:
Post-v0.0.21 Capability Recheck checkpoint

Current Working Tree:
v0.0.22 Deterministic Cyclic Steady Emission
unstaged / uncommitted

Version:
Pixel Effect Maker v0.0.22

FORMAT_VERSION:
19

Full pytest:
1410 passed
0 failed

Focused cyclic:
75 passed

Staged:
0
```

하지만 반드시 실제 상태를 다시 수집한다.

```bat
cd /d "C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker"

git rev-parse HEAD
git status --short
git status -sb
git diff --stat
git diff --check
git diff --cached --name-only

C:\Dev\pixel_effect_test_venv\Scripts\python.exe -m pytest -q --basetemp=C:\Dev\pixel_effect_maker_pytest_temp

C:\Dev\pixel_effect_test_venv\Scripts\python.exe -m compileall app tests tools

C:\Dev\pixel_effect_test_venv\Scripts\python.exe -m app.main --version
C:\Dev\pixel_effect_test_venv\Scripts\python.exe -m app.main --check

run_app.bat --check
```

실제 결과를 baseline으로 기록한다.

---

# 보호 대상

```text
테스트소스.png
```

기준 SHA-256:

```text
8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564
```

계속:

```text
수정 금지
삭제 금지
rename 금지
stage 금지
```

---

# ============================================================
# PART B
# v0.0.22 Local Checkpoint
# ============================================================

사용자가 다음 단계 진행을 요청했으므로 v0.0.22를 checkpoint 대상으로 본다.

다음이 모두 정상이어야 한다.

```text
pytest failures = 0

Pixel Effect Maker v0.0.22

FORMAT_VERSION = 19

ONE_SHOT legacy exact

Cyclic prewarm 정상

F(t+P)=F(t)

Direct Seek deterministic

Preview / Full / Generated / PNG parity

Active-copy safety 정상

staged contamination 없음

보호 PNG unchanged
```

문제가 있으면 v0.0.23으로 넘어가지 말고 먼저 보고한다.

---

## Explicit staging only

금지:

```text
git add -A
```

v0.0.22 승인 파일만 명시적으로 stage.

제외:

```text
테스트소스.png
사용자 project
C:\Dev evidence
build/
dist/
exe
zip
cache
logs
temp
backup
pytest temp
```

---

## 권장 Commit

```text
Add deterministic cyclic emission
```

실제 commit 후 반드시:

```text
actual full commit hash

git status --short

git status -sb

git diff --cached --name-only
```

확인.

기대:

```text
staged 0
```

금지:

```text
Tag
Push
Build
PyInstaller
ZIP
Release
```

---

# ============================================================
# PART C
# 구현 전 Lifetime Architecture Audit
# ============================================================

새 point model부터 만들지 않는다.

먼저 현재 Lifetime 전체를 다시 추적한다.

최소 확인:

```text
LifetimeScalarModulation

LifetimeColorModulation

Scale over Lifetime

Color over Lifetime

Particle opacity_start

Particle opacity_end

Particle opacity easing

normalized_lifetime_age()

eased_lifetime_amount()

Scale evaluator

Color evaluator

Opacity evaluator

Inspector reconstruction

Undo

Serialization

FORMAT migration

Preview

Export
```

---

# 반드시 답할 질문

```text
1.
Scale lifetime persistent 구조는 정확히 무엇인가?

2.
Color lifetime persistent 구조는 정확히 무엇인가?

3.
Opacity는 왜 별도 fields인가?

4.
Scale / Color / Alpha가 사용하는 easing enum은 완전히 같은가?

5.
Scale과 Color가 disabled일 때 identity는 무엇인가?

6.
Opacity neutral/default는 무엇인가?

7.
각 evaluator가 normalized age를 어디서 계산하는가?

8.
Color interpolation은 여전히 encoded sRGB channel arithmetic인가?

9.
Scale result는 base X/Y scale에 어떻게 합성되는가?

10.
Opacity는 source alpha / layer opacity와 어떤 순서로 합성되는가?

11.
Cyclic prewarm copy도 동일 normalized age evaluator를 타는가?

12.
Inspector refresh에서 settings reconstruction 경로는 어디인가?

13.
기존 Alpha Easing integrity fix가 어디에서 보장되는가?
```

실제 코드 근거를 보고에 남긴다.

---

# ============================================================
# PART D
# 새 Version / Schema
# ============================================================

Version:

```text
Pixel Effect Maker v0.0.23
```

Persistent representation이 바뀌므로 기본적으로:

```text
FORMAT_VERSION
19 → 20
```

---

# Migration 원칙

FORMAT <=19 project:

```text
기존 Start
기존 End
기존 Easing
```

을 정확히:

```text
Point 0:
time = 0.0
value = old start
easing_to_next = old easing

Point 1:
time = 1.0
value = old end
```

로 materialize.

---

# Color도 동일

```text
time 0:
old start_rgb

time 1:
old end_rgb

segment easing:
old color easing
```

---

# Opacity도 동일

```text
time 0:
old opacity_start

time 1:
old opacity_end

segment easing:
old Alpha easing
```

---

# 중요

Project를 load하는 것만으로 원본 파일 rewrite 금지.

---

# ============================================================
# PART E
# Single Canonical Representation
# ============================================================

새 FORMAT 20에서:

```text
legacy start/end fields
+
new points
```

를 둘 다 writable source-of-truth로 유지하지 않는다.

---

# 목표

새 format에는 가능한 한:

```text
points
```

가 canonical representation.

Legacy Start/End fields는:

```text
FORMAT <=19 load compatibility
```

용으로만 사용.

---

# 단

현재 architecture상 즉시 제거하면 unrelated API를 대규모로 깨뜨리는 경우:

```text
compatibility property
read-only adapter
```

는 허용.

하지만 서로 독립적으로 수정 가능한 duplicated state는 금지.

---

# 완료 보고에 반드시:

```text
새 canonical representation

legacy loader

compatibility adapter 여부
```

기록.

---

# ============================================================
# PART F
# Lifetime Point Model
# ============================================================

이번 버전은 arbitrary graph system을 만들지 않는다.

두 종류만 필요.

---

## Scalar point

개념:

```text
LifetimeScalarPoint

time: float
value: float
easing_to_next: Easing
```

---

## Color point

```text
LifetimeColorPoint

time: float
rgb: RGB3
easing_to_next: Easing
```

---

# 실제 naming은 현재 codebase convention에 맞춘다.

---

# ============================================================
# PART G
# Point Count Contract
# ============================================================

각 channel:

```text
minimum:
2 points

maximum:
8 points
```

권장.

---

# 만약 현재 project validation convention상 다른 작은 upper bound가 더 적절하면 변경 가능.

단 완료 보고에 근거 명시.

---

# 이유

```text
Start / End compatibility

Mid-point 표현 가능

UI bounded

Serialization bounded

Hot path bounded

Graph editor 없이 관리 가능
```

---

# 8개를 넘어서는 자유로운 spline editor는 이번 범위 아님.

---

# ============================================================
# PART H
# Endpoint Contract
# ============================================================

모든 curve는 반드시:

```text
first.time = 0.0

last.time = 1.0
```

을 가진다.

---

# Endpoints는 제거 불가.

---

# Endpoint time은 수정 불가.

값과 easing은 수정 가능.

---

# Internal point:

```text
0 < time < 1
```

---

# 모든 time은:

```text
strictly increasing
unique
finite
```

이어야 한다.

---

# duplicate time 금지.

---

# ============================================================
# PART I
# Per-Segment Easing
# ============================================================

각 point의:

```text
easing_to_next
```

가 현재 point에서 다음 point까지의 segment easing.

---

# 예

```text
P0 time0 value0 easing=Ease Out

P1 time0.3 value1 easing=Linear

P2 time1 value0
```

의미:

```text
0.0 → 0.3:
Ease Out

0.3 → 1.0:
Linear
```

---

# 마지막 point의 easing은:

```text
not used
```

UI에서는 disabled/hidden 처리 가능.

Serialization은 deterministic default를 가질 수 있다.

---

# 기존 2-point curve

한 segment뿐이므로 기존 단일 Easing과 exact 동일.

---

# ============================================================
# PART J
# Evaluation Contract
# ============================================================

normalized lifetime:

```text
t ∈ [0,1]
```

---

# t == point.time

해당 point value exact.

---

# segment 찾기

```text
Pi.time <= t <= P(i+1).time
```

---

# local segment progress

```text
u =
(t - Pi.time)
/
(P(i+1).time - Pi.time)
```

---

# easing

```text
e =
apply_easing(Pi.easing_to_next, u)
```

---

# scalar

```text
value =
lerp(Pi.value, P(i+1).value, e)
```

---

# Color

각 RGB channel 개별 보간.

현재 v0.0.22까지의 color convention 유지.

새 색공간 도입 금지.

---

# ============================================================
# PART K
# Exact Endpoint / Floating Robustness
# ============================================================

반드시:

```text
t <= 0
→ first value

t >= 1
→ last value
```

---

# point time equality에서 부동소수 tolerance 때문에 이웃 segment의 다른 값을 만들면 안 된다.

---

# points 최대 8이므로:

```text
simple bounded linear scan
```

으로 충분.

거대한 curve index/cache framework 금지.

---

# ============================================================
# PART L
# Scale Multi-point
# ============================================================

기존 의미 유지.

Scale curve result는:

```text
uniform scalar multiplier
```

이다.

---

# Base particle:

```text
base_scale_x
base_scale_y
```

가 있을 때:

```text
final_x =
base_x × lifetime_scale

final_y =
base_y × lifetime_scale
```

---

# Non-uniform base ratio 유지.

---

# 예

```text
0.0 → 0.0
0.35 → 1.25
1.0 → 0.0
```

으로 Hit Spark:

```text
spawn
→ pop
→ shrink
```

가능.

---

# Scale curve는 Position/Layer Scale과 별개.

---

# ============================================================
# PART M
# Opacity Multi-point
# ============================================================

기존 Particle Alpha 의미를 보존.

---

# 예:

```text
0.0 → 0.0
0.15 → 1.0
0.75 → 1.0
1.0 → 0.0
```

으로:

```text
fade in
→ hold
→ fade out
```

가능.

---

# 매우 중요

Opacity points는:

```text
RGB Color Lifetime
```

과 완전히 분리.

---

# 다음을 건드리지 않는다.

```text
source RGB

Color Lifetime RGB

Layer opacity

Parent opacity
```

---

# 기존:

```text
source alpha
×
particle lifetime opacity
×
layer opacity
...
```

합성 의미 유지.

---

# Alpha Easing integrity bug를 절대 재도입하지 않는다.

---

# ============================================================
# PART N
# Color Multi-point
# ============================================================

RGB-only.

---

# 예

```text
0.0  White
0.35 Yellow
1.0  Red
```

---

# Alpha 저장 금지.

---

# Color picker에서 Alpha control 의미 없음.

QColor를 사용하더라도 RGB만 읽고 저장.

---

# 기존 의미:

```text
source artwork RGB
×
lifetime RGB tint
```

유지.

---

# 검은 source pixel은 여전히 tint로 밝아지지 않는다.

이번 버전에서 Recolor mode를 만들지 않는다.

---

# ============================================================
# PART O
# Disabled Identity
# ============================================================

Scale OFF:

```text
v0.0.22 exact
```

---

# Color OFF:

```text
v0.0.22 exact
```

---

# Opacity는 기존 semantics를 그대로 따른다.

Neutral opacity curve가 필요하다면:

```text
1 → 1
```

이 identity.

---

# FORMAT19 legacy project는 migration 후 exact render.

---

# ============================================================
# PART P
# Cyclic Emission Interaction
# ============================================================

매우 중요.

v0.0.22 Cyclic copy:

```text
copy actual age
```

에서 normalized lifetime을 계산.

---

# previous-cycle prewarm copy가:

```text
age = 12
```

라면 해당:

```text
Scale curve
Opacity curve
Color curve
```

의 age 12 normalized position을 사용.

---

# Gate frame이라고 lifetime curve를 time0에서 시작하면 실패.

---

# Periodicity

같은 canonical slot:

```text
Cycle k age a

Cycle k+1 age a
```

는 동일 point evaluation.

따라서 static/local:

```text
F(t+P)=F(t)
```

계약 유지.

---

# ============================================================
# PART Q
# UI 방향
# ============================================================

이번 버전에서 자유 그래프 캔버스를 만들지 않는다.

---

# 기존:

```text
Over Lifetime
```

영역을 유지.

각 channel을 compact point editor로 확장.

---

# 권장:

```text
Scale over Lifetime
────────────────────
☑ Enabled

Time     Scale     Easing →
0%       0.00      Ease Out
35%      1.25      Linear
100%     0.00      —

[ + Point ] [ - Point ]
```

---

# Opacity

```text
Opacity over Lifetime
────────────────────

Time     Opacity   Easing →
0%       0.00      Ease Out
15%      1.00      Linear
75%      1.00      Ease In
100%     0.00      —
```

---

# Color

```text
Color over Lifetime
────────────────────
☑ Enabled

Time     Color          Easing →
0%       ■ #FFFFFF      Linear
35%      ■ #FFD020      Ease In
100%     ■ #FF3000      —
```

---

# ============================================================
# PART R
# UI Time Representation
# ============================================================

Storage:

```text
normalized 0.0..1.0
```

---

# UI는 사용자 친화적으로:

```text
0..100 %
```

권장.

---

# precision

최소:

```text
0.1%
```

또는 현재 numeric convention에 맞는 충분한 precision.

---

# Endpoint:

```text
0%
100%
```

time edit disabled.

---

# ============================================================
# PART S
# Add Point
# ============================================================

Add Point는 명시적인 사용자 action.

---

# 기본 위치

권장:

```text
현재 가장 큰 time gap의 midpoint
```

---

# 새 value

해당 time의 현재 curve evaluated value를 초기값으로 사용.

Color도 evaluated RGB.

---

# Easing

합리적인 deterministic default:

```text
Linear
```

또는 기존 containing segment easing.

---

# 어느 쪽을 선택했는지 문서화.

---

# 중요한 점

Add Point가 curve shape를 완전히 보존한다고 과장하지 않는다.

Point 추가 자체가 editing action이다.

---

# Undo:

```text
Add Point
→ 1 command
```

---

# ============================================================
# PART T
# Remove Point
# ============================================================

Internal point만 삭제 가능.

---

# Endpoint 삭제 금지.

---

# Remove:

```text
1 user action
→ Undo 1
```

---

# Point 선택이 없다면 disabled.

---

# ============================================================
# PART U
# Point Time Editing
# ============================================================

Internal point time만 edit.

---

# 허용 범위:

```text
previous.time < new.time < next.time
```

---

# 이번 버전에서는 point를 다른 point 너머로 drag/reorder하는 기능 추가 금지.

---

# Invalid:

```text
duplicate

cross neighbor

outside 0..1

NaN/Inf
```

명시적으로 reject/revert.

---

# silent sort로 사용자 point identity를 바꾸지 않는다.

---

# ============================================================
# PART V
# Point Value Editing
# ============================================================

Scale range:

기존 Scale over Lifetime range를 감사해 그대로 사용.

---

# Opacity:

기존 range 유지.

예상:

```text
0..1
```

실제 model 기준으로 확정.

---

# Color:

RGB picker.

Alpha 저장하지 않음.

---

# ============================================================
# PART W
# Inspector Refresh Integrity
# ============================================================

다음만으로:

```text
Inspector open
refresh
selection change
timeline scrub
Undo/Redo refresh
project load
localization change
```

다음 모두 0:

```text
curve mutation
point reorder
Dirty
Undo push
revision mutation
```

---

# Sentinel

Layer A Scale:

```text
0.0  0.2 Ease Out
0.37 1.4 Ease In
1.0  0.1
```

Layer A Opacity:

```text
0.0 0
0.18 1
0.77 0.65
1.0 0
```

Layer A Color:

```text
0.0  #F1A203
0.42 #17C9E4
1.0  #9922CC
```

다른 Layer 선택 후 돌아와도 exact.

---

# ============================================================
# PART X
# Undo Contract
# ============================================================

각각 user action 1개 = Undo 1개:

```text
Add Point

Remove Point

Time edit

Scalar value edit

Color edit

Segment easing edit

Scale Enabled

Color Enabled
```

---

# No-op:

```text
Undo 0
Dirty 0
revision 0
```

---

# Color dialog cancel:

```text
mutation 0
Undo 0
```

---

# Refresh:

```text
Undo 0
```

---

# ============================================================
# PART Y
# Timeline / Auto-Key
# ============================================================

Lifetime point editor는 Composition Timeline keyframe editor가 아니다.

---

# 이번 버전에서:

```text
point time
point value
point easing
```

을 Composition Timeline track으로 만들지 않는다.

---

# Auto-Key:

```text
Lifetime Point edit
→ timeline keyframe 생성 0
```

---

# ============================================================
# PART Z
# Serialization
# ============================================================

FORMAT20 new project:

```text
Scale curve points

Color curve points

Opacity curve points
```

round-trip exact.

---

# 반드시 검증:

```text
point count

time

value

RGB

segment easing

enabled state
```

---

# invalid payload:

```text
<2 points

>max points

missing endpoint

duplicate time

unsorted

NaN/Inf

invalid easing

bad RGB

bad scalar range
```

프로젝트 기존 validation policy에 따라 deterministic reject.

---

# silent repair로 다른 curve를 만들지 않는다.

---

# ============================================================
# PART AA
# Legacy Exact Compatibility
# ============================================================

FORMAT19 fixture:

```text
Scale Start/End/Easing

Color Start/End/Easing

Opacity Start/End/Easing
```

를 load.

---

# 자동 변환된 2-point curve로:

```text
v0.0.22 pixels
==
v0.0.23 pixels
```

exact 또는 기존 compositor rounding 범위에서 동일 stage exact.

---

# 특히:

```text
Linear
Ease In
Ease Out
Ease In/Out
```

모두 비교.

---

# 기존 Alpha Easing sentinel 반드시 포함.

---

# ============================================================
# PART AB
# Hot Path / Performance
# ============================================================

Particle마다 curve evaluation.

Points 최대 8.

---

# 금지:

```text
QColor allocation per particle

dict construction

deepcopy

sorting every frame

serialization

filesystem

dynamic spline construction
```

---

# Points는 model validation 시 정렬/검증 완료.

렌더 hot path는 read-only.

---

# bounded linear segment scan 허용.

---

# 필요하면 points tuple/list를 그대로 사용.

매 sample마다 새 collection 생성 금지.

---

# ============================================================
# PART AC
# Performance Benchmark
# ============================================================

동일 fixture:

```text
100
500
1000
5000
```

particles.

---

# 비교:

```text
Legacy-equivalent 2-point

3-point Scale

4-point Opacity

3-point Color

Scale + Opacity + Color all multi-point

Full stack:
Cyclic
+ Gravity
+ Drag
+ Noise
+ Scale Curve
+ Opacity Curve
+ Color Curve
+ Additive
```

---

# Cyclic에서는:

```text
canonical count
active copy count
```

도 같이 기록.

---

# 2-point legacy path에 큰 performance regression을 만들지 않는다.

---

# ============================================================
# PART AD
# Representative Effects
# ============================================================

이번 기능의 실제 제작 가치 검증.

---

## 1. Hit Spark

```text
Scale:
0.0 → 0.2
0.15 → 1.3
1.0 → 0

Opacity:
0 → 1 → 0

Color:
White → Yellow → Orange

Additive
Gravity
Drag
```

기대:

```text
spawn flash
→ 빠른 peak
→ shrink/fade
```

---

## 2. Explosion

```text
Scale:
small → large → smaller

Color:
White → Yellow → Red

Opacity:
0 → 1 → 0
```

---

## 3. Smoke

```text
Scale:
small → large → larger

Opacity:
0 → 1 → 0
```

bell-shaped visibility.

---

## 4. Magic Wisp

```text
Color:
White → Cyan → Blue

Opacity:
0 → 1 → 0

Scale:
small → large → small
```

---

## 5. Sword Slash

```text
Opacity:
0 → 1 → 0

Scale:
small → large → small
```

---

## 6. Cyclic Fire

```text
Cyclic Steady
+
Color multi-point
+
Opacity multi-point
+
Scale multi-point
```

Periodicity 유지 확인.

---

# ============================================================
# PART AE
# Core Evaluator Tests
# ============================================================

권장 신규:

```text
tests/test_lifetime_multi_point.py

tests/test_lifetime_multi_point_serialization.py
```

필요하면 UI test 별도.

---

# Scalar evaluator

```text
test_scalar_curve_two_point_matches_legacy_linear

test_scalar_curve_two_point_matches_legacy_ease_in

test_scalar_curve_two_point_matches_legacy_ease_out

test_scalar_curve_two_point_matches_legacy_ease_in_out

test_scalar_curve_exact_internal_point

test_scalar_curve_three_point_peak

test_scalar_curve_each_segment_uses_own_easing
```

---

# Color

```text
test_color_curve_two_point_matches_legacy

test_color_curve_exact_internal_rgb

test_color_curve_three_point_white_yellow_red

test_color_curve_does_not_modify_alpha
```

---

# Opacity

```text
test_opacity_curve_two_point_matches_legacy

test_opacity_curve_fade_in_hold_fade_out

test_opacity_curve_does_not_modify_color

test_opacity_curve_preserves_layer_opacity_contract
```

---

# Validation

```text
test_curve_requires_two_points

test_curve_requires_zero_endpoint

test_curve_requires_one_endpoint

test_curve_times_strictly_increasing

test_curve_duplicate_time_rejected

test_curve_too_many_points_rejected

test_curve_nan_inf_rejected
```

---

# ============================================================
# PART AF
# UI Tests
# ============================================================

```text
test_scale_point_editor_add_remove

test_opacity_point_editor_add_remove

test_color_point_editor_add_remove

test_endpoint_times_locked

test_internal_time_edit

test_duplicate_time_rejected

test_segment_easing_edit

test_last_point_easing_disabled

test_color_picker_cancel_no_mutation

test_point_refresh_no_mutation

test_point_selection_change_preserves_curve
```

---

# ============================================================
# PART AG
# Undo Tests
# ============================================================

```text
test_add_point_one_undo

test_remove_point_one_undo

test_point_time_edit_one_undo

test_point_value_edit_one_undo

test_point_color_edit_one_undo

test_point_easing_edit_one_undo

test_point_noop_no_undo

test_point_refresh_no_undo
```

---

# ============================================================
# PART AH
# Migration Tests
# ============================================================

```text
test_format19_scale_migrates_to_two_points

test_format19_color_migrates_to_two_points

test_format19_opacity_migrates_to_two_points

test_format19_all_easings_exact

test_old_project_not_rewritten_on_load

test_format20_curve_round_trip
```

---

# ============================================================
# PART AI
# Cyclic Tests
# ============================================================

```text
test_cyclic_prewarm_uses_multi_point_scale

test_cyclic_prewarm_uses_multi_point_opacity

test_cyclic_prewarm_uses_multi_point_color

test_cyclic_multi_point_t_equals_t_plus_period

test_cyclic_multi_point_additive_periodic
```

---

# ============================================================
# PART AJ
# Existing Motion / Blend Regression
# ============================================================

반드시 유지:

```text
Gravity

Drag

Noise

Linear

Orbit

Helix

Normal

Additive

Cyclic One Shot

Cyclic Steady

Scale base ratio

Color RGB-only

Alpha isolation

Playback Speed

Seed
```

---

# ============================================================
# PART AK
# Transform Regression
# ============================================================

보존:

```text
Parenting

parent_offset

Keep World

System Transform

Surface Transform

2.5D

Rotation Revolution

Overscan

strict clip
```

---

# ============================================================
# PART AL
# Preview / Export
# ============================================================

같은 frame:

```text
Current Frame

Full Render

Generated Output

PNG Decode
```

curve 결과 exact.

---

# Cyclic prewarm frame도 포함.

---

# Output dimensions 변경 없음.

---

# ============================================================
# PART AM
# Documentation
# ============================================================

업데이트:

```text
README.md

CHANGELOG.md

docs/MANUAL_TEST_CHECKLIST.md

docs/EFFECT_AUTHORING_CAPABILITY_AUDIT.md
```

새 보고서 권장:

```text
docs/V0_0_23_MULTI_POINT_LIFETIME_REPORT.md
```

---

# Capability Audit

좁은:

```text
Multi-point Lifetime Scale
Multi-point Lifetime Opacity
Multi-point Lifetime RGB Color
```

가 end-to-end 완성되면 COMPLETE 판정 가능.

---

# 그러나 전체 Curve System은:

```text
PARTIAL
```

로 유지 가능.

아직 없음:

```text
Bezier handles
Graph editor
custom tangents
per-axis Scale curves
HSV gradient
randomized curves
Timeline animation of curve points
```

---

# ============================================================
# PART AN
# Manual Windows GUI QA Checklist
# ============================================================

Codex는 Windows native GUI manual QA를 수행했다고 주장하지 않는다.

체크리스트만 작성.

---

# 1. Scale peak

```text
0 → 1.2 → 0
```

실제로 pop 후 shrink되는지.

---

# 2. Opacity bell

```text
0 → 1 → 0
```

fade in/out 자연스러운지.

---

# 3. Color 3-stop

```text
White → Yellow → Red
```

중간 색이 명확히 지나가는지.

---

# 4. Segment easing

첫 segment Ease Out,
둘째 Linear 등 차이가 보이는지.

---

# 5. Add Point

point가 예상 위치/value로 생성되는지.

---

# 6. Remove Point

internal만 제거 가능한지.

---

# 7. Endpoint

0%/100% time이 수정/삭제되지 않는지.

---

# 8. Invalid time

중복/crossing 입력이 명확히 거부되는지.

---

# 9. Undo / Redo

Add/Remove/Time/Value/Color/Easing 각각 exact.

---

# 10. Selection

A/B layer 서로 다른 curves.

A→B→A exact.

---

# 11. Save / Reload

모든 point exact.

---

# 12. Legacy 2-point

기존 Effect가 시각적으로 동일한지.

---

# 13. Cyclic Fire

prewarm particle이 중간 curve 상태로 시작하는지.

---

# 14. Full Stack

```text
Cyclic
Gravity
Drag
Noise
Scale multi-point
Opacity multi-point
Color multi-point
Additive
```

---

# 15. Export

Preview/PNG 같은 frame 결과 동일.

---

# ============================================================
# PART AO
# Final Verification
# ============================================================

```bat
C:\Dev\pixel_effect_test_venv\Scripts\python.exe -m pytest -q --basetemp=C:\Dev\pixel_effect_maker_pytest_temp

C:\Dev\pixel_effect_test_venv\Scripts\python.exe -m compileall app tests tools

C:\Dev\pixel_effect_test_venv\Scripts\python.exe -m app.main --version

C:\Dev\pixel_effect_test_venv\Scripts\python.exe -m app.main --check

run_app.bat --check

git diff --check

git status --short
git status -sb
git diff --cached --name-only
```

기대:

```text
0 failures

Pixel Effect Maker v0.0.23

FORMAT_VERSION = 20

staged 0
```

---

# ============================================================
# PART AP
# Git 종료
# ============================================================

v0.0.22까지만 Local Commit.

---

# v0.0.23 변경은:

```text
unstaged
uncommitted
```

으로 종료.

---

# 즉:

```text
v0.0.23 staged:
0

v0.0.23 commit:
0

Tag:
0

Push:
0

Build:
0

PyInstaller:
0

ZIP:
0
```

---

# ============================================================
# 완료 보고 필수 항목
# ============================================================

```text
1. 실제 작업 시작 HEAD
2. 시작 Version
3. 시작 FORMAT_VERSION
4. 시작 pytest

[v0.0.22 Checkpoint]

5. Cyclic commit hash
6. checkpoint 포함 파일
7. 제외 파일
8. checkpoint 후 Git

[Lifetime Architecture]

9. 기존 Scale model
10. 기존 Color model
11. 기존 Opacity model
12. normalized age
13. easing helper
14. Scale evaluator
15. Color evaluator
16. Opacity evaluator
17. Alpha Easing integrity path
18. Inspector reconstruction
19. serialization

[New Model]

20. Version
21. FORMAT_VERSION
22. scalar point type
23. color point type
24. canonical representation
25. legacy adapter 여부
26. min points
27. max points
28. endpoint rules
29. internal time rules
30. easing ownership

[Migration]

31. Scale start/end mapping
32. Scale easing mapping
33. Color mapping
34. Opacity mapping
35. old project rewrite 여부
36. legacy render exact

[Evaluator]

37. segment lookup
38. local u
39. easing
40. scalar lerp
41. color lerp
42. endpoint behavior
43. exact internal point
44. floating robustness

[Scale]

45. multi-point semantics
46. base X/Y ratio preservation
47. disabled identity
48. representative peak

[Opacity]

49. multi-point semantics
50. source alpha interaction
51. layer opacity interaction
52. color isolation
53. Alpha Easing migration

[Color]

54. RGB-only
55. interpolation space
56. source tint multiplication
57. alpha isolation
58. disabled identity

[UI]

59. Over Lifetime layout
60. Scale editor
61. Opacity editor
62. Color editor
63. time UI
64. value UI
65. color picker
66. easing per segment
67. Add Point
68. Remove Point
69. endpoint lock
70. invalid time handling
71. KO
72. EN
73. refresh integrity

[Undo]

74. add
75. remove
76. time
77. scalar value
78. color
79. easing
80. no-op
81. picker cancel
82. refresh

[Cyclic]

83. prewarm Scale
84. prewarm Opacity
85. prewarm Color
86. F(t+P)
87. canonical identity
88. copy age

[Motion / Blend]

89. Gravity
90. Drag
91. Noise
92. Linear
93. Orbit
94. Helix
95. Normal
96. Additive
97. full stack

[Serialization]

98. FORMAT19 defaults
99. FORMAT20 roundtrip
100. invalid payload
101. point count validation
102. time validation
103. easing validation
104. RGB validation

[Cache]

105. curve edits render invalidation
106. generated output invalidation
107. spawn cache 영향
108. cyclic canonical slots 영향

[Preview / Export]

109. current
110. full
111. generated
112. PNG
113. parity
114. output dimensions
115. strict clip
116. overscan

[Performance]

117. 2-point legacy
118. 3-point Scale
119. multi-point Opacity
120. multi-point Color
121. all curves
122. cyclic full stack
123. allocation/sorting 여부

[Representative Effects]

124. Hit Spark
125. Explosion
126. Smoke
127. Magic Wisp
128. Sword Slash
129. Cyclic Fire
130. 표현력 개선 평가

[Tests]

131. 신규 files
132. focused count
133. scalar curve
134. color curve
135. opacity curve
136. migration
137. UI
138. Undo
139. cyclic
140. motion/blend
141. transforms
142. export
143. full pytest
144. compileall
145. --version
146. --check
147. run_app.bat
148. git diff --check

[Audit]

149. Multi-point Scale status
150. Multi-point Opacity status
151. Multi-point Color status
152. overall Curve System status
153. 남은 Graph Editor gap
154. 남은 Trail gap
155. 남은 Sub-emitter gap

[Git]

156. 최종 HEAD
157. staged
158. v0.0.23 commit
159. tag/push/build

[Manual]

160. Windows native GUI manual 여부
반드시 "수행하지 않음"

[Final]

161. 기존 2-point render exact 여부
162. 0→1→0 Scale 가능 여부
163. 0→1→0 Opacity 가능 여부
164. 3-stop RGB 가능 여부
165. segment별 easing 가능 여부
166. Alpha/Color 분리 유지 여부
167. cyclic prewarm과 정확히 결합되는지
168. Direct Seek/Export deterministic인지
169. 기존 프로젝트 보존 여부
170. 실제 Effect 표현력 개선 평가
171. 기존 roadmap과 현재 우선순위 일치 여부
172. 다음 추천 기능
```

---

# ============================================================
# 최종 성공 조건
# ============================================================

```text
1.
현재 v0.0.22를 실제 Git/Test 상태에서 재검증한다.

2.
정상일 때만 `Add deterministic cyclic emission` Local Checkpoint를 만든다.

3.
git add -A를 사용하지 않는다.

4.
Version을 v0.0.23으로 올린다.

5.
Persistent schema 변경으로 FORMAT_VERSION을 20으로 올린다.

6.
Multi-point Scale / Opacity / RGB Color를 구현한다.

7.
Full Graph Editor는 구현하지 않는다.

8.
각 curve는 최소2 / 최대8 points의 bounded structure다.

9.
time0과 time1 endpoint는 필수다.

10.
Endpoint time은 수정/삭제 불가다.

11.
Internal times는 unique/strictly increasing이다.

12.
각 segment는 독립 easing을 가진다.

13.
기존 2-point Start/End/Easing은 정확히 2-point curve로 migration된다.

14.
새 format에서 duplicated writable Start/End + Points source-of-truth를 만들지 않는다.

15.
Scale curve는 uniform multiplier 의미를 유지한다.

16.
Base non-uniform X/Y scale ratio를 유지한다.

17.
Opacity는 RGB Color와 완전히 분리한다.

18.
Color points는 RGB-only다.

19.
Color Lifetime은 Alpha를 변경하지 않는다.

20.
Opacity curve는 기존 source/layer alpha composition contract를 유지한다.

21.
Alpha Easing integrity regression을 막는다.

22.
Color interpolation convention을 변경하지 않는다.

23.
0→1→0 Scale을 직접 표현할 수 있다.

24.
0→1→0 Opacity를 직접 표현할 수 있다.

25.
White→Yellow→Red RGB를 직접 표현할 수 있다.

26.
Point Add/Remove/Edit/Easing은 정확한 Undo를 만든다.

27.
No-op/refresh/dialog cancel은 Undo를 만들지 않는다.

28.
Point time crossing/duplicate는 명시적으로 거부한다.

29.
Lifetime point edit은 Auto-Key/Composition Timeline track을 만들지 않는다.

30.
Cyclic prewarm copy는 자신의 actual age로 multi-point curves를 평가한다.

31.
Cyclic F(t+P)=F(t) 계약을 유지한다.

32.
Gravity/Drag/Noise 시간 의미를 변경하지 않는다.

33.
Normal/Additive 의미를 변경하지 않는다.

34.
Parenting/System/Surface/2.5D/Rotation Revolution을 변경하지 않는다.

35.
Seed/spawn/cyclic canonical identity를 변경하지 않는다.

36.
FORMAT19 legacy project는 기존 render를 유지한다.

37.
Project load만으로 파일을 rewrite하지 않는다.

38.
Hot path에서 curve sorting/QColor/deepcopy/filesystem 작업을 하지 않는다.

39.
Preview/Full/Generated/PNG parity를 유지한다.

40.
Overscan/strict clipping을 유지한다.

41.
전체 tests failures = 0.

42.
Codex는 Windows native GUI manual QA를 수행했다고 주장하지 않는다.

43.
v0.0.23 변경은 사용자 GUI 승인 전 Stage/Commit하지 않는다.

44.
Tag / Push / Build / PyInstaller / ZIP을 수행하지 않는다.
```

먼저 현재 `v0.0.22 / FORMAT_VERSION 19 / 1410 passed` Deterministic Cyclic Steady Emission을 실제 상태에서 재검증하고, 정상이라면 `Add deterministic cyclic emission` Local Checkpoint로 고정해줘.

그 다음 `v0.0.23 / FORMAT_VERSION 20`으로 전환하고 **Multi-point Lifetime Foundation**을 구현해줘.

이번 버전은 풀 Graph Editor가 아니다. Scale / Opacity / RGB Color 각각에 normalized lifetime `0..1`의 bounded point list와 segment별 기존 Easing을 제공해서 `0→1→0`, fade-in/out, White→Yellow→Red 같은 중간점 표현을 직접 만들 수 있게 하는 것이 목표다.

기존 FORMAT19의 Start/End/Easing 프로젝트는 정확한 2-point curve로 migration하여 기존 render를 보존해줘.

Color와 Alpha는 계속 완전히 분리하고, Cyclic prewarm copy도 자신의 actual age를 사용해 새로운 lifetime curve를 정확히 평가하게 해줘.

v0.0.23 변경은 사용자 실제 Windows GUI 승인 전 Stage/Commit/Tag/Push/Build하지 마.Cyclic Steady Emission

2026-10-01 · 구현/자동 검증 보고 · Windows native GUI manual **수행하지 않음**.

## 결과와 Git 경계

- 시작 HEAD `af9be4c948f3d3a09700478dc00dd2102196c2ab`, v0.0.21 / format18.
- 실제 baseline: **1335 passed in 82.37s**. production diff0, staged0, audit 파일3개만 변경.
  compileall app/tests/tools, app.main --version/--check, run_app.bat --check 통과.
  `tools/recheck_effect_capabilities.py`를 `C:\Dev\pem_v22_baseline_recheck_20261001`에 재실행.
- Audit checkpoint: **`d91f9582984b3d63904c0666d5d76c700bf40b5d`**,
  `Reassess effect authoring capabilities`. 기존 audit 수정, Post-v21 보고서, recheck script
  3개만 explicit staging/commit. checkpoint 직후 main ahead40, staged0, 보호PNG만 untracked.
- 그 이후 구현은 **v0.0.22 / FORMAT_VERSION19**, 전부 unstaged/uncommitted.
  v22 commit/tag/push/build/PyInstaller/ZIP/release 없음. `git add -A` 사용하지 않음.
- 보호 `테스트소스.png`: 수정/삭제/rename/stage하지 않음.
  시작/최종 SHA256 `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`.

## 실제 architecture와 정확한 시간 의미

`ParticleEmitterSettings`는 string-token convention을 따른다. 새 fields는 dataclass 맨 뒤에
추가하여 기존 positional arguments 순서도 유지했다. `emission_cycle_mode`는
`one_shot`/`cyclic_steady`, 기본 one_shot. `emission_period_frames`는 strict integer
1..512, 기본24. bool/float/string/NaN/Inf/unknown enum payload 거부.
Project 기본 frame count와 fps는 기존 convention 그대로이며 period default는 output length와
독립적이다. Missing legacy fields→one_shot/24; load만으로 원본 파일을 rewrite하지 않는다.

`build_particle_instances`에서 seeded RNG를 한번 사용하여 count, delay, spawn shape,
direction/spread, speed, lifetime, scale, rotation, angular velocity, clip start/speed,
random seed를 canonical `ParticleInstance`로 구축한다. `particle_id=index`이며 기존
`ParticleInstance` 구조/생성 수식/RNG draw 순서는 변경하지 않았다.

기존 birth는 **composition-absolute**:
`settings.start_frame + schedule_offset + randint(start_delay_min,start_delay_max)`.
Burst 또는 count≤1에서는 schedule_offset=0; over_time은
`round(index*max(0,emission_duration-1)/(count-1))`. Line/Box/Circle 샘플 수식도 그대로다.
Circle은 circumference/arc이며 새 shapes는 추가하지 않았다.

Particle Resource Layer의 `as_particle_emitter`는 settings를 전달하며 renderer에 들어온 frame은
composition frame 그대로다. gate는 실제 기존 `particle_settings.start_frame`이다.
Resource Layer factory의 timing metadata도 이 값에서 초기화된다. 새로운 layer-local frame
재해석이나 start를 두 번 빼는 코드는 없다. Generated sequence도 기존 output_frame_count의
absolute frames 0..N-1을 쓴다. metadata의 end_frame을 새로운 cyclic simulation gate로 바꾸지 않았다.

## History-free copies와 identity

`particle_cyclic_emission_service.iter_particle_cycle_copies`:

```text
q = requested_frame - settings.start_frame
b = canonical.birth_frame - settings.start_frame
B(k) = canonical.birth_frame + k*P
age = requested_frame - B(k)
alive iff 0 <= age < L
k_min = ceil((q - b - (L-1))/P)
k_max = floor((q - b)/P)
```

Python integer division으로 ceil/floor를 계산해 큰 frame에서도 부동소수 경계 오차를 피한다.
q<0이면 contribution0; q=0부터 살아 있는 k<0 copies 포함. 비용은 O(canonical slots+alive copies),
frame0부터 과거를 simulation하지 않는다. 입력 frame100000도 동일 범위 계산이다.

`ParticleCycleCopy`는 immutable wrapper로 canonical reference, absolute copy birth, cycle index만
보관한다. sampled properties 및 **Noise particle_id는 canonical**에 위임한다. cycle RNG draws0.
Copy identity는 `(cycle_index,canonical particle_id)`; depth sort는
`(projected Z,(cycle index,slot ID))`. One Shot에서는 원래 `(projected Z,generation order)`를 유지한다.
t→t+P에서 cycle index가 일괄+1 되므로 상대 순서는 동일하다. Normal source-over의 순서를
깊이보다 우선하는 새 정렬로 바꾸지 않았다. copy별 dictionary/cache는 없고 canonical
spawn cache와 frame-keyed render cache만 사용하므로 copy ID collision을 만들지 않는다.
Diagnostics에 cycle_index/copy_key를 추가했고 canonical ID와 actual copy birth를 별도로 표시한다.

## 기존 evaluator 재사용

`render_particle_frame`에서 cyclic일 때만 copy iterator로 교체한다. One Shot은 기존 instances
fast path이며 historical enumeration이 없다. `render_particle_frames`, Resource Layer current/full,
parented rendering, generated materialization, exact playback, export는 이 evaluator를 재사용한다.

- Gravity: `.5*g*copy_age²`; Drag: `effective_motion_age(copy_age)`.
- Noise: emitter seed+canonical particle ID+copy age; 매 cycle salt를 바꾸지 않는다.
- Scale/Color/Opacity: 기존 normalized lifetime age, 마지막 visible age=L-1; L=1 의미도 그대로.
- Motion의 age/L 진행과 lifetime modulation의 age/(L-1)은 기존에 의도한 서로 다른 계약이다.
- Source frame/random clip start/playback speed: canonical samples+actual copy age.
- Negative-cycle prewarm은 position만 앞당기지 않고 위 appearance/playback 전체를 평가한다.
- System→Parent affine→2.5D→billboard→Surface 순서, parent_offset, Keep World,
  Rotation Revolution, Advanced bypass, Overscan 및 strict output clipping은 변경하지 않았다.

## Validation / UI / Undo

설정상 maximum birth offset을 사용한다. count_max>1의 over_time이면 duration-1,
그 외0에 delay_max를 더하며 `offset<P`가 필수다. Count0은 births가 없어서 span 제약 예외다.
Modulo/clamp/drop 없이 validation error. 기존 schedule 자체를 바꾸지 않는다.

정수 lifetime convention에서 한 slot의 동시 copy 최대는 `ceil(L/P)`다.
따라서 안전한 worst-case bound는 **count_max × ceil(lifetime_max/P)**, hard limit4096.
정확히4096은 허용, 초과는 명시적 거부. 과도하게 +2 copies를 세지 않아 가능한 경계 설정을
불필요하게 거부하지 않는다. sample lifetime은 max 이하이고 birth phase와 무관하게 이 상한이 성립한다.

기존 Emission group에 localized **Emission Mode / 방출 모드**, **Cycle Period / 반복 주기**를
추가했다. 기존 burst/over_time의 Mode는 유지한다. One Shot / 한 번만, Cyclic Steady / 지속 반복.
One Shot에서 period disabled, 값은 보존. Mode 변경으로 count/duration/delay/shape reset 없음.
작은 status label에 active upper bound와 global periodicity 제한을 표시한다.
Count tooltip은 주기당 전체 개수이며 particles/frame 또는 particles/sec가 아님을 설명한다.

UI invalid cyclic edits는 draft signal을 보내기 전에 검사하고 last accepted settings로 revert,
localization된 오류를 표시한다. model/dirty/revision/Undo 변화0. 기존 One Shot의 임시 resource-less
Inspector 편집 흐름에 새 full-validation을 강제하지 않아 이전 numeric commit 동작을 보존했다.
Programmatic cyclic update도 MainWindow에서 validate한다. Mode/Period accepted commits는
merge_id=-1로 각각 Undo1; 다른 numeric controls의 기존 merge 정책은 그대로다.
No-op/selection/refresh/localization은 mutation/Undo/revision을 만들지 않는다.

## Cache / playback / generated output

| 경로 | mode/period 영향 |
| --- | --- |
| canonical `_SPAWN_STATE_CACHE` / `_spawn_cache_key` | 두 새 fields 제외. 동일 sampled slots 및 tuple object 재사용; RNG reseed 없음 |
| Resource `_base_key`, `_BASE_CACHE` | settings.to_dict의 새 fields 포함, 기존 key 비교로 stale 방지 |
| `_TRANSFORM_CACHE` | base settings key+frame+surface values; settings 변경 시 기존 invalidation 경로 |
| exact playback | `playback_relevant_revision`에 mode/period 포함; 기존 application undo edit revision 변경/worker stale guards 재사용 |
| Particle preview draft/session | 기존 resource_layer_settings transaction이 revert/sync, 새 snapshot settings 전달; 동일 evaluator |
| generated pixels | accept/Undo/Redo의 기존 apply_effect_resource_layer로 재생성; source pixels를 canonical truth로 삼지 않음 |
| guide/proxy | canonical motion path는 mode/period에 따라 바뀌지 않음. 기존 Canvas cache clear와 refresh 사용; prewarm simulation guide 추가 없음 |

Actual 함수: build_particle_instances, particle_spawn_states, iter_particle_cycle_copies,
render_particle_frame(s), render_effect_resource_layer_current_frame/base, render_effect_resource_layer,
apply_effect_resource_layer, render_exact_playback_frame, export_png_frames,
MainWindow.update_particle_draft/apply_undo_value/_particle_settings_merge_id.

## Exactness / export 한계

정적/local emitter contribution에 대해 F(t+P)=F(t), Normal/Additive, Linear/Orbit/Helix 및
G/D/N/lifetime 조합을 검사했다. Global motion tracks, Layer/Parent/System/Surface/opacity tracks가
비주기적이면 전체 프로젝트의 seamless는 보장하지 않는다. 비주기적 layer track test가 이를 확인한다.
Local slot pattern은 매 주기 **동일**; evolving randomness가 없으며 짧은 주기에서 반복이 보이는
것은 의도된 exact-loop 계약이다. 미감/자연스러움은 사용자 GUI 확인이 필요하다.

N=mP일 때 virtual contribution F(N)=F(0); exported frames는 0..N-1이므로 마지막 PNG와
첫 PNG가 같을 필요는 없다. gate가0이 아니면 effect 전체 sequence의 시작/종료 timing도 별도 고려한다.
PNG dimensions/strict canvas는 그대로다. Per-particle/layer RGBA stages와 최종 합성 stage는
구분해서 검사했다: raw current=full=generated layer pixels, final exact playback=Project.compose_frame=PNG decode.
기존 float32 alpha composition에서 raw RGBA와 final RGBA 간 1LSB quantization이 생길 수 있어
서로 다른 stage의 raw array를 잘못 비교하지 않는다. 기존 compositor 의미를 변경하지 않았다.

## 실제 증거 / 성능

`tools/benchmark_cyclic_emission.py --output C:\Dev\pem_v22_cyclic_20261001_verified`
새 output 디렉터리만 생성하고 사용자 프로젝트/보호 PNG에 접근하지 않는다.
실제 v21 checkpoint renderer source를 read-only `git show`하여 독립 module로 평가했다.
변경하지 않은 dependency services/current model을 공유하는 비교라는 조건을 명시한다.
7 One Shot full-stack scenarios의 actual old builder slots 및 old renderer RGBA exact,
old/new warm render를 5회 교대 측정한다. 자동 성능 수치로 native GUI FPS/미감을 보증하지 않는다.

대표 3종 × P6/12/24=9 fixtures: canonical24, lifetime24..36, 시작 copy 약25..121,
상한48..144. Fire는 narrow Box+upward/signed Gravity+Drag+Noise+tint+Alpha+Additive,
Dust는 filled Box+slow Drag/Noise+Scale growth+Alpha+Normal,
Rain은 Line+fall+Gravity/Noise. 모두 negative-cycle copies/nonempty gate/periodicity/direct seek/
full/playback/save-reload/PNG equality 통과. Optional Smoke는 별도 추가하지 않았고 unlock 수에 더하지 않는다.
9 JSON project, 216 PNG sequence frames, contact_sheet.png, results.json은 C:/Dev에만 보관한다.
Contact sheet의 행은 Fire P6/12/24, Dust P6/12/24, Rain P6/12/24; 열0/1/5/6/12/23.
합성 작은 dot artwork이며 production art가 아니다. 시트를 직접 확인했다.

벤치마크는 Windows11/Python3.12.14, 96×96 RGBA, static white sprite, full G/D/N+Scale+Color+
Opacity+Additive. canonical100/500/1000, P1/12/24, lifetime1/24/96의 valid combinations.
1000×L24/P1=24000 상한은 expected validation rejection이며 억지로 render하지 않았다.
4000-copy full stack은 약0.4초/frame이 관측되어 realtime60FPS를 보장하지 않는다.
frame100000 enumeration은 현재 alive copies만 수행하고 history에 따른 cycle 누적 비용은 없다.
자세한 최종 수치는 results.json 및 아래 최종 검증 절에 기록한다.

## Tests / 문서 / 남은 기능

신규 `test_particle_cyclic_emission.py`, `test_particle_cyclic_emission_serialization.py`:
**75 focused passed**. Actual v21의 10종 SHA256 pixel goldens (Normal/Additive 포함), canonical reuse,
no new RNG/cache tuple identity, bounded ages/gates/negative copies, overflow/period/span payload,
L<P/L=P/L>P, period min/max, count0/1/max, boundary4096/plus-one,
G/D/N and Scale/Color/Alpha/sprite copy age, normal/additive periodicity, large seek,
layer/Surface/2.5D/parent_offset/Keep World/Revolution, nonperiodic tracks,
decoded PNG, format18 defaults/no rewrite/format19 roundtrip, Korean/English/selection/refresh,
Undo/no-op/revision/dirty/invalid revert를 검증한다.
기존 tests의 현재 version/schema assertions만 갱신했으며 legacy payload 형식과 unrelated numeric
sentinel18은 보존했다. 첫 전체 실행의 남은 hardcoded schema18 assertion1건도19로 수정했다.

README/CHANGELOG/Manual Checklist/Capability Audit 갱신. 과거 audit를 삭제하지 않았다.
좁은 Cyclic Steady end-to-end는 COMPLETE, 전체 Emission은 PARTIAL.
Rate API/multi-burst/fill-disk/annulus/mask/path/evolving randomness 없음.
Trail/Sub-emitter/Multi-point Lifetime/Force/Collision/infinite streaming/Sprite Sheet도 구현하지 않았다.
Fire/Dust/Rain sustained 목표는 코드/fixture 수준 practical; 완성품 art와 native interaction 승인은 별도다.
다음 추천 기능은 **Multi-point Lifetime**: peak/pulse/multi-stop의 반복 source artwork 작업을 줄이는 범위.

## 최종 검증 결과

| 최종 검사 | 결과 |
| --- | --- |
| Full pytest | **1410 passed in 90.49s**, failures0 |
| 신규 focused cyclic tests | **75 passed in 3.38s**; 추가 dirty/revision assertions도 full suite 통과 |
| compileall app/tests/tools | exit0 |
| app.main --version | Pixel Effect Maker v0.0.22 |
| FORMAT_VERSION | 19 |
| app.main --check / run_app.bat --check | 각각 exit0 |
| diagnostic verified | exit0, representatives9/benchmarks14/old renderer comparisons7 |
| Git | HEAD d91f9582984b3d63904c0666d5d76c700bf40b5d, staged0, v22 commit0 |
| 보호 PNG | 시작과 동일 SHA256, untracked/unstaged |
| diff --check / 신규 whitespace | 통과 |
| native Windows GUI manual | **수행하지 않음** |

Direct/batch --check는 sandbox AppData log 쓰기 제한으로 PermissionError /
logging_unavailable warning을 출력했다. 진단은 exit0이며 로그 파일 쓰기/GUI 수동 검증
성공을 주장하지 않는다. 보호 파일/권한을 변경하거나 경고를 숨기지 않았다.

### 최종 synthetic performance 상세

| Mode | Count | Period | Life | Active | v22 warm ms | v21 warm ms | T100000 ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| one_shot | 100 | 1 | 1 | 100 | 1.449 | 1.43 | — |
| cyclic_steady | 100 | 1 | 1 | 100 | 2.081 | — | 2.009 |
| one_shot | 500 | 12 | 24 | 500 | 70.304 | 82.101 | — |
| cyclic_steady | 500 | 12 | 24 | 1000 | 147.254 | — | 156.31 |
| one_shot | 1000 | 24 | 24 | 1000 | 139.474 | 126.972 | — |
| cyclic_steady | 1000 | 24 | 24 | 1000 | 140.822 | — | 171.548 |
| one_shot | 100 | 12 | 96 | 100 | 15.126 | 17.038 | — |
| cyclic_steady | 100 | 12 | 96 | 800 | 114.348 | — | 122.549 |
| one_shot | 500 | 24 | 96 | 500 | 71.991 | 68.147 | — |
| cyclic_steady | 500 | 24 | 96 | 2000 | 287.799 | — | 285.488 |
| one_shot | 1000 | 24 | 96 | 1000 | 151.8 | 141.877 | — |
| cyclic_steady | 1000 | 24 | 96 | 4000 | 473.019 | — | 473.649 |
| one_shot | 1000 | 1 | 24 | 1000 | 123.004 | 122.531 | — |
| cyclic_steady | 1000 | 1 | 24 | rejected 24000 | — | — | — |

One Shot v21/v22는 동일 emitter/frame의5회 교대 median이고, Cyclic warm은3회 median이다.
대조 source는 실제 af9be4c renderer이며 unchanged services/current model을 공유한다.
측정 중 자동 테스트 등 호스트 부하가 있을 수 있으므로 작은 차이를 일반화하지 않는다.
One Shot에 history enumeration을 추가하지 않았고7 workload에서 canonical properties와
RGBA exact를 별도 확인했다. Cyclic T100000의 enumeration은 실제 copy count에만 비례한다.
4,000 active copies의 최종 warm473.019ms/direct473.649ms는 real-time performance 한계다.
상한은 안전장치이지 60FPS 보증이 아니다. 폭넓은 renderer rewrite를 추가하지 않았다.

Native Windows GUI manual: **수행하지 않음**. 실제 GUI 승인 전 v22 stage/commit하지 않는다.

## 요청 209항목 대응

각 행은 사용자 완료 보고 항목 번호와 대응한다. 상세 코드 계약은 위 각 절을 참조한다.


| 번호 | 요청 항목 | 실제 결과/계약 |
| --- | --- | --- |
| 1 | 실제 작업 시작 HEAD | af9be4c948f3d3a09700478dc00dd2102196c2ab |
| 2 | 시작 Version | v0.0.21 |
| 3 | 시작 FORMAT_VERSION | 18 |
| 4 | 시작 pytest | 1335 passed / 82.37s |
| 5 | Audit checkpoint commit hash | d91f9582984b3d63904c0666d5d76c700bf40b5d |
| 6 | 포함 파일 | 기존 audit + Post-v21 report + recheck script 3개 |
| 7 | 제외 파일 | 보호 PNG, C:/Dev evidence, 이후 v22 변경 |
| 8 | checkpoint 후 Git | main ahead40, staged0, PNG만 untracked |
| 9 | ParticleEmitterSettings 관련 필드 | cycle mode/period 추가; 기존 schedule/count/delay/seed 필드 유지 |
| 10 | ParticleInstance 구조 | 기존 frozen sampled fields unchanged; copy wrapper 별도 |
| 11 | canonical instance build 함수 | build_particle_instances / particle_spawn_states |
| 12 | birth schedule 함수 | 기존 build_particle_instances 수식 |
| 13 | birth_frame 의미 | composition-absolute frame |
| 14 | layer/start gate | particle_settings.start_frame 한 번 적용 |
| 15 | burst semantics | offset0 + random delay |
| 16 | over_time semantics | round(i*(duration-1)/(count-1)), count≤1은0 |
| 17 | random delay semantics | randint(min,max), schedule offset에 합산 |
| 18 | count sampling | seed RNG randint(min,max) 1회 |
| 19 | lifetime sampling | canonical slot당 randint(min,max) 1회 |
| 20 | particle_id semantics | canonical generation index |
| 21 | spawn cache | _SPAWN_STATE_CACHE; 새2fields 제외 |
| 22 | render cache | base settings repr+frame / transform values |
| 23 | depth/order key | projected Z → cycle+slot; One Shot은 기존 order |
| 24 | Version | v0.0.22 |
| 25 | FORMAT_VERSION | 19 |
| 26 | emission mode model | 기존 convention에 맞춘 string tokens |
| 27 | One Shot default | one_shot |
| 28 | Cyclic Steady | cyclic_steady |
| 29 | period field | emission_period_frames |
| 30 | period min/max/default | strict int 1..512/default24 |
| 31 | migration | missing→one_shot/24; 원본 load rewrite 없음 |
| 32 | ONE_SHOT v0.0.21 byte compatibility | v21 10종 pixel goldens exact + 실제 old renderer 비교 |
| 33 | RNG draw compatibility | actual checkpoint builder samples exact |
| 34 | particle ID compatibility | 기존 particle_id=index 그대로 |
| 35 | spawn compatibility | shape 및 모든 sampled properties 그대로 |
| 36 | performance fast path | One Shot에 cycle enumeration 없음; 기존 instance path |
| 37 | slot identity | 기존 canonical particle_id |
| 38 | sampled properties | position/direction/speed/scale/lifetime/playback/delay 그대로 |
| 39 | slot birth offset | canonical.birth_frame - start_frame |
| 40 | cycle reuse | 동일 slot object를 모든 cycle에서 참조 |
| 41 | new RNG draws 여부 | cycle enumeration RNG draws0 |
| 42 | local cycle time | q=composition frame-start_frame |
| 43 | cycle copy birth formula | absolute canonical birth+kP |
| 44 | actual age | frame-copy birth |
| 45 | visible condition | 0≤age<L, 마지막 age L-1 |
| 46 | negative cycle index | alive 범위이면 k<0 포함 |
| 47 | prewarm | gate 순간 previous copies 상태 즉시 평가 |
| 48 | analytic k min/max | ceil((q-b-(L-1))/P)..floor((q-b)/P) |
| 49 | large-frame behavior | T100000도 O(slots+alive copies), history loop 없음 |
| 50 | canonical slot identity | canonical particle_id |
| 51 | cycle-copy identity | (cycle_index,canonical particle_id) |
| 52 | Noise identity | canonical ID+emitter seed+copy age |
| 53 | render sort identity | (depth,(cycle,slot)), 상대 순서 보존 |
| 54 | collision/cache key 여부 | copy별 dict/cache 없음; tuple key unique |
| 55 | slot birth constraint | 0≤maximum possible offset<P |
| 56 | duration interaction | over_time count_max>1이면 duration-1 |
| 57 | delay interaction | delay_max 합산 후 검사 |
| 58 | invalid period behavior | ValueError/UI localized rejection+revert |
| 59 | modulo/clamp/drop 없음 | 없음, canonical schedule 변경 없음 |
| 60 | frame gate 이전 | contribution0 |
| 61 | gate frame | prewarm 상태로 등장 |
| 62 | previous-cycle alive copies | k<0 alive copies 포함 |
| 63 | lifetime > period | 동시에 여러 cycle copies |
| 64 | multiple copies per slot | bound 내 모두 평가, truncate 없음 |
| 65 | F(t+P)=F(t) | t/t+P/t+2P RGBA exact, Normal/Additive 및 L>P 자동 검증 |
| 66 | Normal | t/t+P/t+2P RGBA exact, Normal/Additive 및 L>P 자동 검증 |
| 67 | Additive | t/t+P/t+2P RGBA exact, Normal/Additive 및 L>P 자동 검증 |
| 68 | lifetime>P | t/t+P/t+2P RGBA exact, Normal/Additive 및 L>P 자동 검증 |
| 69 | multiple periods | t/t+P/t+2P RGBA exact, Normal/Additive 및 L>P 자동 검증 |
| 70 | last-vs-first 설명 | F(N)=F(0), 마지막 PNG N-1=0 요구하지 않음 |
| 71 | Layer animation periodicity 제한 | global layer tracks는 별도 주기 조건 |
| 72 | Parent animation 제한 | parent tracks도 별도 주기 조건 |
| 73 | full-project seamless 보장 범위 | static/local emitter만 자동 periodicity 보장 |
| 74 | UI/document warning | KO/EN mode/period tooltip 및 status warning |
| 75 | active-copy upper bound | count_max*ceil(lifetime_max/P) |
| 76 | active-copy limit | 4096 simultaneous copies |
| 77 | exact-boundary case | exact4096 허용 test |
| 78 | over-limit behavior | 초과 ValueError/UI revert |
| 79 | silent drop 여부 | 없음 |
| 80 | Emission section | 기존 Emission group |
| 81 | mode label | Emission Mode / 방출 모드 |
| 82 | One Shot label | One Shot / 한 번만 |
| 83 | Cyclic label | Cyclic Steady / 지속 반복 |
| 84 | Period | Cycle Period / 반복 주기, frames suffix |
| 85 | Korean | KO labels/status/tooltips |
| 86 | English | EN labels/status/tooltips |
| 87 | tooltip | seed repeat/previous cycles/count units/global limit |
| 88 | period enable/disable | One Shot disabled, 값 보존 |
| 89 | validation status | localized reason+last accepted revert |
| 90 | active-copy estimate | worst-case active bound status |
| 91 | refresh safety | selection A17/B41/A, no signal/model/revision change |
| 92 | mode | accepted commit Undo1, merge_id=-1 |
| 93 | period | 각 accepted commit Undo1 |
| 94 | no-op | Undo/dirty/revision0 |
| 95 | refresh | Undo/model/revision0 |
| 96 | invalid edit | revert, draft signal0, 이전 model 보존 |
| 97 | spawn RNG | 기존 random.Random(seed) canonical sampling 동일; actual v21 builder comparison exact |
| 98 | count | 기존 random.Random(seed) canonical sampling 동일; actual v21 builder comparison exact |
| 99 | position | 기존 random.Random(seed) canonical sampling 동일; actual v21 builder comparison exact |
| 100 | direction | 기존 random.Random(seed) canonical sampling 동일; actual v21 builder comparison exact |
| 101 | speed | 기존 random.Random(seed) canonical sampling 동일; actual v21 builder comparison exact |
| 102 | scale | 기존 random.Random(seed) canonical sampling 동일; actual v21 builder comparison exact |
| 103 | lifetime | 기존 random.Random(seed) canonical sampling 동일; actual v21 builder comparison exact |
| 104 | playback | 기존 random.Random(seed) canonical sampling 동일; actual v21 builder comparison exact |
| 105 | delay | 기존 random.Random(seed) canonical sampling 동일; actual v21 builder comparison exact |
| 106 | cycle copy RNG draws | RNG0, wrapper만 생성 |
| 107 | Gravity copy age | .5*g*copy actual age² |
| 108 | Drag copy age | effective_motion_age(copy age) |
| 109 | Noise copy age | Noise actual copy age |
| 110 | canonical Noise seed | slot ID로 seed 유지, cycle index로 reseed하지 않음 |
| 111 | Scale | 기존 lifetime multiplier |
| 112 | Color | 기존 RGB multiplier |
| 113 | Opacity | 기존 eased alpha |
| 114 | normalized lifetime | age/(L-1), L1은 기존 convention |
| 115 | prewarm lifetime state | position뿐 아니라 모든 채널에 prewarm copy age |
| 116 | sprite frame | particle_clip_frame_index(copy age) |
| 117 | playback random | canonical clip start/speed 샘플 재사용 |
| 118 | prewarm playback state | 이전 copy의 실제 sprite age |
| 119 | canonical spawn cache | mode/period key에서 제외, cached tuple same object |
| 120 | render cache | settings repr에 fields 포함 |
| 121 | preview cache | 기존 snapshot settings/draft revert/session invalidation |
| 122 | playback revision | playback_relevant_revision 새 fields + existing edit revision |
| 123 | generated output | 기존 apply_effect_resource_layer regenerate |
| 124 | mode invalidation | key+existing transaction invalidation |
| 125 | period invalidation | key+existing transaction invalidation |
| 126 | reseed 여부 | 없음; guide는 canonical path라 불필요한 새 sampling 없음 |
| 127 | Parenting | 기존 parent affine 유지, cyclic parity test |
| 128 | parent_offset | 기존 9-value offset 유지 |
| 129 | Keep World | 새 cyclic Keep World parity test |
| 130 | System | 기존 Layer Space evaluator |
| 131 | Surface | 기존 post Surface transform |
| 132 | 2.5D | Rotation X/Y+perspective parity test |
| 133 | Rotation Revolution | 720° test + 기존 full regression |
| 134 | sequential | raw current/full/generated layer exact; final playback/composition/PNG exact, seek 순서 무관 |
| 135 | direct | raw current/full/generated layer exact; final playback/composition/PNG exact, seek 순서 무관 |
| 136 | step | raw current/full/generated layer exact; final playback/composition/PNG exact, seek 순서 무관 |
| 137 | current frame | raw current/full/generated layer exact; final playback/composition/PNG exact, seek 순서 무관 |
| 138 | full render | raw current/full/generated layer exact; final playback/composition/PNG exact, seek 순서 무관 |
| 139 | generated output | raw current/full/generated layer exact; final playback/composition/PNG exact, seek 순서 무관 |
| 140 | PNG | raw current/full/generated layer exact; final playback/composition/PNG exact, seek 순서 무관 |
| 141 | large-frame seek | 100000 direct, active copies만 열거 |
| 142 | sequence periodicity | static/local N=mP이면 periodic |
| 143 | virtual N frame contract | virtual F(N)=F(0) |
| 144 | dimensions | 기존 canvas width/height RGBA |
| 145 | strict clip | 기존 strict clipping 유지 |
| 146 | overscan | editor overscan 변경 없음, 기존 regression suite |
| 147 | benchmark fixture | tools/benchmark_cyclic_emission.py, C:/Dev verified results |
| 148 | canonical count | 100/500/1000 |
| 149 | Period | 1/12/24 |
| 150 | lifetime | 1/24/96 |
| 151 | active copy count | actual 100..4000, invalid24000 rejection |
| 152 | ONE_SHOT | actual checkpoint renderer와 교대5회 비교 |
| 153 | CYCLIC | full-stack valid cases, median3 |
| 154 | lifetime>P | 여러 copies 포함, same local pattern |
| 155 | full feature stack | G+D+N+Scale+Color+Opacity+Additive |
| 156 | history independence | large-frame enumeration0..100000 counts bounded |
| 157 | Fire/Ember | P6/12/24 gate nonempty/prewarm/exact |
| 158 | Area Dust | P6/12/24 filled Box+slow motion/growth/exact |
| 159 | Rain/Snow | P6/12/24 Line+Gravity/Noise/exact |
| 160 | optional Smoke | 별도 fixture 없음, unlock 중복 없음 |
| 161 | sustained goal completion | 3 sustained 목표 code/fixture practical, 미감은 사용자 확인 |
| 162 | 신규 files | test_particle_cyclic_emission.py / serialization.py |
| 163 | focused count | 75 focused passed |
| 164 | legacy exact | 10 v21 SHA256 goldens+checkpoint renderer |
| 165 | prewarm | negative copies+age+sprite+modulation |
| 166 | periodicity | Normal/Additive/linear/orbit/helix/multiple periods |
| 167 | identity | canonical ID vs copy_key unique |
| 168 | RNG isolation | cached canonical tuple/RNG draws0 |
| 169 | motion | G/D/N copy age test |
| 170 | lifetime | Scale/Color/Alpha normalized age test |
| 171 | cache | mode/period/revision/base-key test |
| 172 | UI/Undo | KO/EN/Undo/noop/refresh/invalid revert |
| 173 | serialization | format18 missing defaults/no rewrite, format19 roundtrip |
| 174 | safety bounds | 4096 exact/over, integer payloads, span |
| 175 | transforms | parent_offset/Keep World/System/Surface/2.5D/Revolution |
| 176 | export | raw stage parity 및 final composed PNG parity |
| 177 | full pytest | 1410 passed / 90.49s |
| 178 | compileall | compileall app/tests/tools exit0 |
| 179 | --version | Pixel Effect Maker v0.0.22 |
| 180 | --check | exit0, sandbox logging warning 별도 |
| 181 | run_app.bat | exit0, 동일 logging warning |
| 182 | git diff --check | tracked diff/new whitespace 검사 |
| 183 | Cyclic Steady capability state | 좁은 end-to-end COMPLETE |
| 184 | overall Emission state | 전체 Emission PARTIAL |
| 185 | remaining Rate gap | particles/sec 없음 |
| 186 | remaining Multi-Burst gap | multi-burst editor 없음 |
| 187 | remaining Spawn Shape quality gaps | filled disk/annulus/mask/path 없음 |
| 188 | 최종 HEAD | d91f9582984b3d63904c0666d5d76c700bf40b5d |
| 189 | staged | 0 |
| 190 | v0.0.22 commit | 0 |
| 191 | tag/push/build | tag/push/build/PyInstaller/ZIP/release0 |
| 192 | Windows native GUI manual 여부 | 수행하지 않음 |
| 193 | ONE_SHOT legacy exact 여부 | 검증한 legacy samples/RGBA exact |
| 194 | stateful simulation 없는지 | 없음, bounded integer evaluation |
| 195 | steady prewarm 성공 여부 | 성공, gate nonempty |
| 196 | previous-cycle alive copies 성공 여부 | 성공, k<0 실제 lifetime 포함 |
| 197 | Direct Seek deterministic 여부 | 성공, reverse/random/large seek |
| 198 | F(t+P)=F(t) local periodicity 여부 | 성공, static/local contribution |
| 199 | RNG/Noise periodicity 여부 | 성공, canonical slots repeat |
| 200 | lifetime>period 처리 여부 | 성공, 여러 alive copies 동시에 |
| 201 | active-copy safety 여부 | worst-case bound4096, 초과 거부 |
| 202 | Preview/Export parity | 동일 stage exact (raw vs final stage 구분) |
| 203 | sustained Fire practical 여부 | fixture/code practical |
| 204 | sustained Dust practical 여부 | fixture/code practical |
| 205 | sustained Rain/Snow practical 여부 | fixture/code practical |
| 206 | exact repeated pattern의 의도된 한계 | 짧은 주기 동일 random pattern 반복은 의도 |
| 207 | 전체 프로젝트 seamless 보장 한계 | nonperiodic Layer/Parent/global tracks는 제외 |
| 208 | 실제 표현력 개선 평가 | 유한 기본형을 지속형으로 재사용 가능; art/GUI 자연스러움 자동 판단 없음 |
| 209 | 다음 추천 기능 | Multi-point Lifetime 권장 |
