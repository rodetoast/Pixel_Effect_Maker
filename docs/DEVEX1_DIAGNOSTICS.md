# DevEx-1 — Integrated Diagnostics Foundation

> 2026-10-30 checkpoint 준비 후속: 현재 core175/4 checks PASS. 이전 HEAD+DevEx-only 3 ERROR 이력은 아래에 보존한다. 이번에는 UX2+B, FPS, SpinBox 선행 내용을 포함한 누적 격리 CP4에서 core175 PASS와 CLI35 PASS/1 SKIP을 확인했다. 실제 선행 commit/native 승인/명시적 Git 승인은 아직 없으므로 DEVEX1-CHECKPOINT는 BLOCKED다. [최종 준비 보고서](UX2_FINAL_VERIFICATION_CHECKPOINT_PREPARATION.md)와 [파일 manifest](UX2_CHECKPOINT_FILE_MANIFEST.md)를 기준으로 다음 승인 범위를 검토한다.

2026-10-29. 개발 대상은 콘솔 진단/작업 목록이며 Effect/UI 기능 변경이 아니다.

## 실행

프로젝트 루트에서 기존 테스트 Python을 사용한다. 예:

```powershell
& 'C:\Dev\pixel_effect_test_venv\Scripts\python.exe' tools/diagnose_editor.py --list
& 'C:\Dev\pixel_effect_test_venv\Scripts\python.exe' tools/diagnose_editor.py --check ui
& 'C:\Dev\pixel_effect_test_venv\Scripts\python.exe' tools/diagnose_editor.py --check rotation --trace
& 'C:\Dev\pixel_effect_test_venv\Scripts\python.exe' tools/diagnose_editor.py --check groups
& 'C:\Dev\pixel_effect_test_venv\Scripts\python.exe' tools/diagnose_editor.py --check render
& 'C:\Dev\pixel_effect_test_venv\Scripts\python.exe' tools/diagnose_editor.py --check all
```

의존성이 있는 Python이면 요청서의 `python tools/diagnose_editor.py ...` 형태도 동일하다. `--list`는 stdlib만 사용하며 Qt/pytest를 시작하지 않는다. 기본 실행(인자 없음)은 core all이다. `--check`는 반복 가능하고 중복 범주는 한 번만 실행한다. all과 개별 범주는 혼합하지 않는다.

`--output C:\Dev\new_unique_name`으로 **새** 외부 폴더를 지정할 수 있다. 생략하면 OS temp 아래의 고유 `pem-diagnostics-*` 디렉터리를 만든다. 기존 디렉터리·repo 내부·repo 조상은 거부한다. 경로 resolve로 symlink/junction의 실제 대상도 검사한다. 기존 보고서는 덮어쓰거나 정리하지 않는다. 콘솔 마지막 줄이 실제 JSON 위치다.

`--timeout 30`은 범주별 초 단위 제한이다. 기본 core180초, explicit legacy tool300초. 유한 양수만 허용한다. `--screenshots`는 UI 범주에 기존 `inspector_visual_probe`의 합성 offscreen 증거를 추가한다. 일반 진단은 screenshot을 남기지 않는다. parity 테스트에 필요한 작은 PNG는 private scratch에서 생성·디코드 비교 후 제거한다. `--trace`는 아래 제한된 metadata만 추가하며 프로젝트·RGBA·pytest locals를 저장하지 않는다.

## Registry와 재사용 범위

| 명령 | 기존 소유 로직 | 실행한 현재 case 수 / 범위 |
| --- | --- | --- |
| ui | `test_inspector_visual_quality.py`, Native Repair Lifetime geometry, Gizmo/lifecycle nodes, `test_lifecycle_prewarm_isolation.py`, 기존 native SpinBox hold node, `test_spinbox_repeat_conditions.py` | 90(UI v4); KO/EN, 폭/font/style matrix, disclosure/reveal/Jump/A-B-A, control geometry, Gizmo/lifecycle 완료, native repeat 초기+타이머2회·Release 취소·negative controls; OS 입력 QA나 과거 SpinBox 실패 원인 확정 아님 |
| rotation | Native Repair의 rotation/FPS/output extent/speed tests, `test_fps_playback_semantics.py` | 49(Rotation v2); 360/720/-360, 11/22·12/24 FPS, source speed0.5/1/2×, Resource FPS 편집·Undo, 정확한 source index, stale preview 거부, Current/Full/Generated/Playback/decoded PNG, direct seek/reload |
| groups | Native Repair selection/eligibility/history/mouse cases + Resource group workflow | 13; Duplicate, domain selection 대 current, root adjacency/lock/membership/Parent, Ctrl/Shift QTest, Group/Ungroup/Undo/Redo/reload |
| render | 기존 Trail/Sub-emitter의 selected parity/cache/seek/dependency tests | 23; 반복/random/reverse seek, historical appearance, Current/Full/Generated/PNG, cache invalidation |

`all`은 현재 **175개** core cases이며 전체 pytest 수천 개를 실행하지 않는다. 같은 assertion을 CLI에 복제하지 않았다. 향후 test parameter가 늘면 case 수는 달라질 수 있고 registry/check version과 문서를 갱신한다. default timeout이나 시간 측정은 성능 합격 기준이 아니다. 아래126 PASS 기록은 UI v1 시점의 이력이다.

명시적 legacy adapters(기본 all에서 제외):

```powershell
python tools/diagnose_editor.py --tool editor-inventory --output C:\Dev\new_inventory
python tools/diagnose_editor.py --tool particle-workflow --output C:\Dev\new_workflow
python tools/diagnose_editor.py --tool capabilities --output C:\Dev\new_capability_audit
```

`audit_editor_ux`의 logical-control metrics, `audit_particle_workflow`의 workflow inventory, `recheck_post_v25_capabilities`의 기존 전체 artifact tool을 그대로 실행한다. inventory는 **실행 성공**일 뿐 시각 품질/zero-overlap 승인으로 해석하지 않는다. JSON의 purpose/conditions/reason에도 이 경계를 기록한다. capability audit은 확대 렌더 자료를 생성하므로 명시적으로 선택해야 한다. 일반 core 진단에서 대규모 benchmark를 자동 호출하지 않는다. PERF-1은 별도 workload 승인과 기존 `tools/benchmark_particle_*` explicit 실행으로 분리한다.

## 결과와 종료 코드

콘솔은 범주별 PASS/FAIL/SKIP/ERROR와 소요 시간을 출력한다. `report.json`은 공통 envelope, 각 범주의 `result.json`은 같은 결과의 상세다.

| 필드 | 의미 |
| --- | --- |
| schema_version / check_version | common schema1, UI check4 / Rotation check2 / 나머지 check1 |
| app_version / format_version | 실제 import한 앱/저장 형식, 현재0.0.25/22 |
| started_utc / runtime | UTC 기계 시각, 실제 Python/OS/offscreen/Qt version, trace/screenshot/synthetic 조건 |
| checks[].name/title/conditions | 검사 ID·목적·재현 matrix |
| related_tests / tests[].test | 실행한 node IDs 및 parameter; 같은 pytest node로 독립 재현 가능 |
| status / reason | PASS/FAIL/SKIP/ERROR, 실패/필수 조건/실행 오류 구분 |
| duration_seconds / child_exit_code / pytest_exit_code | 관찰 시간과 원래 자식/pytest 코드 보존 |
| evidence | 실행 폴더 기준 파일 경로; 선택적 images에만 사용 |
| trace / failure_location | opt-in count/enum/bool metadata, 실패 stage와 test source/line |
| tests[].observations.gizmo_sync | test-owned 고정 bool/count/stage만 수집; transform 변경·refresh 요청·Qt callback·최종값/필드·layout 구분. 프로젝트/이미지 payload 제외 |
| summary / exit_code | 범주별 결과 집계와 CLI 코드 |

- 0: 선택 검사 모두 PASS.
- 1: 실제 assertion 검증 FAIL.
- 2: 실행/필수 의존성/timeout 오류, 혹은 필수 cases가 SKIP. SKIP은 PASS가 아니다. 여러 결과가 섞이면 ERROR/SKIP의2가 FAIL1보다 우선한다.
- argparse 오류/불안전 출력 폴더도2다. 실행 전 거부했거나 디스크 자체를 쓸 수 없으면 JSON이 없을 수 있다. 가능한 실행 오류는 run report에 남긴다.

실패 기본 보고서는 원본 payload 대신 test ID/재현 matrix/일반 원인을 제공한다. `--trace`는 failure stage/source/line을 더하지만 `longrepr`, locals, 임의 예외 문자열, 출력 RGBA를 저장하지 않는다. 상세 expected/actual이 필요하면 `related_tests`의 해당 합성 pytest node를 직접 실행해 콘솔에서 확인한다.

## 안전장치와 프로세스 수명

- 범주마다 별도 Python worker. `QT_QPA_PLATFORM=offscreen`, private APPDATA/LOCALAPPDATA/TEMP/XDG 및 QSettings test namespace; 사용자 앱·프로젝트·artwork를 열지 않는다.
- pytest 외부 plugin autoload, inherited PYTEST_ADDOPTS/PLUGINS를 제외한다. repo/cache ACL은 바꾸지 않는다. pytest cacheprovider를 core worker에서 끈다.
- Windows에서는 Job Object의 KILL_ON_JOB_CLOSE로 **해당 자식 tree만** 소유한다. worker는 Job에 들어간 뒤 ready barrier가 열려야 Qt/pytest를 시작한다. 실패·timeout·정상 exit 모두 남겨진 descendants를 정리한다. Job 할당이 불가능하면 unsafe fallback 대신 ERROR2다. POSIX는 전용 session/process group을 쓴다.
- stdout은 계속 drain하되 마지막64KiB까지만 메모리에 보관한다. raw child output은 디스크에 저장하지 않는다. trace에도 길이만 기록한다. raw worker intermediate는 redaction된 result로 대체한다.
- Qt top-level은 숨기고 deleteLater/DeferredDelete로 정리한다. unattended cleanup에서 closeEvent의 저장 확인 대화상자를 띄우지 않는다. 최종 process tree 종료가 남은 threads/windows의 경계다.
- scratch에는 합성 fixtures/PNG/settings만 생성하고 종료 시 제거한다. 외부 증거/보고서 폴더는 유지한다. 보호 PNG와 기존 미커밋 파일에는 쓰지 않는다.
- source/output/home 절대 경로를 trace에서 대체하고, arbitrary Windows path도 마스킹한다. report의 재현 node ID·상대 source path와 사용자가 선택한 output 위치는 필요한 범위다. 사용자 파일 내용/원본 이미지/serialized project를 포함하지 않는다.
- 시스템 ACL·소유권·Git 전역 설정 변경 없음. `safe.directory`는 child environment의 GIT_CONFIG_COUNT에 추가해 기존 per-process 항목도 보존한다.

Windows native 수동 조작은 이번 DevEx-1에서 **실행하지 않았다**. QTest의 click은 private offscreen process 안에서 Qt event를 전달하며 사용자의 마우스/키보드를 주입하지 않는다. offscreen windows11 style 통과가 OS DPI/native interaction 통과를 뜻하지 않는다. Lifetime의 실제 사용자 조건·다중 모니터·IME·dark/hit-test 체감은 UX2-VERIFY에 남긴다.

## 기존 logging 감사와 최소 추적 adapter

`app/services/runtime_diagnostics.py`는 기존에 bounded rotating UTF-8 log(기본2MiB×최대4 files), startup version, uncaught main/thread/Qt exception hooks, diagnostics text를 제공한다. safe_path_label은 filename만 남기지만 기존 log_exception은 예외 문자열/traceback을 기록할 수 있고 diagnostics text에는 log path가 있다. 이 기존 로그를 자동 수집·병합하지 않으며, DevEx 보고서를 앱 전체 로그의 완전한 개인정보 scrubber라고 주장하지 않는다.

이번에는 production instrumentation을 추가하지 않았다. `tools/diagnostics/trace_adapter.py`가 **trace를 요청한 private worker에서만** 관련 호출을 context patch하고 종료 시 복원한다. normal app 실행 overhead는0이다.

선택 수, Group/Ungroup accepted/rejected, Undo index, FPS/frame count, derived outputs invalidation, base cache hit/miss, preview session generation을 관찰한다. id/name/path/model/pixels를 기록하지 않는다. 최대2000 events, event 종류별100 records로 hot cache stream이 FPS/Undo를 밀어내지 않게 했고 마지막 trace_summary가 생략 수를 표시한다. 모든 frame/particle 이벤트를 production에서 상시 기록하지 않는다. 완전한 렌더 request graph와 앱 내부 보고서 UI는 DEVEX-2/후속 설계 범위다.

## 실제 실행 및 검증 기록

시작: HEAD `ca9ed1c287022a653b96c2d75f81ea737b94d5f1`, v0.0.25/FORMAT22, staged0. 최근 full1888을 기준으로 하고 불필요한 시작 full 재실행은 하지 않았다. Git 상태와 보호 PNG hash는 실제 재확인했다.

- `--list`: 4 core + 3 explicit adapters; 초기 CP949에서 em dash 출력 실패를 발견해 ASCII 안내로 수정했다.
- `--check ui --screenshots --output C:\Dev\pem_devex_ui_verified`: PASS73, 26.89s; optional7PNG 저장.
- `--check rotation --trace --output C:\Dev\pem_devex_trace_verified`: PASS17, 4.77s. FPS/derived/session/cache 이벤트 확인. 초기 trace quota가 cache만으로 소진되는 문제를 종류별 quota로 수정했다.
- `--check groups --output C:\Dev\pem_devex_groups_first`: PASS13, 3.52s.
- `--check render --output C:\Dev\pem_devex_render_verified`: PASS23, 2.27s.
- `--check all --output C:\Dev\pem_devex_all_verified`: **4 PASS, 0 FAIL/SKIP/ERROR**, 총126 cases; 범주25.50/4.75/3.58/2.17s. 전체 pytest가 아니다.
- `--check rotation --timeout 0.05 --output C:\Dev\pem_devex_timeout_verified`: ERROR2, timeout JSON 유지.
- 기존 `pem_devex_groups_first`에 재실행: 기존 폴더 거부2, 기존 보고서 보존.
- `--tool particle-workflow --output C:\Dev\pem_devex_workflow_adapter`: 정상 실행0; 관찰 tool이지 UI 품질 PASS는 아니다. editor-inventory/capabilities 전체 tool 실행은 이번 검증에서 하지 않았다.
- focused DevEx tests:34 passed / 1 skipped. symlink 생성 권한이 없는 환경이라 실제 symlink 생성 case만 SKIP이며, resolve/기존폴더/repo경계 검사는 실행했다. timeout과 정상 종료 후 실제 grandchild 종료도 검사했다.

최종 full pytest를 변경 완료 후 한 번 실행했다: **1922 passed, 1 skipped, 1 warning / 186.49s**, exit0 (`C:\Dev\pem_devex_full_verified`). SKIP은 실제 symlink 생성 권한, warning은 기존 pytest cache ACL이다. 전체를1923 PASS로 보고하지 않는다. compileall, app --version(v0.0.25), app --check, run_app.bat --check, git diff --check는 모두 exit0. FORMAT22 및 보호 PNG SHA256 `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564` 유지.

새 production bug를 발견·수정했다고 주장하지 않는다. 기존 UI/animation/group/render assertions는 전부 재사용했고 진단 기반 자체의 출력·trace 문제를 수정했다. git documentation checkpoint에는 WORK_QUEUE.md 하나만 허용하며 나머지 구현·테스트·기존 UX2는 미커밋으로 유지한다.

## 작업 대기열

[WORK_QUEUE](tasks/WORK_QUEUE.md)가 stable ID·상태·우선순위·목적·선행 조건·완료 조건·문서/테스트·수동 QA를 소유한다. [ROADMAP](ROADMAP.md)의 오래된 기준과 차이를 보존하며 양방향으로 연결했다. 새 최소 AGENTS.md는 queue 링크와 작업 규약만 안내한다. documentation-only checkpoint가 가능해도 기존 UX-2와 DevEx 구현을 함께 stage하지 않는다.

실제 local documentation checkpoint: **ea8ff47** — `Track deferred Pixel Effect Maker development tasks`. staged diff 전체와 파일 목록을 확인한 뒤 **docs/tasks/WORK_QUEUE.md 하나만** 커밋했다(48 lines). 시작 HEAD의 production source는 커밋에 포함되지 않았다. 종료 staged0이며 DevEx 구현/테스트/AGENTS/ROADMAP/이 문서와 기존 UX2 변경은 미커밋이다. Tag/Push/Build/PyInstaller/ZIP 없음.

후속 [Checkpoint / UX2-VERIFY 감사](UX2_VERIFY_CHECKPOINT_REPORT.md)에서 **DevEx 독립 checkpoint는 BLOCKED**임을 확인했다. 위126 PASS는 dirty working tree의 결과다. HEAD에는 UX2의 필수 회귀 tests/보조 모듈과 timing hook이 없으며, HEAD 파일 snapshot+DevEx 후보만의 실행은3 ERROR/1 PASS였다. UX2 의존성이 승인·추적되거나 별도 분리 작업이 끝나기 전에는 현재 DevEx 파일만으로 clean checkout 재현성을 주장하지 않는다.
