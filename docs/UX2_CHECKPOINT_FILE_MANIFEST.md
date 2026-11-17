# Checkpoint File Manifest — 2026-10-30

기준 HEAD `ea8ff478c12a9b1032982476f84da62f4009d095`. 시작 변경68개(29 tracked M/39 untracked), 그 중 사용자 PNG1개는 보호 제외다.
이 표는 기존 변경 전체의 검토용 분류이며 staging/commit 승인이 아니다. A=Inspector/UI, B=Gizmo/Lifetime/Group/Lifecycle, C=FPS, D=SpinBox 검사, E=DevEx, F=문서/사용자 자료.
문서/도구의 과거 실행 이력을 현재 candidate에서 전부 검증했다는 뜻으로 읽지 않는다. 같은 파일에 다수 범주가 있으면 명시했다.

## 회귀 검사 묶음 약어

- T_A: `test_inspector_components.py`, `test_particle_inspector_workflow.py`, `test_inspector_visual_quality.py`, 기존 architecture/layout/Particle UI 검사.
- T_B: `test_native_regression_repair.py`의 Lifetime/Group, `test_interactive_transform_proxy.py`, `test_gizmo_inspector_sync_wait.py`, `test_gizmo_visual_overlay.py`, `test_v9_editor_lifecycle_integration.py`, `test_lifecycle_prewarm_isolation.py`, 기존 group/prewarm 검사.
- T_C: `test_fps_playback_semantics.py`, Native Regression rotation/FPS/output extent/speed, 기존 speed range/Undo 및 revolution 검사.
- T_D: `test_native_spinbox_buttons.py`, `test_spinbox_repeat_conditions.py`, Numeric commit/bounds/Ctrl-wheel.
- T_E: `test_diagnostics_cli.py` 및 registry `--check all` 175 cases. 실제 Group trace/child cleanup도 CLI tests에 포함.
모든 test 약어 경로의 접두사는 `tests/`다. 개별 test 행은 해당 파일 자체와 그 import closure가 필수다.

## 파일별 분류

| 파일 | Git 상태 | 범주 | 목적 | 범주 간 의존성 / HEAD 없는 직접 import | HEAD에 없는 부분 | 관련 검사 | 체크포인트 독립성 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `AGENTS.md` | untracked | F/E | WORK_QUEUE 읽기 및 작업 규약 링크; 새 정책 파일 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_E | 문서 단독 가능; 근거·범위/사용자 승인 별도 |
| `app/services/effect_group_service.py` | untracked | B | 공유 read-only Group/Ungroup 자격·거부 이유 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_B | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `app/services/effect_resource_layer_render_service.py` | tracked M | C | Single base cache key에 output extent 포함 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | T_C | 본 계획 CP2; CP1 선행 |
| `app/services/localization_service.py` | tracked M | C | Resource FPS·source speed·Effect output FPS KO/EN 안내 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | T_C | 본 계획 CP2; CP1 선행 |
| `app/services/particle_preview_service.py` | tracked M | C | preserve_drafts reset 및 특정 source revision/session/pending 무효화 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | T_C | 본 계획 CP2; CP1 선행 |
| `app/services/particle_render_service.py` | tracked M | C | composition FPS 샘플링의 정수 곱셈 우선 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | T_C | 본 계획 CP2; CP1 선행 |
| `app/ui/canvas_widget.py` | tracked M | A+B | Gizmo NoBrush/save·restore, 시각 크기와 hitbox 분리·가이드 숨김 | 추가 untracked 직접 import 없음; A/B를 CP1로 결합 | dirty hunk는 HEAD에 없음 | T_A/T_B | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `app/ui/effect_library_panel.py` | tracked M | A+B | 명령 divider/role 스타일과 Group eligibility·선택 후 상태 동기화 | `app/services/effect_group_service.py`; A/B를 CP1로 결합 | dirty hunk는 HEAD에 없음 | T_A/T_B | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `app/ui/inspector_components.py` | tracked M | A | InspectorSection·native disclosure/status/동적 HFW 기반 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | T_A | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `app/ui/interactive_proxy_prewarm.py` | tracked M | B | close: pending cancel 및 poll 중단 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | T_B | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `app/ui/layout_metrics.py` | tracked M | A | shared spacing·action role·gizmo visual/hit tokens | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | T_A | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `app/ui/lifetime_point_editor.py` | tracked M | B | compound HFW/constraints·label/editor wrap·동적 오류 높이 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | T_B | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `app/ui/main_window.py` | tracked M | B+C | Group command guard·close 정리 + FPS derived 재생성·stale preview 무효화 | `app/services/effect_group_service.py`; C를 CP2로 분리, CP1 선행 | dirty hunk는 HEAD에 없음 | T_B/T_C | 파일 단위 불가; CP1/CP2 hunk 분리 검증 |
| `app/ui/particle_inspector_workflow.py` | untracked | A+C | 8범주/Search/Jump/view-only workflow + FPS/source speed 안내 | 추가 untracked 직접 import 없음; C를 CP2로 분리, CP1 선행 | 파일 자체가 HEAD에 없음 | T_A/T_C | 파일 단위 불가; CP1/CP2 hunk 분리 검증 |
| `app/ui/particle_properties_panel.py` | tracked M | A | 기존 controls 유지한 workflow 연결·message 기반 status | `app/ui/particle_inspector_workflow.py` | dirty hunk는 HEAD에 없음 | T_A | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `app/ui/resource_editor_v2/composition_inspector.py` | tracked M | C | Resource FPS 입력·초 길이·기존 metadata Undo | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | T_C | 본 계획 CP2; CP1 선행 |
| `app/ui/resource_editor_v2/resource_editor_widget.py` | tracked M | C | Resource FPS 변경 시 preview 정지 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | T_C | 본 계획 CP2; CP1 선행 |
| `docs/ASEPRITE_TIMING_TIMELINE_ARCHITECTURE_AUDIT.md` | untracked | F | Timing 소유권·후속 설계 감사; 새 모델 구현 아님 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | 문서/보호 hash 검토 | 문서 단독 가능; 근거·범위/사용자 승인 별도 |
| `docs/DEVEX1_DIAGNOSTICS.md` | untracked | F/E | 해당 작업의 검증 근거·제약·미확인 사항 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_E | 문서 단독 가능; 근거·범위/사용자 승인 별도 |
| `docs/ROADMAP.md` | tracked M | F/E | 현재 queue로 안내하는 2줄만 추가; 과거 계획 본문 보존 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | T_E | 문서 단독 가능; 근거·범위/사용자 승인 별도 |
| `docs/TIMING_FPS_PLAYBACK_REPORT.md` | untracked | F/C | 해당 작업의 검증 근거·제약·미확인 사항 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_C | 문서 단독 가능; 근거·범위/사용자 승인 별도 |
| `docs/UI_SPINBOX_AUTOREPEAT_REPORT.md` | untracked | F/D | 해당 작업의 검증 근거·제약·미확인 사항 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_D | 문서 단독 가능; 근거·범위/사용자 승인 별도 |
| `docs/UI_UX_PRINCIPLES.md` | tracked M | F/A | view-only/height-for-width/역할/overlay 공통 규칙 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | T_A | 문서 단독 가능; 근거·범위/사용자 승인 별도 |
| `docs/UX2_GIZMO_SYNC_REPAIR_REPORT.md` | untracked | F/A+B | 해당 작업의 검증 근거·제약·미확인 사항 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_A/T_B | 문서 단독 가능; 근거·범위/사용자 승인 별도 |
| `docs/UX2_LIFECYCLE_ISOLATION_REPORT.md` | untracked | F/A+B | 해당 작업의 검증 근거·제약·미확인 사항 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_A/T_B | 문서 단독 가능; 근거·범위/사용자 승인 별도 |
| `docs/UX2_NATIVE_GUI_CORRECTIONS_REPORT.md` | untracked | F/A+B | 해당 작업의 검증 근거·제약·미확인 사항 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_A/T_B | 문서 단독 가능; 근거·범위/사용자 승인 별도 |
| `docs/UX2_NATIVE_REGRESSION_REPAIR_REPORT.md` | untracked | F/B+C | Lifetime/Group 및 FPS 회전 수정 이력 혼합; C 뒤 문서화 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_B/T_C | B+C 이력 혼합; CP2 뒤 전체 포함 |
| `docs/UX2_PARTICLE_INSPECTOR_REPORT.md` | untracked | F/A+B | 해당 작업의 검증 근거·제약·미확인 사항 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_A/T_B | 문서 단독 가능; 근거·범위/사용자 승인 별도 |
| `docs/UX2_VERIFY_CHECKPOINT_REPORT.md` | untracked | F | 누적 검증과 과거 DevEx-only 3 ERROR 보존 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | 문서/보호 hash 검토 | 문서 단독 가능; 근거·범위/사용자 승인 별도 |
| `docs/tasks/WORK_QUEUE.md` | tracked M | F | 누적 상태·검증·의존성·Backlog; 작업별 혼합 문서 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | 문서/보호 hash 검토 | 문서 단독 가능; 근거·범위/사용자 승인 별도 |
| `tests/gizmo_sync_support.py` | untracked | B | test-only timer/필드/값/layout 완료 관찰 helper | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_B | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tests/spinbox_repeat_support.py` | untracked | D | native timer 반복·Release 취소·guard 완료 helper | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_D | D 묶음 독립 가능(HEAD+D 22 PASS); 파일 단독 아님 |
| `tests/test_2_5d_inspector_architecture.py` | tracked M | A | 기존 assertion/fixture의 UX2 경로 갱신 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | `tests/test_2_5d_inspector_architecture.py` | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tests/test_diagnostics_cli.py` | untracked | E | 신규 회귀 검사/fixture | `tools/diagnose_editor.py`; `tools/diagnostics/process.py`; `tools/diagnostics/registry.py`; `tools/diagnostics/worker.py`; registry/trace는 CP1+2+3 필요 | 파일 자체가 HEAD에 없음 | `tests/test_diagnostics_cli.py` | 단독 불가; CP1+2+3 뒤 CP4 |
| `tests/test_editor_layout_polish.py` | tracked M | A | 기존 assertion/fixture의 UX2 경로 갱신 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | `tests/test_editor_layout_polish.py` | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tests/test_effect_inspector_responsive_layout.py` | tracked M | A | 기존 assertion/fixture의 UX2 경로 갱신 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | `tests/test_effect_inspector_responsive_layout.py` | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tests/test_fps_playback_semantics.py` | untracked | C | 신규 회귀 검사/fixture | `tests/test_native_regression_repair.py` | 파일 자체가 HEAD에 없음 | `tests/test_fps_playback_semantics.py` | 본 계획 CP2; CP1 선행 |
| `tests/test_gizmo_inspector_sync_wait.py` | untracked | B | 신규 회귀 검사/fixture | `tests/gizmo_sync_support.py` | 파일 자체가 HEAD에 없음 | `tests/test_gizmo_inspector_sync_wait.py` | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tests/test_gizmo_visual_overlay.py` | untracked | B | 신규 회귀 검사/fixture | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | `tests/test_gizmo_visual_overlay.py` | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tests/test_inspector_components.py` | tracked M | A | 기존 assertion/fixture의 UX2 경로 갱신 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | `tests/test_inspector_components.py` | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tests/test_inspector_visual_quality.py` | untracked | A | 신규 회귀 검사/fixture | `tools/inspector_visual_probe.py` | 파일 자체가 HEAD에 없음 | `tests/test_inspector_visual_quality.py` | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tests/test_interactive_transform_proxy.py` | tracked M | B | 기존 assertion/fixture의 UX2 경로 갱신 | `tests/gizmo_sync_support.py` | dirty hunk는 HEAD에 없음 | `tests/test_interactive_transform_proxy.py` | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tests/test_lifecycle_prewarm_isolation.py` | untracked | B | 신규 회귀 검사/fixture | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | `tests/test_lifecycle_prewarm_isolation.py` | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tests/test_native_regression_repair.py` | untracked | B+C | Lifetime/Group 회귀 + rotation fixture·FPS/source sampling 회귀(파일 혼합) | `app/services/effect_group_service.py`; `tools/inspector_visual_probe.py`; C를 CP2로 분리, CP1 선행 | 파일 자체가 HEAD에 없음 | `tests/test_native_regression_repair.py` | 파일 단위 불가; CP1/CP2 hunk 분리 검증 |
| `tests/test_native_spinbox_buttons.py` | tracked M | D | 기존 assertion/fixture의 UX2 경로 갱신 | `tests/spinbox_repeat_support.py` | dirty hunk는 HEAD에 없음 | `tests/test_native_spinbox_buttons.py` | D 묶음 독립 가능(HEAD+D 22 PASS); 파일 단독 아님 |
| `tests/test_particle_inspector_workflow.py` | untracked | A | 신규 회귀 검사/fixture | `app/ui/particle_inspector_workflow.py` | 파일 자체가 HEAD에 없음 | `tests/test_particle_inspector_workflow.py` | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tests/test_particle_motion_gizmo.py` | tracked M | A | 기존 assertion/fixture의 UX2 경로 갱신 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | `tests/test_particle_motion_gizmo.py` | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tests/test_particle_sub_emitter_ui.py` | tracked M | A | 기존 assertion/fixture의 UX2 경로 갱신 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | `tests/test_particle_sub_emitter_ui.py` | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tests/test_particle_trail_ui.py` | tracked M | A | 기존 assertion/fixture의 UX2 경로 갱신 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | `tests/test_particle_trail_ui.py` | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tests/test_resource_layer_panel_clarity.py` | tracked M | A | 기존 assertion/fixture의 UX2 경로 갱신 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | `tests/test_resource_layer_panel_clarity.py` | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tests/test_spinbox_repeat_conditions.py` | untracked | D | 신규 회귀 검사/fixture | `tests/spinbox_repeat_support.py` | 파일 자체가 HEAD에 없음 | `tests/test_spinbox_repeat_conditions.py` | D 묶음 독립 가능(HEAD+D 22 PASS); 파일 단독 아님 |
| `tests/test_v9_editor_lifecycle_integration.py` | tracked M | B | 기존 assertion/fixture의 UX2 경로 갱신 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | `tests/test_v9_editor_lifecycle_integration.py` | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tools/audit_editor_ux.py` | tracked M | A | 고정 nav와 scroll body의 측정 owner 분리 | 추가 untracked 직접 import 없음 | dirty hunk는 HEAD에 없음 | T_A | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tools/audit_particle_workflow.py` | untracked | A | 합성 IA/탐색/geometry 관찰 도구 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_A | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tools/diagnose_editor.py` | untracked | E | 진단 CLI·private env·출력 경계·집계 | `tools/diagnostics/process.py`; `tools/diagnostics/registry.py`; registry/trace는 CP1+2+3 필요 | 파일 자체가 HEAD에 없음 | T_E | 단독 불가; CP1+2+3 뒤 CP4 |
| `tools/diagnostics/__init__.py` | untracked | E | diagnostics package 경계 | 추가 untracked 직접 import 없음; registry/trace는 CP1+2+3 필요 | 파일 자체가 HEAD에 없음 | T_E | 단독 불가; CP1+2+3 뒤 CP4 |
| `tools/diagnostics/process.py` | untracked | E | bounded child output·timeout·Windows Job Object cleanup | 추가 untracked 직접 import 없음; registry/trace는 CP1+2+3 필요 | 파일 자체가 HEAD에 없음 | T_E | 단독 불가; CP1+2+3 뒤 CP4 |
| `tools/diagnostics/registry.py` | untracked | E | UI90/Rotation49/Groups13/Render23 node 목록과 explicit tools | `tests/test_fps_playback_semantics.py`; `tests/test_inspector_visual_quality.py`; `tests/test_lifecycle_prewarm_isolation.py`; `tests/test_native_regression_repair.py`; `tests/test_spinbox_repeat_conditions.py`; registry/trace는 CP1+2+3 필요 | 파일 자체가 HEAD에 없음 | T_E | 단독 불가; CP1+2+3 뒤 CP4 |
| `tools/diagnostics/trace_adapter.py` | untracked | E | opt-in Group/Undo/FPS/cache bounded metadata patch | 추가 untracked 직접 import 없음; registry/trace는 CP1+2+3 필요 | 파일 자체가 HEAD에 없음 | T_E | 단독 불가; CP1+2+3 뒤 CP4 |
| `tools/diagnostics/worker.py` | untracked | E | pytest adapter·privacy·Qt cleanup·gizmo allowlist | `tools/diagnostics/registry.py`; `tools/diagnostics/trace_adapter.py`; `tools/inspector_visual_probe.py`; registry/trace는 CP1+2+3 필요 | 파일 자체가 HEAD에 없음 | T_E | 단독 불가; CP1+2+3 뒤 CP4 |
| `tools/inspector_visual_probe.py` | untracked | A | make_panel·geometry fixture와 screenshot helper | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_A | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tools/native_inspector_preview.py` | untracked | A | 명시적 native/offscreen 합성 preview; 이번 실행 안 함 | `tools/inspector_visual_probe.py` | 파일 자체가 HEAD에 없음 | T_A | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tools/native_regression_probe.py` | untracked | B+C | Lifetime/Group 합성 도구이나 Group 경로가 rotation_project(C helper)를 import | `tests/test_native_regression_repair.py`; `tools/inspector_visual_probe.py` | 파일 자체가 HEAD에 없음 | T_B/T_C | 본 계획 CP2; CP1 선행 |
| `tools/probe_gizmo_sync.py` | untracked | B | bounded old/fixed gizmo 계측 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_B | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tools/probe_lifecycle_isolation.py` | untracked | B | bounded render 주체/phase·fixed 계약 관찰 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_B | CP1 의존성 묶음; 파일 단독 검증 아님 |
| `tools/probe_spinbox_autorepeat.py` | untracked | D | bounded native/fixed/controlled style 관찰 | 추가 untracked 직접 import 없음 | 파일 자체가 HEAD에 없음 | T_D | D 묶음 독립 가능(HEAD+D 22 PASS); 파일 단독 아님 |
| `tools/rotation_regression_probe.py` | untracked | C | 합성 Resource/Effect 회전 RGBA 증거 | `tests/test_native_regression_repair.py` | 파일 자체가 HEAD에 없음 | T_C | 본 계획 CP2; CP1 선행 |
| `테스트소스.png` | untracked | F/보호 | 사용자 원본. hash 확인만; 모든 checkpoint payload에서 제외 | 추가 untracked 직접 import 없음 | 구현 의존성 아님 | 문서/보호 hash 검토 | 포함 금지 |
| `docs/UX2_CHECKPOINT_FILE_MANIFEST.md` | untracked (이번 추가) | F | 현재 감사/명시적 payload·격리 근거 | 기존 reports 및 candidate evidence | 파일 자체 HEAD에 없음 | 문서/hash 검토 | 문서 단독; 사용자 승인 별도 |
| `docs/UX2_FINAL_VERIFICATION_CHECKPOINT_PREPARATION.md` | untracked (이번 추가) | F | 현재 감사/명시적 payload·격리 근거 | 기존 reports 및 candidate evidence | 파일 자체 HEAD에 없음 | 문서/hash 검토 | 문서 단독; 사용자 승인 별도 |

## 명시적 candidate payload 목록

아래 목록은 `C:/Dev/pem_checkpoint_preparation_20261030_v2/candidates.json`과 같다. CP1의 partial3개는 전체 working file을 stage하면 안 된다.
검증 사본은 `.git` 없는 HEAD Git-object export + 누적 overlay다. 실제 commit/clone/branch/worktree가 아니며, source working tree는 수정하지 않았다.

### CP1 — UX2 UI + 필수 B 회귀

- `app/services/effect_group_service.py`
- `app/ui/canvas_widget.py`
- `app/ui/effect_library_panel.py`
- `app/ui/inspector_components.py`
- `app/ui/interactive_proxy_prewarm.py`
- `app/ui/layout_metrics.py`
- `app/ui/lifetime_point_editor.py`
- `app/ui/main_window.py` — partial content
- `app/ui/particle_inspector_workflow.py` — partial content
- `app/ui/particle_properties_panel.py`
- `tests/test_2_5d_inspector_architecture.py`
- `tests/test_editor_layout_polish.py`
- `tests/test_effect_inspector_responsive_layout.py`
- `tests/test_inspector_components.py`
- `tests/test_interactive_transform_proxy.py`
- `tests/test_particle_motion_gizmo.py`
- `tests/test_particle_sub_emitter_ui.py`
- `tests/test_particle_trail_ui.py`
- `tests/test_resource_layer_panel_clarity.py`
- `tests/test_v9_editor_lifecycle_integration.py`
- `tests/gizmo_sync_support.py`
- `tests/test_gizmo_inspector_sync_wait.py`
- `tests/test_gizmo_visual_overlay.py`
- `tests/test_inspector_visual_quality.py`
- `tests/test_lifecycle_prewarm_isolation.py`
- `tests/test_native_regression_repair.py` — partial content
- `tests/test_particle_inspector_workflow.py`
- `tools/audit_editor_ux.py`
- `tools/audit_particle_workflow.py`
- `tools/inspector_visual_probe.py`
- `tools/native_inspector_preview.py`
- `tools/probe_gizmo_sync.py`
- `tools/probe_lifecycle_isolation.py`
- `docs/UX2_PARTICLE_INSPECTOR_REPORT.md`
- `docs/UX2_NATIVE_GUI_CORRECTIONS_REPORT.md`
- `docs/UX2_GIZMO_SYNC_REPAIR_REPORT.md`
- `docs/UX2_LIFECYCLE_ISOLATION_REPORT.md`

### CP2 — FPS Playback

- `app/services/effect_resource_layer_render_service.py`
- `app/services/localization_service.py`
- `app/services/particle_preview_service.py`
- `app/services/particle_render_service.py`
- `app/ui/main_window.py`
- `app/ui/particle_inspector_workflow.py`
- `app/ui/resource_editor_v2/composition_inspector.py`
- `app/ui/resource_editor_v2/resource_editor_widget.py`
- `tests/test_native_regression_repair.py`
- `tests/test_fps_playback_semantics.py`
- `tools/rotation_regression_probe.py`
- `tools/native_regression_probe.py`
- `docs/TIMING_FPS_PLAYBACK_REPORT.md`
- `docs/UX2_NATIVE_REGRESSION_REPAIR_REPORT.md`

### CP3 — SpinBox contract

- `tests/test_native_spinbox_buttons.py`
- `tests/spinbox_repeat_support.py`
- `tests/test_spinbox_repeat_conditions.py`
- `tools/probe_spinbox_autorepeat.py`
- `docs/UI_SPINBOX_AUTOREPEAT_REPORT.md`

### CP4 — DevEx

- `tests/test_diagnostics_cli.py`
- `tools/diagnose_editor.py`
- `tools/diagnostics/__init__.py`
- `tools/diagnostics/process.py`
- `tools/diagnostics/registry.py`
- `tools/diagnostics/trace_adapter.py`
- `tools/diagnostics/worker.py`
- `docs/DEVEX1_DIAGNOSTICS.md`

### F — 별도 문서 검토

- `AGENTS.md`
- `docs/ROADMAP.md`
- `docs/UI_UX_PRINCIPLES.md`
- `docs/tasks/WORK_QUEUE.md`
- `docs/ASEPRITE_TIMING_TIMELINE_ARCHITECTURE_AUDIT.md`
- `docs/UX2_VERIFY_CHECKPOINT_REPORT.md`

보호 PNG는 어떤 목록에도 포함하지 않는다. 이번 새 감사 보고서와 이 manifest는 F에 추가되며 기존 사용자 파일과 구분해 검토한다.
기계 inventory에는 SHA256/정적 local imports가 있으며, 정적 분석만으로 Python 동적 import·메서드 API를 완전히 증명하지 않는다. 격리 tests/trace 실행이 이를 보완한다.
