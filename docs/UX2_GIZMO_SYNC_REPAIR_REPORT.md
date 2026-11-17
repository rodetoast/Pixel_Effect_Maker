# UX2-GIZMO-SYNC — Flaky Regression Repair

## 1. 정확한 실패 원인

2026-10-29, v0.0.25 / FORMAT22, HEAD `ea8ff478c12a9b1032982476f84da62f4009d095`.
AGENTS/WORK_QUEUE, UX2 verification 및 DevEx 보고서/기존 tests를 읽고 기존 미커밋 변경을 보존했다.

**재현된 records=[]는 콜백 완료 전에 elapsed-time assertion을 실행한 테스트 동기화 race다.**
직접 계측한 실패에서는 transient transform 변경·신호·refresh 요청·타이머 예약이 모두 존재했다.
timer는 취소/재예약되지 않았고, assertion 순간 active/pending이며 remainingTime0이었다.
그 다음 이벤트 처리에서 정확한 rotation_y 콜백이 실행됐다. 신호 손실이나 domain 값 손상이 아니었다.

### 코드 경로

1. Canvas hit-test/start drag → `_set_resource_transform_interactive_value`가 transient transform을 변경한다.
2. Canvas `resource_transform_changed(..., final=False)`와 `resource_transform_changed_fields=(rotation_y,)`가 전달된다.
3. MainWindow는 transient layer를 만들고 `_pending_transform_inspector`에 panel/layer/frame/fields를 저장한다.
4. timer가 비활성이면33ms single-shot을 시작한다. 활성 timer를 포인터 이동마다 재시작하지 않는다.
5. Qt timeout → `_flush_transform_inspector_sync` → pending 해제 → `panel.set_transform_fields`.
6. 기존 테스트는20회 mouse move 후 `qWait40ms + processEvents1회`만으로 이 callback이 완료됐다고 가정했다.

Qt의 대기 시간 경과·remainingTime0은 Python timeout slot 실행 완료를 보장하지 않는다.
이벤트 처리 지연이 있는 조건에서 요청이 남아 있는데 assertion이 먼저 실행되는 것을 실제로 확인했다.
OS/Qt scheduler 내부의 특정 kernel primitive가 잘못됐다고 단정하지 않는다.

### 실제 관찰(지연 주입 없이)

`tools/probe_gizmo_sync.py`는 기존 fixture/QTest drag를 사용해 timer.start/stop, signal, fields/timeout,
legacy assertion 시점을 기록했다. 출력은 합성 상태·필드 이름·시각·bool/count뿐이다.

| 조건 | 결과 |
| --- | --- |
| fresh observation24회 | legacy records0:0 |
| 관련39 tests 선행 후24회 | legacy records0:0 |
| Inspector/components/visual/prewarm/proxy102 tests 선행 후24회 | **legacy records0:2** |

마지막 조건의 실제 두 실패(zero-based attempt5/14):

| 관찰 | attempt5 | attempt14 |
| --- | --- | --- |
| timer start(ms, 각 시도 시작 기준) | 6.016 | 5.973 |
| drag 변경 신호 | 19회, rotation_y | 19회, rotation_y |
| legacy assertion(ms) | 58.912 | 57.812 |
| assertion 당시 | records0, pending/active=true, remaining0 | 동일 |
| fields applied(ms) | 59.108 | 57.921 |
| assertion 뒤 추가 소요 | **0.196ms** | **0.109ms** |
| 결과 | rotation_y만 갱신, pending 해제 | 동일 |

증거: `C:\Dev\pem_gizmo_sync_inspector_order\observations.json`.
이 시도에서 타이머 start는1회, assertion 전 stop0회였고 callback이 실제 늦게 도착했다.
관찰 계측도 실행 시간을 소량 바꿀 수 있으므로 재현 빈도2/24를 실사용 통계로 일반화하지 않는다.
전체 pytest를 원인 탐색용으로 반복하지 않았다.

## 2. Production bug인지 test synchronization 문제인지

**이 재현 경로는 test synchronization 문제이며 production 수정은0이다.**
app/ui/main_window.py·Canvas·33ms interval·renderer를 이번에 변경하지 않았다.
드래그 중 authoritative document transform이 그대로인 것은 오류가 아니라 proxy/비파괴 설계다.
transient 값은 바뀌고 Inspector는 이를 표시하며 최종 release에서 document/Undo로 확정된다.

요구된 분류에서 이 실패는6번(callback 전에 assertion)이다. 1번(transform 무변경),
2번(신호 없음), 3번(timer 미예약), 4번(취소/재예약), 5번(callback 있지만 records0)은 관찰된 두 실패와 다르다.
취소(Escape)는 별도 테스트에서 pending/timer 정리와 success로 오판하지 않는 것을 검사했다.
기존 테스트는 실패 시 mouseRelease/close에 도달하지 못했으므로 finally cleanup도 추가했다.
새 helper는 상태를 관찰할 뿐 callback을 직접 실행하거나 missing signal을 합성하지 않는다.
과거 전체 실패에는 당시 단계별 로그가 없었지만, 같은 기존 assertion 실패를 수정 전 경로에서 직접 재현해 설명했다.
모든 가능한 UI/selection bug의 부재를 이 테스트 하나로 보증하지 않는다.

## 3. 수정 파일과 변경 내용

- `tests/test_interactive_transform_proxy.py`: fixed40ms를 제거하고 실제 completion predicate 대기(최대1000ms)로 바꿨다.
  timeout callback 관찰, 정확한 최신 rotation_y 값, pending 해제, timer 비활성을 모두 기다린다.
  기존 `records`, `all(names==(rotation_y,))`, `counter.count<=3` assertion은 그대로 유지했다.
  값 일치와 문서 비변경 assertion을 추가하고 finally에서 metadata 기록·signal disconnect·release·close한다.
- `tests/gizmo_sync_support.py`: test-only 관찰 helper. Qt Python binding에는 qWaitFor(predicate)가 없어
  QElapsedTimer deadline과 QTest의 event pump를 사용한다. 만족하면 즉시 반환하며1초를 무조건 자는 방식이 아니다.
  생산 타이머 시작/중단, 입력 신호, callback·실제 필드 갱신, 최신 값 일치 여부를 구별한다.
- `tests/test_gizmo_inspector_sync_wait.py`: 명시적 scheduling gate 뒤 원래33ms Qt 타이머를 시작하는 경우와
  실제 Escape 취소/timeout 분류를 추가했다. 임의40/90ms 차이에 의존하는 새 flaky assertion을 만들지 않았다.
  gate 해제 뒤에는 원래 Qt timeout/production slot만 실행하며 test가 flush 함수를 직접 호출하지 않는다.
- `tools/probe_gizmo_sync.py`: 1..30회 제한된 offscreen 계측 및 선행 관련 모듈/수정 test 재사용 모드.
- `tools/diagnostics/registry.py`: 원래 대상 pytest node를 **UI v2**에 등록했다. UI74 / core 전체127 cases가 된다.
  나머지 범주/버전은 유지하며 새로운 assertion 사본을 만들지 않았다.
- `tools/diagnostics/worker.py`: 해당 test가 record_property로 제공하는 **gizmo_sync의 고정 bool/count/stage만**
  observations에 넣는다. generic ERROR reason 동작은 변경하지 않았다(DEVEX-ERROR-REASON 범위 제외).
- `tests/test_diagnostics_cli.py`: 실패 report에서도 단계 metadata가 남고 arbitrary project/image/path payload는 제거되는지 추가 검사했다.
- docs/queue: 검증 근거·기존 상태/남은 native QA를 갱신했다.

실패 JSON의 stage는 transform_not_changed / signal_not_observed / refresh_not_scheduled /
timer_cancelled / awaiting_callback / callback_without_fields / field_value_mismatch / pending_refresh / complete다.
signal_count, refresh_requested, callback_count, field_refresh_count, fields_correct, value_matches,
pending/timer_active, layout_requests를 보고 입력·요청·실행·최종 결과를 구별할 수 있다.
사용자 id/프로젝트/이미지/전체 traceback locals는 수집하지 않는다.

## 4. 재현 전후 결과

수정 전: 위102-tests 선행 조건에서 legacy check2/24 실패. 두 경우 모두 추가 이벤트 처리로 실제 callback이 완료됐다.

수정 후: 같은102-tests 선행 실행 PASS 후 **수정된 대상 test 자체를24회 재사용하여24/24 complete**.
각 시도의 signals19/start1/stop0/callback1/field refresh1, fields_correct/value_matches=true,
pending=false, timer_active=false, document_changed=false를 확인했다.
`C:\Dev\pem_gizmo_sync_fixed_order\observations.json`.

완료 대기는 신호가 없거나 취소됐을 때 success가 되지 않는다. companion gate case는 callback 이전 records가 없음을 확인한 뒤
실제 timer를 시작하고 completion을 기다린다. Escape case는 timeout 내 false로 끝나고 cancel 상태를 남긴다.
대기 시간을 늘려 강제로 통과시키거나 SKIP/assertion 삭제로 숨기지 않았다.

## 5. 전체 테스트/진단 결과

- 최초 대상 module baseline:15 passed.
- 변경 후 대상+companion:3 passed.
- 관련 proxy/DevEx/companion 묶음:52 passed / 1 skipped.
- Inspector components·gizmo paint·DevEx·companion:68 passed / 1 skipped / 14.06s.
- 실제 `python tools/diagnose_editor.py --check ui --output C:\Dev\pem_gizmo_sync_ui_verified`:
  **PASS74, UI check_version2, exit0 / 29.30s**.
  JSON의 대상 observations는 complete, transient_changed=true, signal19, refresh_requested=true,
  starts1/stops0, callback1, field_refresh1, fields_correct/value_matches=true, pending/active=false,
  document_changed=false, layout_requests3이었다. `ui/result.json`으로 확인했다.
- 나머지 rotation/groups/render 생산·검사 경로는 바꾸지 않아 이번 단계에서 중복 실행하지 않았다.
  과거 --check all126 PASS 기록은 이력이며 현재127 전체를 이번에 실행했다고 주장하지 않는다.
- 마지막 full pytest는 변경 완료 후 **정확히1회**, `--basetemp=C:\Dev\pem_gizmo_sync_full_final --tb=short`:
  **1924 passed / 1 failed / 1 skipped / 2 warnings / 211.19s**, exit1. 기즈모 대상은 PASS.
  별도 `tests/test_v9_editor_lifecycle_integration.py::test_ui_navigation_state_does_not_dirty_project`가 실패했다.
  generation은0==0, spawn_cache_hits4080→4081, resource_cache_hits1052→1053,
  current_frame_renders20657→20658이었다. 이 test는 APP.processEvents 전후 전역 통계 불변을 검사한다.
  단독 fresh process는1 passed/0.85s(`C:\Dev\pem_gizmo_sync_lifecycle_check`).
  이 별도 실패의 원인은 미확정이며 이번 범위에서 수정하거나 전체 suite를 다시 돌리지 않았다.
  **기즈모 race 수정 완료와 전체 suite green은 다르다. 전체 검증은 여전히 FAIL이다.**
- compileall, app --version(v0.0.25), app --check, run_app.bat --check, git diff --check는 exit0.
  FORMAT22 유지. SKIP은 symlink 권한, warnings는 기존 pytest cache ACL이다.

## 6. Work Queue/Git/Window Use 상태

UX2-GIZMO-SYNC는 원인 재현·수정·대상 검증 근거로 DONE으로 갱신했다.
UX2-VERIFY·UX2-CHECKPOINT는 별도 lifecycle full FAIL 및 원본 GUI/사용자 승인 전까지 BLOCKED,
DEVEX1-CHECKPOINT도 미추적 의존성이 해결되기 전까지 BLOCKED다.
TIMING/ASE/Timeline/UX3/Effect Backlog와 우선순위를 보존한다.

Window Use0. 콘솔/offscreen/QTest만 사용했다. 각 실행은 종료했고 probe는 finally release/close,
진단은 소유한 process tree cleanup을 사용한다. 사용자 마우스·키보드·프로젝트를 점유/로드하지 않았다.
모든 변경은 unstaged/uncommitted로 남기며 add/reset/restore/clean/commit/tag/push/build를 실행하지 않는다.
종료 시 HEAD `ea8ff478c12a9b1032982476f84da62f4009d095`, staged0을 재확인했다.
보호 `테스트소스.png` SHA256은 `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`로 동일하다.
