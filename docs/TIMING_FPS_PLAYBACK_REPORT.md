# TIMING-FPS-PLAYBACK — Independent timebases and exact source playback

2026-10-30. Baseline HEAD `ea8ff478c12a9b1032982476f84da62f4009d095`, v0.0.25 / FORMAT22.
AGENTS/WORK_QUEUE, Timing Architecture Audit 및 Native Regression Repair 보고서를 읽었다.
기존 UX2/DevEx/Gizmo/lifecycle의 dirty 변경·보호 PNG를 보존했다.

## 1. 실제 의미와 호출 경로

- ResourceComposition.fps는 Resource의 시간축이다. frame_count와 rotation track의 key index는 별개다.
  새 FPS 입력은 Resource 정보 Inspector에 있으며 레이어 선택을 해제하면 보인다.
- Project.fps는 Effect 출력 시간축이다. 출력 FPS 변경은 Resource.fps나 source speed를 자동 변경하지 않는다.
  MainWindow.set_fps/apply_project_settings는 이전 수정대로 generated raster/preview context를 갱신한다.
- Particle의 clip_speed_min/max는 원본 배율이다. 각 instance가 seeded uniform speed를 선택한다.
  정확한2×에는 **Min=Max=2, Random Start OFF**가 필요하다. 이동 speed_min/max와 다른 값이다.
- Resource-as-clip은 composition_as_clip이 Resource frame을 생성하고 source_format=composition으로 표시한다.
  Particle `particle_clip_frame_index`: `floor(age * resource_fps / effect_fps * instance_speed) + start_offset`.
  이전 정수 곱셈 우선 순서를 유지했다. `age/effect_fps`부터 계산하는 회귀로 되돌리지 않았다.
- Single의 Current/Full은 effect_composition_layer_render_service에서
  `int((effect_frame-start_frame)*resource_fps/effect_fps)`를 사용한다. 양수 범위이므로 floor와 같다.
  Resource.loop면 modulo, 아니면 마지막 프레임 hold. Single start/end는 inclusive다.
- Particle source loop/hold는 composition_as_clip의 playback_mode로 전달된다. Random Start는 seeded source offset이다.
  Particle의 birth/lifetime/물리 계산은 기존 Effect frame 단위이며 source speed로 가속되지 않는다.

따라서 Resource12/Effect24/1×의 **1,1,2,2**는 코드상 의도된 초 단위 샘플링이다.
이를 무조건 frame-for-frame으로 바꾸면 기존 프로젝트가 두 배 빨라지므로 renderer 수학을 변경하지 않았다.

## 2. A/B/C 및 0.5× 검증

방향 식별 비대칭 RGBA sprite와12 Resource frames, track0..11=0..330°를 사용했다.
추가로0..660°/음수 회전과 기존 정확한360/720/-360° endpoint 회귀를 함께 검사했다.
아래 frame 번호는 사용자 기준1-based이며 renderer 내부는0-based다.

| 경우 | Resource FPS | Effect FPS | Source speed | Effect source 선택 | 원본12프레임 한 주기 |
| --- | --- | --- | --- | --- | --- |
| A: Resource 자체12→24 | 24 | 24 | 1× | 1,2,3,…,12 | 12/24 = **0.5초** |
| B: Effect 출력만12→24 | 12 | 24 | 1× | 1,1,2,2,…,12,12 | 24/24 = **1초** |
| C: 원본을2× | 12 | 24 | 2× | 1,2,3,…,12 | 12/24 = **0.5초** |
| 느린 원본 | 12 | 24 | 0.5× | 1,1,1,1,2,2,2,2,… | 48/24 = **2초** |

A의 Resource frame_count12·키 index/각도·모든12 RGBA는 동일했다. 자동 frame 삽입/삭제/복제나 key retime은0이다.
시간은 rational frame_count/FPS 및 source rate로 검증했다. OS 타이머 callback이 정확히 벽시계0.500000초에
실행된다는 의미는 아니다. Resource preview의 기존 round(1000/FPS) QTimer scheduler는 변경하지 않았다.

18 Particle 조합(speed3 × rotation3 × loop/hold2)의48개 출력 프레임 각각에서 실제
ParticleFrameDiagnostic.source_frame과 독립 Fraction 기반 기대 index를 대조했다.
Current / Full / Generated / Exact Playback / 역순 Direct Seek / 실제 Save-Reload / decoded PNG RGBA가 모두 일치했다.
Single의 B loop/hold도 전 프레임·같은 경로로 검증했다.

Loop에서 C의13번째 출력은 source1로 돌아오고, hold에서는 source12가 유지된다.
Single end47은 표시되고48은 투명하다. Particle fixture는 lifetime48/output48이므로48에서 소멸한다.
Source loop는 particle lifetime이나 출력 길이를 자동 늘리지 않는다. Particle은 현재 start/end 메타데이터가 아닌
settings의 birth/output/lifetime 경로를 사용하므로 Single의 end 규칙을 Particle에 새로 강제하지 않았다.
12출력만 필요하면 Effect 출력 길이/입자 출력·수명을12에 맞춰야 하며 speed2만으로 문서 길이가 줄지는 않는다.
PNG는 순번 이미지이며 FPS/시간 metadata가 없다. 위 길이대로 전달하려면 소비 측의24FPS 설정도 필요하다.

## 3. 발견한 실제 결함과 수정

### FPS 편집/설명 누락

Resource 정보는 FPS를 보여주기만 하고 기존 Resource의 FPS 입력을 제공하지 않았다.
CompositionInspector에 Resource FPS1..120과 명목 초 길이를 추가했다. 기존 composition_meta Undo command를 재사용하며
FPS 변경 때 Resource preview를 정지하고, touch/cache invalidation/composition_changed 경로로 모든 소비 출력이 갱신된다.
Undo/Redo에서도12프레임과 키를 유지하며 generated/current 결과가 이전/새 FPS와 일치했다.
Resource root 정보에 접근하려면 Resource layer 선택을 해제한다(clear_layer_selection 기존 동작).

Effect FPS tooltip은 출력 FPS임을 설명한다. Particle Source에는 KO/EN으로1×/2× 예시·Min=Max·Random Start 안내를
항상 읽을 수 있는 wrapping label로 추가했다. 입력 배율 값이나 기존 프로젝트를 자동으로 변경하지 않는다.

### 이전 FPS의 늦은 preview 결과 수락 (실제 red→green)

Resource composition 변경 시 기존 코드는 session 일부만 지웠고 draft revision은 그대로였다.
편집 전 FPS를 capture한 worker가 늦게 돌아오면 `_drain`의 context/draft revision 검사에 통과해 낡은 session을 설치했다.
`test_resource_fps_edit_rejects_old_preview_result_without_discarding_draft`에서 old-context/revision 결과를
FPS 변경 후 반환시키는 결정적 gate로 **수정 전1 FAIL**을 확인했다. wall-clock sleep이나 worker 속도에 의존하지 않았다.

ParticlePreviewManager.invalidate_resource는 해당 source를 참조하는 draft revision만 올리고 session·pending timer를 취소한다.
MainWindow.resource_composition_changed가 이를 호출하고 해당 active preview만 제거한다.
사용자 draft.settings/seed/is_dirty는 보존한다. 다른 리소스의 draft revision/session도 그대로 보존하는 테스트가 있다.
늦은 결과는 revision 불일치로 거부되고 새 요청은 새 revision/FPS를 사용한다.
renderer sampling, 물리, 캐시 key 형식, 파일 format은 변경하지 않았다.

## 4. Single 속도 기능의 명시적 보류

EffectResourceLayer의 playback_speed/resource_start_frame/playback_mode는 저장되지만 현재 Single adapter의
EffectCompositionLayer에는 전달되지 않는다. Single UI에도 source speed 입력이 없다.
이를 이번에 무조건 활성화하면 이미 저장된 nondefault 필드의 의미가 달라질 수 있으므로 활성화하지 않았다.
`TIMING-SINGLE-SOURCE-SPEED` P2에 versioned opt-in/기존 파일 보존/adapter·cache·Undo·schema 필요 여부 검토를 등록했다.
새 '출력 FPS에 맞춰 재생' 버튼도 암묵적 speed 변경 대신 후속 opt-in 설계 대상이다.
지금 가능한 방법은 **Resource FPS24**(공유 소비자에도 적용) 또는 **Particle Source speed2×**(그 레이어에만 적용)다.

Resource 안의 imported animated clip은 독립 ms timebase로 샘플링된다. 새 FPS 입력이 그런 source를 baked12-frame
이미지로 바꾸거나 자동 retime하는 기능은 아니다. A의 RGBA 보존 검증 대상은 frame-indexed 회전/정적 비대칭 source다.
Aseprite ms/frame persistent 모델·프레임 보간·Particle 물리 시간 변경은0이다.

## 5. 검증 결과

- 수정 전 baseline Rotation 진단:17 PASS/4.78s (`C:\Dev\pem_fps_baseline_rotation`).
- 신규 focused 최종32 PASS/6.38s (`C:\Dev\pem_fps_fixed`).
- Resource editor/기존 speed range·Undo/rotation/tooltip/DevEx/project settings 관련: **141 PASS / 1 SKIP / 26.47s**.
  별도 관련 명령의 미존재 test 파일 지정은 수집 전 exit1이었고, 올바른 파일 목록으로 정정했다. 테스트 FAIL로 혼동하지 않는다.
  초기 fixture도 실제 count 필드/refresh를 바로잡았으며 그 실패를 production defect의 red 증거로 사용하지 않았다.
- 최종 통합 진단: UI78 PASS/25.36s, Rotation v2 49 PASS/15.31s, Render23 PASS/2.22s, 총150 PASS,
  3 checks PASS/exit0 (`C:\Dev\pem_fps_diagnostics_final\report.json`), 소유 process tree cleanup 완료.
  registry 전체163 중 groups13은 이번 별도 진단에서 중복 실행하지 않았고 최종 pytest에는 포함된다.
- compileall, app --version(v0.0.25), app --check, run_app.bat --check: exit0.
- 최종 full pytest는 모든 수정/관련 진단 후 **정확히1회** 실행:
  **1959 passed / 1 failed / 1 skipped / 2 warnings / 229.04s**, exit1 (`C:\Dev\pem_fps_full_final`).
  새32 tests 및 Gizmo/lifecycle 대상 모두 PASS였다. 전체 검증이 green이라고 보고하지 않는다.
  별도 `test_native_spinbox_buttons.py::test_mouse_press_hold_uses_qt_native_auto_repeat`에서
  width91→mouse press/qWait800ms/release 뒤92, 기대>=93으로 FAIL했다. 이 test와 focus_wheel_widgets 구현은 이번에 수정하지 않았다.
  단독 fresh-process 확인은1 PASS/1.37s(`C:\Dev\pem_fps_spinbox_followup`)이며 원인은 미확정이다.
  UI-SPINBOX-AUTOREPEAT P1로 기록하고 이번 FPS 범위에서 수정/시간 완화하거나 전체 suite를 재실행하지 않았다.
  SKIP은 symlink 권한, warnings2는 기존 pytest cache ACL이다.
- git diff --check exit0. LF→CRLF 안내는 whitespace 오류가 아니다.

## 6. Git / Queue / Window Use

TIMING-FPS-PLAYBACK P1은 범위 내 구현/검증 근거로 DONE. Single opt-in은 별도 BACKLOG다.
기존 완료·BLOCKED 및 TIMING1/2/ASE/Timeline/UX3/Effect Backlog 유지. 전체 SpinBox1 FAIL은 별도 P1이며 전체 green은 아니다.
UX2-VERIFY/CHECKPOINT는 실제 사용자 native 승인, DEVEX1-CHECKPOINT는 기존 독립성 의존성 대기다.
Window Use0. 콘솔·Offscreen Qt·합성 RGBA만 사용했다. 실제 사용자 원본 프로젝트/이미지를 로드하지 않았다.
현재 변경은 기존 dirty 작업과 함께 unstaged/uncommitted로 남긴다. Commit/Tag/Push/Build/ZIP·stage·파괴적 Git 명령 없음.
보호 PNG SHA256 기준 `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`.
종료 시 동일 hash, HEAD `ea8ff478c12a9b1032982476f84da62f4009d095`, staged0을 확인했다.
