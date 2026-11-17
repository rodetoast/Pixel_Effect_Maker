# UX2-LIFECYCLE-ISOLATION

2026-10-30 / v0.0.25 / FORMAT22. HEAD `ea8ff478c12a9b1032982476f84da62f4009d095`.
AGENTS/WORK_QUEUE 및 직전 Gizmo/DevEx 진단·checkpoint 보고서를 확인하고 기존 dirty 변경을 보존했다.

## 1. 재현 조건

전체 pytest 반복 대신 기존 합성 fixture로 QApplication을 공유하는 bounded probe를 사용했다.
`tools/probe_lifecycle_isolation.py`는 최대24회, 함수 이름으로만 된 호출 경로·현재 프로젝트 일치 bool·단계·통계 delta만 저장한다.
사용자 모델/이미지/절대 경로/locals를 JSON에 넣지 않는다. setup 렌더는 관찰 로그에서 제외한다.

| 수정 전 조건 | 결과 |
| --- | --- |
| fresh process, 기존 navigation 동작12회 | 12회 통계 변화0 |
| Gizmo proxy + Inspector components 44 tests 뒤 기존 동작12회 | 11회 통계 변화; 10회는 spawn hit/resource hit/current frame 정확히 +1/+1/+1 |
| 기존 lifecycle4 tests 뒤 기존 동작8회 | 7회 통계 변화; 4회 current frame +1도 관찰 |
| 선택한 창을 close하는 최소 회귀 test | pending prewarm이 남아 deterministic FAIL |

증거는 각각 `C:\Dev\pem_lifecycle_alone`, `C:\Dev\pem_lifecycle_gizmo_order`,
`C:\Dev\pem_lifecycle_lifecycle_order`의 observations.json 및 `C:\Dev\pem_lifecycle_close_before` 실행이다.
일부 snapshot이 cache 접근과 frame render 사이를 가르므로 cache hit만 먼저 증가한 시도도 있었다.
probe가 실행 시간을 바꿀 수 있어 이 빈도를 제품 발생률로 해석하지 않는다.
probe는 기존 test 동작을 관찰한 것이며 이전 전체 실패의 당시 로그가 있었던 것은 아니다.

## 2. Render/cache +1의 실제 경로

관찰된 +1의 스택은 `_PrewarmWorker.run → _run_guarded → render_effect_resource_layer_local_current_frame → render_layer_particles → render_particle_frame`이다.
**owner_current=false**: 현재 navigation 프로젝트가 아닌 다른 창의 idle prewarm이었다.
spawn state와 resource clip이 이미 있으므로 새 생성/miss는0, 두 cache hit와 current frame render만 각각1 증가했다.

`MainWindow.closeEvent`는 다른 renderer는 닫았지만 `interactive_proxy_prewarm`을 cancel하지 않았다.
QWidget.close는 자식 QObject/QTimer를 파괴하지 않는다. Python/Qt 참조가 남은 닫힌 창은80ms 타이머가 살아 있고
`_start`가 payload를 만들어 worker를 제출할 수 있었다. 이 worker는 전역 PARTICLE_RENDER_STATS를 갱신한다.
최소 상태 재현은 **합성 창 생성 → effect 선택 → prewarm pending 확인 → close → pending이 여전히 존재**다.
공유 QApplication에서 다음 창이 이벤트를 처리하면 이전 창의 작업도 실행된다.
QThreadPool.waitForDone은 아직 타이머에만 예약된 작업까지 기다리지 않는다. 원래 테스트는 반환값도 확인하지 않았다.

또한 현재 창의 최초 effect 선택 역시 의도된 idle proxy 준비를 예약한다. 이 정상적인 setup과 반복 navigation의
불필요한 재렌더를 같은 wall-clock snapshot으로 비교하면 경계가 불명확하다. worker completion event 자체가
추가 시뮬레이션을 요구한 것이 아니라 idle timer가 시작시킨 worker의 실제 render 진입을 관찰했다.

## 3. 판정

**두 문제가 결합했다: production의 closed-window prewarm 정리 누락 + 테스트의 전역 비동기 측정 경계 오류.**
관찰된 +1은 현재 navigation의 직접 렌더가 아니었다. Dirty0만으로 Render0을 대체하지 않는다.
모든 이전 테스트를 일일이 수정하거나 테스트 순서를 고정하지 않는다.
이 보고서는 특정 과거 전체 실행의 개별 창 이름을 확인했다고 주장하지 않는다.

## 4. 최소 수정

- `app/ui/interactive_proxy_prewarm.py`: close()에서 pending cancel/cancellation token 설정과 poll 중단.
- `app/ui/main_window.py`: 사용자 close 승인이 난 경로에서 prewarm.close(), Effect/Resource playback timer stop.
  거부된 close 경로는 바꾸지 않는다. 이미 실행 중인 renderer를 강제 종료하지 않으며 기존 revision/cancel 검사를 유지한다.
- `tests/test_v9_editor_lifecycle_integration.py`: 고정 sleep 대신2500ms deadline 내 실제 pending timer/active revision/
  thread-pool 완료를 기다린다. 먼저 이전 idle 작업을 정착시키고 첫 선택의 **동기 render0**를 검사한다.
  최초 선택의 정상 prewarm은 완료시켜 baseline에 포함한다. 초기 선택 역시 generation/document/Dirty 불변을 검사한다.
  이어 원래 Resource frame8/zoom/pan/Effect 선택을 수행하고 예약된 idle 작업까지 완료한 뒤
  **전체 render 통계 완전 동일**, generation 동일, Dirty0, project.to_dict 동일을 각각 검사한다.
  closed manager는 poll하지 않으므로 stale active revision 목록 대신 실제 pool 종료를 기다린다.
  finally에서 close/deleteLater로 실패 시에도 정리한다. 전역 통계를 reset하거나 +1을 허용하지 않는다.
- `tests/test_lifecycle_prewarm_isolation.py`: 닫기 취소 정리, due-at-next-dispatch 이전 창→기존 navigation node 재사용,
  불필요한 render 주입 시 기존 통계 assertion이 실패하는 negative control, 총3 tests.
- `tools/diagnostics/registry.py`: 기존 lifecycle node와 companion tests를 UI v3에 등록(UI78/core131).
  generic ERROR 설명/DEVEX-ERROR-REASON은 수정하지 않는다.
- bounded probe, 이 보고서, DevEx 문서 및 Work Queue 근거 갱신.

Renderer 수학·캐시 key·Direct Seek·Undo·파일 format은 변경하지 않았다.

## 5. 검증

- 수정 전 close 회귀:1 FAIL(pending retained).
- 수정 후 lifecycle+companion:7 PASS. 최초 선택 동기 render0 assertion 추가 뒤에도7 PASS/2.70s.
- Gizmo/Inspector/lifecycle48 tests 후 실제 수정 대상12회: **12/12 PASS** (`C:\Dev\pem_lifecycle_fixed_order`).
- 관련 prewarm/Gizmo/Inspector/DevEx/v9 parity 묶음: **109 passed / 1 skipped / 27.03s**.
- compileall app/tests/tools: exit0.
- UI v3 진단: **78 PASS/28.28s, exit0**, `C:\Dev\pem_lifecycle_ui_final\report.json`.
  기존 대상 node와3 companion이 각각 PASS이며 진단 worker의 소유 process tree cleanup도 완료했다.
  앞선78 PASS/26.66s 기록과 구분하며 현재 core131 전체 범주를 이번에 실행했다고 주장하지 않는다.
- 최종 전체 pytest는 UI 진단 뒤 **정확히1회**, `python -m pytest -q --basetemp=C:\Dev\pem_lifecycle_full_final --tb=short`:
  **1928 passed / 1 skipped / 1 warning / 195.62s**, exit0. lifecycle 대상과 기존 Gizmo sync 모두 PASS.
  SKIP은 계정의 symlink 생성 권한, warning은 기존 pytest cache nodeids ACL이다.
  전체 suite를 원인 탐색 또는 우연한 PASS를 위해 반복하지 않았다.

## 6. Git / Queue / Window Use

UX2-LIFECYCLE-ISOLATION P1을 별도 등록하고 재현/수정/검증 근거로 DONE 처리했다. UX2-GIZMO-SYNC DONE 및 모든 후속 Backlog를 보존한다.
UX2-VERIFY/CHECKPOINT는 사용자 native 승인 대기, DEVEX1-CHECKPOINT는 기존 미추적 의존성으로 BLOCKED 유지한다.
Window Use0. 합성 Offscreen Qt/콘솔만 사용하며 사용자 창·입력·프로젝트를 점유하지 않았다.
각 pytest/probe/진단 프로세스 종료 및 scoped Qt 창/worker 정리를 확인한다.
이번 변경은 unstaged/uncommitted이며 Commit/Tag/Push/Build/ZIP/add/reset/restore/checkout/clean 없음.
보호 PNG 기준 SHA256: `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`.
종료 시 위 hash 동일 및 HEAD `ea8ff478c12a9b1032982476f84da62f4009d095`/staged0을 재확인했다.
