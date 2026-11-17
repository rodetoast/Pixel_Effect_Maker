# DevEx-1 Checkpoint & UX2-VERIFY

> 2026-10-30 Final Preparation: 현재 core175/4 checks PASS. 생산/테스트 source 변경 없이 직전 full1971 PASS/1 SKIP을 유지했다. 파일/hunk별 A~F 분류 및 HEAD-object 기반 순차 격리 후보를 검증했다(CP1 167 PASS, CP2 134 PASS, CP3 52 PASS, CP4 core175/CLI35 PASS+1 SKIP; D-only HEAD22 PASS). 따라서 DevEx는 선행 CP1/2/3 뒤 기술적 완결성이 검증됐지만 현재 HEAD에 독립적이거나 실제 commit된 것은 아니다. 사용자 원본 Lifetime 및 native 승인은 NOT VERIFIED로 UX2/DevEx checkpoint BLOCKED 유지. SpinBox 미확정 이력은 BACKLOG/P2 재발 시 조사로 보존. 상세: [최종 준비](UX2_FINAL_VERIFICATION_CHECKPOINT_PREPARATION.md), [명시적 파일 목록](UX2_CHECKPOINT_FILE_MANIFEST.md).

> 2026-10-30 SpinBox 후속: 생산 코드 변경 없이 완료 조건 기반 native 반복/Release 검증을 강화했다. UI90 PASS, 최종 full 정확히1회 **1971 passed/1 skipped/1 warning/193.11s**다. 다만 자연38회에서 과거92 실패는 재현하지 못했고 controlled900ms 사례만 확인했으므로 UI-SPINBOX-AUTOREPEAT는 직접 원인 미확정 NEXT/P1이다. 아래 과거 FAIL을 삭제하거나 원인 확정으로 덮지 않는다. 사용자 native 승인 및 DevEx 독립성 조건도 미충족으로 checkpoint BLOCKED 유지. [SpinBox 보고서](UI_SPINBOX_AUTOREPEAT_REPORT.md).

> 2026-10-30 FPS 후속: TIMING-FPS-PLAYBACK 범위의32 tests 및 UI78/Rotation49/Render23은 PASS다. 최신 full1회는1959 passed/1 failed/1 skipped/229.04s이며 별도 SpinBox press-hold에서92>=93이 실패했다. 단독PASS지만 원인 미확정으로 UI-SPINBOX-AUTOREPEAT P1 기록. Gizmo/lifecycle 수정 DONE은 유지한다. 사용자 native 승인·DevEx 독립성뿐 아니라 이 전체 실패도 남아 있으므로 checkpoint BLOCKED를 유지한다. [FPS 보고서](TIMING_FPS_PLAYBACK_REPORT.md).

> 2026-10-30 후속: UX2-LIFECYCLE-ISOLATION에서 닫힌 창의 idle prewarm 예약 정리 누락과 전역 통계 측정 경계를 수정했다. UI v3 78 PASS, 최종 full 정확히1회 **1928 passed / 1 skipped / 1 warning / 195.62s**, lifecycle·Gizmo 대상 모두 PASS다. 아래 과거 실패 이력을 지우지 않는다. 자동 전체 회귀 실패 조건은 해소됐지만 UX2-VERIFY/CHECKPOINT의 사용자 native 승인 및 DEVEX1-CHECKPOINT의 독립성 의존성은 여전히 미충족이다. 상세: [UX2_LIFECYCLE_ISOLATION_REPORT.md](UX2_LIFECYCLE_ISOLATION_REPORT.md).

> 2026-10-29 후속: 아래는 이전 checkpoint 시점의 이력이다. 기즈모 records=[]는 실제 timer callback 완료 전 assertion race로 재현·수정했다. 같은 선행102 tests 후 수정 대상24/24 및 UI74 PASS, 최종 전체의 기즈모 대상도 PASS다. 다만 전체는 별도 lifecycle render 통계 증가로 **1924 passed / 1 failed / 1 skipped**여서 UX2-VERIFY/CHECKPOINT는 계속 BLOCKED다. 사용자 native 승인과 DevEx 독립성 조건도 미충족이다. 상세: [UX2_GIZMO_SYNC_REPAIR_REPORT.md](UX2_GIZMO_SYNC_REPAIR_REPORT.md). 과거 실패 기록을 삭제하거나 전체 PASS로 대체하지 않는다.

## 1. Baseline 및 실제 Git 상태

2026-10-29. 프로젝트 `C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker`.
지정 Python `C:\Dev\pixel_effect_test_venv\Scripts\python.exe`.
시작 HEAD `ea8ff478c12a9b1032982476f84da62f4009d095`는 WORK_QUEUE 문서만의 커밋이었다.
v0.0.25 / FORMAT22 / staged0이며 기존 UX2·Corrections·Regression Repair·DevEx 구현이 미커밋인 상태를 확인했다.
직전 full1922 passed/1 skipped 이력과 실제 현재 Git 상태를 구분했다.
보호 PNG SHA256 `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564` 동일.

AGENTS/WORK_QUEUE/DEVEX1_DIAGNOSTICS/UX2_PARTICLE_INSPECTOR_REPORT/UX2_NATIVE_GUI_CORRECTIONS_REPORT,
UI_UX_PRINCIPLES와 registry 및 관련 테스트를 대조했다. 과거 문서의 native 합성 관찰은 이력일 뿐 이번 사용자 승인으로 취급하지 않았다.

## 2. DevEx-1 독립성 검증 / Checkpoint 결과

**독립 checkpoint: BLOCKED. stage/commit하지 않았다.** dirty tree PASS만으로 독립성을 주장하지 않는다.

DevEx 후보 파일은 다음11개다. 이번 작업에서 새 구현을 추가한 목록이 아니라 직전 DevEx 작업의 경계를 조사한 것이다.

- `AGENTS.md`
- `docs/DEVEX1_DIAGNOSTICS.md`
- `docs/ROADMAP.md`의 queue 링크2줄 (실제 diff 확인, 기존 계획 본문은 미변경)
- `docs/tasks/WORK_QUEUE.md` (문서 baseline은 이미 HEAD에 존재)
- `tests/test_diagnostics_cli.py`
- `tools/diagnose_editor.py`
- `tools/diagnostics/__init__.py`, `registry.py`, `process.py`, `trace_adapter.py`, `worker.py`

이 목록에 UX2-only 파일을 임의로 섞지 않았다. 현재 DevEx 파일들은 별도 파일/ROADMAP 링크로 경계를 식별할 수 있지만 **런타임·테스트 의존성은 분리되지 않았다**.

| 필수 의존성 | 실제 Git 상태 / 영향 |
| --- | --- |
| `tests/test_inspector_visual_quality.py` | untracked, HEAD에 없음; core ui가 참조 |
| `tests/test_native_regression_repair.py` | untracked, HEAD에 없음; ui/rotation/groups 및 DevEx integration test가 참조 |
| `tools/inspector_visual_probe.py` | untracked, HEAD에 없음; 위 테스트 fixture/geometry와 screenshot adapter가 import |
| `app/ui/particle_inspector_workflow.py` | untracked, HEAD에 없음; UX2 runtime layout/navigation |
| `app/services/effect_group_service.py` | untracked, HEAD에 없음; Group eligibility runtime |
| `tools/audit_particle_workflow.py` | untracked, HEAD에 없음; explicit legacy adapter 의존성 |
| `app/ui/main_window.py::_refresh_resource_timing_outputs` | HEAD에 없음; uncommitted FPS repair와 opt-in trace adapter가 사용 |
| `app/ui/particle_properties_panel.py`, `inspector_components.py`, `lifetime_point_editor.py`, `canvas_widget.py`, 관련 services/tests | tracked이지만 UX2/Repair 변경은 dirty; 현재 assertions의 동작 기반 |
| `tests/test_particle_trail.py`, `test_particle_sub_emitter.py`, `test_resource_layer_group_workflow.py` | HEAD에 이미 존재; 이것만으로 나머지 core 의존성이 충족되지 않음 |

### HEAD 기반 실행 증거

먼저 새 외부 경로의 일반 `git clone --local --no-hardlinks`를 시도했지만 Git/MSYS의 named-object 접근 오류(`0xC0000022`)로 실패했다. ACL/전역 설정을 바꾸지 않았다. 이를 clean Git clone 성공으로 기록하지 않는다.

대신 staged diff가 비어 **index=HEAD**임을 확인했다. `git checkout-index --all --prefix=C:/Dev/pem_devex_index_snapshot_ea8ff47_20261029/`로 추적 파일만 외부 새 디렉터리에 읽기 전용 export했다. 이 명령은 원래 working tree/index 내용을 되돌리지 않았으며 `git checkout --`를 사용하지 않았다. 위 DevEx 후보11개만 복사하고 UX2의 미추적 파일/dirty production은 복사하지 않았다. 이 사본은 `.git` 없는 HEAD 파일 snapshot이며 완전한 clone이라고 부르지 않는다. 필수 source/test 파일의 부재 자체도 `git cat-file -e HEAD:path`로 별도 확인했다.

| HEAD snapshot + DevEx 후보만 | 결과 |
| --- | --- |
| --list | exit0, registry 목록 출력 가능 |
| --check all: UI | ERROR, pytest exit4, tests0 |
| Rotation | ERROR, pytest exit4, tests0 |
| Groups | ERROR, pytest exit4, tests0 |
| Render | PASS |
| 최종 CLI | exit2; 1 PASS / 3 ERROR |

증거: `C:\Dev\pem_checkpoint_candidate_result\report.json`.
이는 checkpoint가 불완전함을 재현한 결과이지 현재 working tree의 UI 기능 FAIL을 뜻하지 않는다.

추가 발견(P2): 위 pytest exit4에서 JSON status/child_exit_code/pytest_exit_code는 보존되지만 `reason` 문자열이 비어 있었다. 미존재 node/파일의 읽기 쉬운 오류 설명 보완은 후속 `DEVEX-ERROR-REASON`으로 기록했고 이번에는 코드를 자동 수정하지 않았다.

### 안전한 분리안

권장: 사용자 native 승인 뒤 **UX2 runtime+회귀 tests+검사 helpers를 먼저** UX2-CHECKPOINT로 검토/커밋한다. 그 위에서 DevEx 후보11개를 따로 검증하고 `Add integrated editor diagnostics`로 커밋한다. UX2 테스트만 선행 커밋해도 runtime이 없으면 assertions/trace가 실패하므로 완결된 UX2 의존성 묶음이 필요하다.

대안: DevEx registry/fixtures를 HEAD만으로 실행 가능하게 별도 설계·분리하는 작업 승인을 받는다. 미존재 검사를 조용히 제거하거나 SKIP→PASS 처리해 독립성을 꾸미지 않는다. 이번 요청은 검증 단계이므로 이 재설계를 자동 시작하지 않았다.

## 3. 통합 진단 실행 및 결과

현재 working tree에서 지정 Python으로 다음을 실행했다.

```powershell
& 'C:\Dev\pixel_effect_test_venv\Scripts\python.exe' tools/diagnose_editor.py --list
& 'C:\Dev\pixel_effect_test_venv\Scripts\python.exe' tools/diagnose_editor.py --check all --output C:\Dev\pem_ux2_verify_20261029
```

| 범주 | 결과 / tests / 시간 |
| --- | --- |
| UI Layout | PASS / 73 / 26.48s |
| Rotation/FPS | PASS / 17 / 4.61s |
| Group/Undo | PASS / 13 / 3.52s |
| Render Parity | PASS / 23 / 2.17s |

**4 PASS / 126 cases / 0 FAIL·SKIP·ERROR / CLI exit0.**
JSON: `C:\Dev\pem_ux2_verify_20261029\report.json` 및 하위 범주별 result.json.
각 자식 exit0, pytest exit0, `cleanup=owned process tree closed`를 확인한다.
이미 통과한 범주의 동일 개별 명령은 불필요하게 재실행하지 않았다. trace 경로는 직전 `C:\Dev\pem_devex_trace_verified`의 기록과 현 코드·추가 DevEx focused tests를 참고했다.

core에 없는 pending numeric/view-only Undo/OFF preservation/warning discovery/gizmo paint/export는 기존 focused tests를 추가 실행했다.
`test_diagnostics_cli.py`, `test_gizmo_visual_overlay.py`, workflow의 document noop/A-B-A/OFF reveal/pending/warning cases, inspector의 pending collapse/accepted Undo cases:
**44 passed, 1 skipped, 1 warning / 9.22s**, `C:\Dev\pem_ux2_verify_focused`.
SKIP은 symlink 생성 권한, warning은 기존 pytest cache ACL이다. 제품 결함 FAIL이 아니다.

## 4. UX-2 PASS / FAIL / NOT VERIFIED

**판정: core126 자동 PASS / 전체 회귀1 FAIL(간헐) / 사용자 native NOT VERIFIED.** 전체 회귀 실패가 남았으므로 자동 검증 전체 완료나 승인 가능 상태로 선언하지 않는다. UX2 자체를 DONE이나 native 승인 완료로 바꾸지 않는다.

| 항목 | 자동 판정 / 근거 | 실사용 GUI 판정 |
| --- | --- | --- |
| Trail/Events/Lifetime list·label·editor·status·button geometry | PASS, 논리 컨트롤 교차/containment/양수 크기·섹션 전환 | NOT VERIFIED: 사용자 원본의 Lifetime 중첩 소멸 |
| KO/EN, 좁은 폭, 확대 font, summary/warning 구조 | PASS, 280/320/360·font100/125/150·palette/style matrix, warning 입구 | NOT VERIFIED: 실제 긴 한글 이름·OS DPI/멀티 모니터·고대비/IME 가독성 |
| Jump/Search, A→B→A, OFF 값 보존 | PASS, 기존 workflow assertions 및 core matrix | NOT VERIFIED: 사용자의 실제 작업 속도·탐색 체감 |
| 미확정 numeric·disclosure Undo | PASS, QTest pending text와 view noop, accepted Undo1/Redo | NOT VERIFIED: 실제 native IME/키보드/focus 조합 전체 |
| 12→24FPS, frame count/cache, 0/360/720/negative, source frame, all-path RGBA/reload | PASS, rotation17 | NOT VERIFIED: 실제 Resource→Effect360° 재생 결과 |
| Duplicate/multi-select/Group/Ungroup, adjacency/lock/Parent, Undo/Redo/reload | PASS, groups13 및 modifier QTest | NOT VERIFIED: 사용자 실제 Group/Ungroup 마우스 조작 |
| Trail/Sub-emitter repeat/seek/cache/PNG parity | PASS, render23 | NOT VERIFIED: 실제 제작 아트의 시각적 품질/속도 |
| Gizmo overlay interior/brush restore/hitbox·hide와 export RGBA 불변 | PASS, focused paint/export2 | NOT VERIFIED: 실제 아트 위 가림·핸들 조작감·zoom/DPI |
| Gizmo→Inspector changed-field sync / bounded layout 요청 | **FAIL**, 전체 실행에서 records가 비어 assert 실패; 별도3회는 PASS | NOT VERIFIED: 간헐 원인 및 실제 조작 영향 |

core4범주에는 FAIL이 없지만 전체 회귀에 기즈모 동기화 테스트 FAIL이 있다. 독립 checkpoint의 ERROR, 이 FAIL, 실사용 미확인을 구분하며 단독 재실행 PASS로 전체 실패를 지우지 않는다.

### 사용자 Native Manual QA 체크리스트

자동화가 사용자의 프로젝트·마우스·키보드를 다루지 않았다. 사용자가 평소 앱/자료에서 확인할 항목:

1. **Lifetime**: 이전 문제가 있던 원본에서 수명/외형을 열고 Scale/RGB OFF/ON, 2~8 points, scroll/선택 복귀를 수행한다. 목록/시간/값/보간/추가·삭제/오류 문구가 서로 가리지 않는지 확인한다. 가능하면 사용한 창 폭·배율·언어와 화면을 기록한다.
2. **Rotation**: Resource와 Effect의 FPS/프레임 수/loop/모드를 따로 기록한다. 12→24 변경 뒤 seek/playback/PNG를 Resource의 대응 source frame과 비교한다. Full Rotation의 12-frame loop는 보통0..330°이고 다음 loop가360°다. 수동으로 마지막 프레임에360°를 키했다면 중간 기대 각도는 그 track 평가값이다. 마지막 이미지 하나만으로 판정하지 않는다.
3. **Group**: 복제 후 단일 선택→Ctrl/Shift로2개 선택→만들기→그룹 헤더 선택→해제→Undo/Redo. 비인접·잠금에서는 이유가 맞는지 확인한다. Save/Reload는 사용자가 선택한 테스트 사본에서 수행한다.
4. **Gizmo**: 표시/숨김을 비교해 원본 검은 pixel과 overlay를 구별한다. scale/rotation drag와 zoom에서 내부가 불투명하게 채워지거나 작은 handle의 조작성이 나빠지지 않는지 확인한다.
5. **가독성/입력**: 실제 긴 한글 이름, OS125/150%·다중 모니터 이동, dropdown/status/warning, numeric Enter/Tab/focus-out과 한글 IME를 확인한다. offscreen font 확대와 실제 OS DPI는 다른 조건이다.

각 결과는 확인 조건과 함께 PASS/FAIL을 사용자 승인으로 남긴다. 현재 다섯 항목은 NOT VERIFIED다. 과거 합성 native 관찰은 실제 원본 확인의 대체물이 아니다.

## 5. Work Queue 갱신 및 다음 작업

DEVEX-1의 기존 구현 완료 이력은 유지하되 독립 checkpoint는 BLOCKED로 명시했다. 별도 DEVEX1-CHECKPOINT와 DEVEX-ERROR-REASON의 의존성/근거를 기록했다. UX2-VERIFY는 core PASS지만 전체 간헐 FAIL 조사·사용자 승인이 필요한 BLOCKED이며 UX2-GIZMO-SYNC를 P1로 추가했다. UX2-CHECKPOINT도 전체 회귀 실패 해소/승인 전 대기다. TIMING-1은 다음 기능 후보 NEXT이며 선행 조건은 그대로다.

**UX2-VERIFY(사용자 확인) → UX2-CHECKPOINT → TIMING-1** 순서를 유지한다. DevEx-only checkpoint는 승인된 UX2 의존성 commit 뒤 별도 검증한다. TIMING-2/ASE-IMPORT/TIMELINE-UX/UX-3/Contact/Ribbon/Force 등 기존 Backlog/우선순위를 삭제하거나 낮추지 않았다.

## 6. 최종 테스트 / Git / Window Use 사용 여부

최종 full pytest는 한 번 실행했다: **1 failed, 1921 passed, 1 skipped, 2 warnings / 193.18s**, exit1 (`C:\Dev\pem_ux2_checkpoint_full`). 실패는 `tests/test_interactive_transform_proxy.py::test_gizmo_updates_only_changed_inspector_field_without_layout`, line190의 `assert records ...`에서 **records=[]**였다. source에서는 transform inspector의 single-shot timer가33ms, test는 QTest.qWait40ms 뒤 callback 기록을 기대한다. 이 사실만으로 timeout이 유일한 원인이라고 단정할 수 없다. pointer/hit 전달, 타이머/이벤트 처리, suite 상태 등은 추가 조사가 필요하다.

우선순위 **P1 / UX2-GIZMO-SYNC**: 렌더 RGBA 손상은 확인되지 않았지만 기즈모→Inspector 갱신의 신뢰성 검증이므로 checkpoint 전에 원인을 좁혀야 한다. 과거 Native Corrections baseline에도 같은 test/records=[] 실패 이력이 있었고 이후 전체 실행은 통과했다. 이번에도 단독 fresh-process 재실행3회는 각각 PASS(0.80/0.73/0.72s)였다. `C:\Dev\pem_ux2_gizmo_isolated_1`~`_3`. 원인/해결을 확정하지 않았고 code/assertion/wait를 완화하지 않았다. 요청대로 광범위한 수정을 시작하지 않았다. 전체 pytest를 다시 돌려 실패를 덮지 않았다.

SKIP1은 계정의 symlink 생성 권한, warning2는 기존 pytest cache nodeids/lastfailed ACL이다. compileall, app --version(v0.0.25), app --check, run_app.bat --check, git diff --check는 exit0. FORMAT22 유지.

변경은 검증 문서/queue뿐이며 기존 production·tests·registry 코드를 수정하지 않았다. Stage/Commit/Tag/Push/Build/ZIP/PyInstaller 없음. HEAD `ea8ff478c12a9b1032982476f84da62f4009d095`, staged0, 보호 PNG hash는 위 기준과 동일하다.

Window Use **0회**. native 합성 창도 이번에는 새로 실행하지 않았다. 모든 Qt 동작은 private offscreen/QTest process 안에서 수행됐고 OS 마우스/키보드 입력을 주입하지 않았다. diagnostic Job Object cleanup 및 focused의 실제 descendant 종료 검사가 통과했다. 실패한 clone/export 작업도 명령이 종료됐고 시스템 권한이나 전역 Git 설정을 바꾸지 않았다. 외부 snapshot/보고서는 재현 증거로 C:\Dev에 남기며 기존 결과를 덮어쓰지 않았다.
