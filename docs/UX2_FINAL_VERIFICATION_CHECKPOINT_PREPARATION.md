# UX2 Final Verification & Safe Checkpoint Preparation

2026-10-30. **검증·분류·계획만 수행. Stage/Commit/Tag/Push/Build/ZIP 없음.**

## 1. Baseline / 보호 상태

- 실제 HEAD: `ea8ff478c12a9b1032982476f84da62f4009d095`, 시작 staged0.
- v0.0.25 / FORMAT22. 최신 전체 pytest는 직전 작업의 **1971 passed / 1 skipped / 1 warning / 193.11s**, exit0다.
- 시작 변경: **29 tracked modified + 39 untracked = 68 files**. 이 중53개 Python source/test/tool을 SHA256으로 고정했다.
- 보호 `테스트소스.png`는 untracked 사용자 파일이다. SHA256
  `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564` 일치. 검사 fixture/후보/커밋 목록에 포함하지 않았다.
- AGENTS/queue/UX 원칙/DevEx/Timing 및 최신 UX2·Gizmo·Lifecycle·FPS·SpinBox 보고서와 실제 diff/import를 대조했다.
- 이번 작업의 저장소 변경은 이 보고서·파일 manifest·queue·기존 검증 문서의 후속 주석뿐이다.
  기존53개 Python 변경 파일은 시작 hash와 모두 동일하다. 생산/테스트 코드 수정0이므로 전체 pytest를 불필요하게 반복하지 않았다.

외부 재현 자료: `C:\Dev\pem_checkpoint_preparation_20261030_v2`.
`baseline_inventory.json`은 시작 상태·파일 hash·local import/HEAD 부재 의존성을 보관하고,
`candidates.json`은 명시적 payload, `validation_results.json`은 관찰한 검증 결과다.
`import_origins.json`은 각 후보에서 app/tests/tools 모듈101~106개가 그 후보 폴더에서만 로드되며
원 작업 트리 fallback이0임을 확인한다. timing/D/E의 존재도 단계별 False→True로 검사했다.
v1 폴더는 중간 초안이며 **v2만 아래 후보 검증의 기준**이다.

## 2. UX-2 자동 검증 결과

먼저 실제 working tree에서 요청한 `tools/diagnose_editor.py --check all`을 실행했다.

| 범주 | 현재 registry | 결과 |
| --- | --- | --- |
| UI | v4,90 cases | PASS / 30.53s |
| Rotation / FPS | v2,49 cases | PASS / 12.61s |
| Group / Undo | v1,13 cases | PASS / 3.52s |
| Render parity | v1,23 cases | PASS / 2.11s |
| 합계 | 175 cases / 4 checks | 4 PASS, FAIL/SKIP/ERROR0, exit0 |

보고서: `C:\Dev\pem_checkpoint_final_all_20261030\report.json`.
모든 진단 child의 `cleanup=owned process tree closed`를 확인했다.

- Lifetime list/label/editor/status의 논리 교차·containment·양수 크기, Trail/Events 펼침·접힘,
  Search/Jump/reveal·A→B→A·OFF 보존·view-only 상태가 기존 matrix에 포함된다.
- Resource→Effect rotation/FPS/source speed0.5/1/2×, source index, key/프레임 보존,
  cache 무효화·stale preview 거부·Undo/Save/Reload/Direct Seek를 검사했다.
- Group/Ungroup eligibility와 modifier QTest/Undo, Gizmo→Inspector 완료·정확한 값·필드와 bounded layout,
  closed-window prewarm 정리, SpinBox native 반복·Release 취소/negative controls도 등록된 원래 node로 검사했다.
- Render/Full/Generated/Playback/decoded PNG parity 및 Trail/Sub-emitter historical/cyclic/seek 경로를 검사했다.

이것은 **합성 Offscreen 자동 검사 PASS**다. 실제 사용자 원본의 Lifetime 중첩 해결 확인이나 Windows 입력 체감 승인이 아니다.
SpinBox의 과거800ms/92 실패는 직접 원인 미확정이다. 이번 PASS가 그 사실을 삭제하지 않는다.

## 3. 사용자 Native QA 미확인 항목

**Window Use0. 이번에 사용자 원본 프로젝트·마우스·키보드를 조작하지 않았다.**
과거 보고서의 합성 native 관찰도 현재 사용자 승인으로 재해석하지 않는다.

| 사용자 확인 항목 | 권장 확인 조건 / 합격 기준 | 현재 |
| --- | --- | --- |
| 원본 Lifetime 중첩 | 문제 원본의 테스트 사본에서 수명/외형 열기, Scale/RGB OFF/ON,2..8 points, scroll·다른 선택 복귀. list/label/editor/button/status가 가리지 않아야 함 | **NOT VERIFIED** |
| Trail/Events 탐색 | 접기/펼치기, Search/Jump, OFF 상세 reveal 후 값/enable 보존과 다음 section 충돌 여부 | NOT VERIFIED |
| Rotation / FPS 의도 | Resource12 frames/12 FPS, Effect24 FPS·speed1×와2× 구별. 또는 Resource FPS24로 바꿔0.5초. 실제 seek/playback/PNG에서 대응 source frame 확인 | NOT VERIFIED |
| Group/Ungroup/Undo | 실제 mouse Ctrl/Shift 선택→인접 leaf group→header ungroup→Undo/Redo; locked/비인접 이유가 이해되는지 | NOT VERIFIED |
| Gizmo | 문제 아트에서 guide 표시/숨김 비교, zoom/DPI에서 scale/rotation drag, 검은 원본 pixel과 overlay 구분, Inspector 반영·조작감 | NOT VERIFIED |
| 입력·가독성 | SpinBox press/hold/release, Enter/Tab/focus-out·한글 IME, 긴 KO/EN 이름·좁은 폭, OS100/125/150%·다중 모니터·high contrast | NOT VERIFIED |

사용자가 PASS/FAIL, 사용 원본/모드/FPS·프레임 수·속도, 창 폭·OS 배율·언어, 날짜와 재현 단계를 남긴다.
필요한 화면은 사용자가 선택해 제공한다. 원본에 덮어 저장하지 말고 사용자가 정한 테스트 사본을 사용한다.
확인되지 않은 항목을 자동 PASS로 채우지 않으며, 실제 오류가 나오면 좁은 재현 test부터 추가하는 별도 수정 작업으로 전환한다.

## 4. Git 변경 분류와 의존성

**모든 파일별 tracked/untracked·목적·의존성·HEAD 부재·회귀·독립성은
[파일 manifest](UX2_CHECKPOINT_FILE_MANIFEST.md)에 명시했다.** 아래는 핵심 판단이다.

| 범주 | 포함되는 핵심 | 독립성 판단 |
| --- | --- | --- |
| A. Inspector/UI Corrections | workflow·InspectorSection/status/HFW·layout tokens·panel 연결·UI/geometry tests·합성 helpers | A/B가 canvas/library와 회귀 helpers에서 결합하므로 CP1 권장 |
| B. Gizmo/Lifetime/Group/Lifecycle | NoBrush/paint·Group service/command guards·Lifetime constraints·prewarm.close·동기화/종료 회귀 | CP1에 runtime+tests+helpers 동반. test 파일만 넣으면 안 됨 |
| C. FPS Playback | 정수 우선 sampling·output extent cache·FPS derived 재생성·source별 preview revision·Resource FPS 입력/설명·32 tests | 공유3파일은 hunk/내용 분리 후 CP2. CP1과 누적 검증 |
| D. SpinBox hardening | 기존 target 수정·repeat helper·controlled/negative tests·bounded probe | **HEAD+D만의 독립 snapshot22 PASS**. root-cause repair라고 commit 명칭을 붙이지 않음 |
| E. DevEx | CLI·registry/process/worker/trace·CLI tests·진단 문서 | 현재 registry는 A/B/C/D, trace는 C timing hook 의존. 이들 선행 후 CP4만 검증됨 |
| F. 문서/사용자 변경 | AGENTS/ROADMAP/UX 원칙/queue/Timing audit/검증 이력 및 보호 PNG | 문서는 별도 검토. 사용자 PNG는 절대 포함하지 않음 |

### 파일 단위로 나누면 깨지는 부분

1. `app/ui/main_window.py`: B의 Group guards/종료 정리와 C의 `set_fps`/설정 적용/
   `_refresh_resource_timing_outputs`/resource preview invalidation이 같은 파일에 있다.
2. 미추적 `app/ui/particle_inspector_workflow.py`: A 전체 구현 안에 C의 source speed help3줄이 섞였다.
   whole-file로 먼저 넣으면 HEAD에 없는 localization key를 읽으므로 C와 독립이라고 할 수 없다.
3. 미추적 `tests/test_native_regression_repair.py`: B의 Lifetime/Group과 C의 rotation fixture+4개 parameterized test 함수가 섞였다.
   CP1에서는 C 함수5개(도우미 포함)를 제외하고, CP2에서 추가하는 내용을 검증했다. assertions를 SKIP하지 않았다.
4. `tools/native_regression_probe.py`의 Group 모드는 위 rotation fixture를 import하므로 C 뒤로 미뤘다.
   B/C 혼합 보고서 `UX2_NATIVE_REGRESSION_REPAIR_REPORT.md`도 CP2 뒤에 전체 포함하는 편이 안전하다.
5. `effect_library_panel.py`는 A 명령 시각 교정과 B Group eligibility가 혼합된다. 이번에는 더 잘게 쪼개지 않고 CP1로 묶었다.

원래 checkout에는 분리 편집을 하지 않았다. 격리 사본의 AST 함수 경계와 정확히 일치하는 문자열을 사용해 CP1의 C 부분을 제외하고,
CP2에서 원래 현재 내용을 복원하는 누적 candidate를 만들었다.
`hunk_evidence/candidate_1_mixed_files.diff`, `candidate_2_mixed_files.diff`가 검토용 context다.
이것은 실제 index에 적용한 patch가 아니며 이후 승인 시 실제 diff/hunk와 hash를 다시 확인해야 한다.

### HEAD에 없는 필수 구현 / 이전 DevEx 실패와의 차이

`particle_inspector_workflow`, `effect_group_service`, Native/visual/workflow 회귀 tests,
`inspector_visual_probe`, Gizmo/SpinBox helpers, FPS test 모듈과 timing hook은 HEAD에 없다.
DevEx registry는 이 검사들의 node를 참조하며, worker screenshot 경로도 visual helper를 import한다.
trace adapter의 실제 Group integration test도 MainWindow의 C hook 존재를 필요로 한다.

이전 HEAD+DevEx-only 3 ERROR를 무의미하게 다시 실행하지 않았다. 이번에는 static import/registry graph로 누락을 먼저 찾고
runtime/test/helper를 선행 candidate에 포함한 뒤 실제 누적 snapshot에서 검증했다.
**DevEx가 기존 HEAD에 단독으로 독립적이라는 결론은 여전히 아니다.** 선행 candidate가 실제 commit되기 전까지 DEVEX1-CHECKPOINT는 BLOCKED다.

## 5. 권장 Checkpoint 순서 및 차단 요소

명시적 전체 파일 목록과 partial 표시: [manifest의 candidate payload](UX2_CHECKPOINT_FILE_MANIFEST.md).
다음은 실제 commit이 아니라 **`.git` 없는 Git HEAD-object export + 누적 overlay** 검증이다.
branch/worktree/clone/index를 생성·변경하거나 커밋을 만들지 않았다.

| 후보 / 권장 message | 선행 후보 | 반드시 동반할 검사·구현 | 격리 검증 |
| --- | --- | --- | --- |
| CP1 `Polish inspector workflow and stabilize editor interactions` | 현재 HEAD | A+B runtime, 미추적 Group/workflow, visual/Gizmo/Lifecycle tests와 helpers. manifest37 files 중3개 partial | focused **167 PASS/56.42s**, 전체 collection **1876 nodes/4.08s**, import error0 |
| CP2 `Clarify resource playback timebases and invalidate stale previews` | CP1 | C services/UI/localization, shared3파일 C 부분, Native rotation fixture/tests와 신규32 cases·도구·혼합 보고서. manifest14 files | **134 PASS/37.90s** |
| CP3 `Test native spinbox repeat completion and release cancellation` | 권장 순서는 CP2 뒤; 기술적으로 HEAD에 독립 가능 | D4 Python files+보고서. 원래>=93 및2 timer repeat·Release 계약 유지 | 누적 Numeric 묶음 **52 PASS/7.76s**; 별도 **HEAD+D22 PASS/4.96s** |
| CP4 `Add integrated editor diagnostics with isolated process cleanup` | **CP1+CP2+CP3** | CLI/diagnostics package/registry/trace/CLI tests+문서, manifest8 files | **core175 PASS/4 checks**, CLI **35 PASS/1 SKIP/6.08s**, 실제 Group trace·child cleanup 포함 |
| F `Document verified checkpoints and deferred timeline work` | 연관 내용 검토 후; 실제 실행 상태 반영 | AGENTS/ROADMAP/UX 원칙/Timing audit/queue/누적 검증 문서와 이번 보고서2개 | 문서/hashes/상태 consistency 검토. 사용자 PNG 제외 |

CP4 격리 보고서: `C:\Dev\pem_cp4_diagnostics_20261030\report.json`.
UI31.69s / Rotation11.98s / Groups3.59s / Render2.22s, 모두PASS·exit0.
CLI SKIP1은 계정의 symlink 생성 권한이다. SKIP을 PASS로 바꾸지 않았다.
CP4의 모든 변경 Python53개가 원래 작업 트리의 시작 bytes/hash와 일치함도 확인했다.
따라서 완결된 선행 내용 위에서 현재 DevEx가 import/실행되는 것은 증명했지만, 각 후보의 전체 pytest를 반복 실행한 것은 아니다.

### 실제 commit 전 남은 차단 요소

- UX2 원본 Lifetime 등 위 native 항목의 사용자 확인·승인.
- 위 파일/hunk 경계와 명칭에 대한 사용자 승인. 이 보고서는 승인 대체물이 아니다.
- CP1/2는 whole-file staging으로 분리되지 않는다. 검증 candidate와 동일 내용을 재검토해야 한다.
- 실제 선행 commit이 아직 없으므로 CP4를 먼저 stage/commit하면 이전 누락 문제가 재발한다.
- 문서의 역사적 PASS/FAIL은 보존하고 현재 상태를 후속 주석으로 명시한다. 자동 통과를 native 승인으로 쓰지 않는다.

source code 변경이 없어 직전1971 PASS를 유지한다. 실제 후보를 승인받아 Git으로 구성할 때에는 예상 predecessor/hash 확인,
candidate에 해당하는 검사, 최종 조합의 회귀 검증을 별도로 수행해야 한다. 이번에 그 실제 Git 작업을 수행한 것으로 보고하지 않는다.

## 6. WORK_QUEUE / 다음 TIMELINE-ARCH 착수 조건

- UX2-FINAL-PREP: 검증·분류·격리 후보 계획 준비 완료. **UX2-VERIFY/CHECKPOINT, DEVEX1-CHECKPOINT 자체는 BLOCKED 유지**.
- UI-SPINBOX-AUTOREPEAT: 테스트 보강·제품 결함 미재현·1971 PASS 및 이번90/175 진단을 근거로
  **BACKLOG/P2, 재발 시 재조사**로 낮춘다. 과거 직접 원인 미확정과 관찰 기록은 삭제하지 않는다.
- TIMELINE-ARCH는 다음 개발 후보(NEXT/P1)다. 기존 TIMING1/2, SINGLE-SOURCE-SPEED, ASE-IMPORT,
  TIMELINE-UX/CUSTOM-POC/MIGRATION, UI-DESIGN-SYSTEM 및 Effect Backlog는 그대로 유지한다.

착수 조건을 두 단계로 구분한다.

1. **읽기 전용 구조 감사**: 사용자가 이 준비 자료를 확인하고 별도 감사 착수를 승인한다.
   기준을 실제 승인 checkpoint 또는 현재 manifest/hash로 명시해 Resource/Effect의 paint/input/selection/commands/Undo/timebase 소유권을 조사한다.
   native QA가 아직이면 NOT VERIFIED를 유지한 채 읽기 전용 감사만 가능하며, UI/명령/시간 모델은 바꾸지 않는다.
2. **POC/마이그레이션 구현**: ARCH 결론과 별도 구현 범위·계약 승인, 합성 POC의 독립성 검증,
   production 연결 전 UX2 사용자 QA 및 실제 checkpoint 선행 조건을 충족해야 한다.
   Frame selection과 key/layer selection을 섞지 않고, 기존 clipboard·Undo·seek·FPS 계약을 보존한다.

이번에는 커스텀 timeline/새 기능을 구현하지 않았다. 모든 관련 검사 프로세스는 종료했고 Window Use0,
최종 staged0/HEAD·v0.0.25·FORMAT22·보호 PNG 불변 및 `git diff --check` exit0를 확인했다.
최종 Git 상태는29 tracked modified/41 untracked다. 시작 대비 새 repository 파일은 이 보고서와 manifest2개뿐이다.
`final_state.json`에 전체 status와53개 Python 불변 검증을 남겼다. 외부 C:\Dev 증거는 검토용으로 보존한다.
