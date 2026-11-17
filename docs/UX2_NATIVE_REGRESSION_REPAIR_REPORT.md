# UX-2 Native Regression Repair

## 1. 재현된 결함과 실제 원인

프로젝트 `C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker`, 검증 Python `C:\Dev\pixel_effect_test_venv\Scripts\python.exe`. 시작 full pytest는 **1824 passed / 163.59s**, 기존 cache ACL warning 1개. HEAD `ca9ed1c287022a653b96c2d75f81ea737b94d5f1`, staged 0, v0.0.25 / FORMAT 22였다. 기존 UX-2/Corrections 미커밋 변경을 보존했다.

| 문제 | 판정 | 근거 |
| --- | --- | --- |
| Resource → Effect 회전 | 해결 — 재현한 FPS/캐시/샘플 경로 | FPS 변경 뒤 stored/generated와 exact playback가 서로 다른 이미지를 사용했다. 프레임 수 변경 시 이전 짧은 base cache도 재사용했다. 별도로 11 FPS particle sampling의 부동소수점 직전 프레임 오류를 재현했다. |
| Lifetime PointEditor | 부분 해결 | 복합 editor의 동적 높이 전달·경계 이탈을 수정하고 native 폼 가독성을 확보했다. 다만 제공된 일반 조건만으로 사용자 설명의 list/form 중첩 자체는 수정 전에도 재현되지 않았다. 동적 큰 font+긴 오류 status의 경계 이탈은 red→green으로 확인했다. 원본과 동일한 모든 발생 조건이 확정되었다고 주장하지 않는다. |
| Group/Ungroup | 해결 | 선택 집합 변경 후 button state를 sync하지 않아 이전 단일 선택의 비활성 상태가 남았다. UI의 group eligibility도 실제 command의 root/인접/잠금 계약과 달랐다. |

회전·FPS 누락 경로는 HEAD 코드에서도 확인했다. UX-2에서 새로 도입된 shortest-angle 회귀가 아니다. Lifetime nested editor 또한 이전 작업에서 검사되지 않은 영역이었다. 기존 flags 0은 전체 화면 사용성 보증이 아니었다.

## 2. Resource → Effect 360° 회전 수정 및 결과

사용자 추가 단서: “1초에 12프레임짜리를 24프레임으로 늘리는 과정”. FPS 변경과 frame count 변경을 분리했다.

1. `MainWindow.set_fps` / 프로젝트 설정의 FPS 변경은 fps만 바꾸고 generated pixels를 다시 만들지 않았다. Playback는 새 FPS로 exact sampling하므로 일반 seek/PNG와 달랐다. 이제 FPS가 바뀌면 Resource Layer의 derived outputs를 재생성한다. 사용자 paint pixels와 Resource의 keyframe 위치/각도는 retime하지 않는다.
2. Single base cache key에 출력 길이가 빠져 12→24 frames 증가에도 12-frame 결과가 남았다. Single에만 project output extent를 포함했다. 활성 범위를 늘리지 않은 layer는 종료 뒤 투명해야 하며, 마지막 frame hold로 변하지 않는다.
3. Particle composition sampling의 `(age / effect_fps) * resource_fps`는 `15/11*11=14.999999999999998`이 되어 source14를 선택했다. 정수 단위 곱셈을 먼저 하도록 순서를 수정했다. 다른 imported animation clip의 millisecond duration 경로는 그대로다.
4. preview worker의 이전 FPS 결과가 되돌아오지 않도록 render context/session을 무효화한다. draft settings는 `preserve_drafts=True`로 보존한다.

합성 스프라이트는 방향 식별 가능한 빨강/청록 비대칭 모양이다. Resource12 FPS, 12-frame loop는 0..11에 0..330°를 저장한다. Effect24 FPS의 frame0/6/12/18은 source0/3/6/9, 즉 **0/90/180/270°**다. 360°는 다음 period의 source0과 동일하며 loop의 마지막 저장 프레임을 중복 360°로 바꾸지 않았다. Effect layer end23을 넘는 frame24는 layer 비활성/투명이다. 이와 별도로 61-frame fixture에서는 end60의 360°, 720°, -360° 키를 실제 저장하고 중간 및 끝 RGBA를 검증했다.

2x 재생처럼 90°가 Effect7.5프레임에 해당하면 정수 frame7은 source14(84°)를 선택하는 것이 맞다. 임의 angle 보간이나 프레임 보간을 새로 추가하지 않았다. 0.5x/2x sampling도 기존 discrete 계약으로 검사했다.

검증 경로: Resource / Current / Full / Generated / Exact Playback / PNG 디코드 RGBA. 0/25/50/75%와 endpoint, 동일·상이 FPS(11/22, 12/24), multi-turn/음수, Save/Reload, 기존 revolution/Undo/direct seek regression을 포함한다. Parent/Layer Space/Surface에 회전을 다시 더하거나 생략하는 수정은 하지 않았다. 기본 identity 외의 기존 2.5D/Keep World 회귀는 전체 suite로 확인한다.

프레임 증거: `C:\Dev\pem_rotation_repair_evidence\results.json` 및 각 PNG. FPS 변경 전 픽셀을 보존한 비교 이미지와 수정 전 red pytest를 구별한다. 새 timebase/ms-frame 모델 변경 없음.

## 3. Lifetime PointEditor 겹침 수정 및 결과

`LifetimePointEditor`는 QFormLayout의 spanning field이며 그 안에 VBox(list/form/buttons/status)가 있다. 이전 editor는 default layout constraint였고, 내부 form은 WrapLongRows였다. 동적 font/오류 문구로 intrinsic height가 변할 때 부모가 확보한 높이와 실제 label 영역이 달라져 status QLabel이 밖으로 나왔다.

root layout에 SetMinAndMaxSize를 사용해 실제 minimum/HFW를 전달하고, 내부 form은 label 위/editor 아래 WrapAllRows로 정리했다. 긴 label/status는 wrap하며 Preferred 크기 정책을 갖는다. 큰 고정 minimumHeight를 추가하지 않았다. 기존 목록 최대 높이 112는 그대로이며 포인트가 많으면 원래처럼 목록이 스크롤된다.

수정 과정에서 native 검사로 QForm label을 horizontal Ignored로 두면 폭0으로 사라지는 현상도 발견했다. 최종 정책은 Preferred이며 테스트에 모든 논리 control의 양수 크기 검사를 추가했다. native 창에서 라벨과 입력을 다시 확인했다.

이전 geometry 감사는 Trail/Events row와 native group title, wrap text 높이를 확인했지만 nested PointEditor의 list/내부 form/buttons 간 교차는 검사하지 않았다. 새 검사는 QWidget 구현 자식(SpinBox lineEdit 등)을 제외한 논리 control 전체를 mapToGlobal rect로 비교한다. 모든 pair의 수평·수직 교차, containment, 0 크기를 검사한다. 같은 x 또는 y만 가진 정상 행은 교차로 오판하지 않는다.

36개 조합: KO/EN × 280/320/360 × font100/125/150 × Fusion/windows11 style. 포인트2..8, Scale/RGB OFF/ON, category collapse/reopen, reveal, A→B→A, 동적 resize/font 및 긴 오류 문구를 포함한다. 추가 stress font200%도 사용했다. OS DPI 변경 자체의 검증은 아니다. native KO320/font150 창에서 scale/opacity/RGB를 스크롤해 직접 관찰했다. 색상 취소·endpoint·add/remove·easing·Undo/Redo 데이터 계약은 기존 테스트를 유지했다.

사용자 원본과 같은 중첩의 완전한 재현이 미확보이므로 **부분 해결**이다. 보통 조건에서 수정 전부터 overlap0이었던 사실을 숨기지 않는다. 정확한 남은 재현 screenshot/project 설정이 있으면 이 동일 검사로 이어갈 수 있다.

## 4. Group/Ungroup 수정 및 선택 조건

`currentItemChanged`가 `_sync_composition_controls`를 호출할 때는 아직 이전 domain selection이 남아 있었고, `set_resource_selection`은 signals를 차단한 채 UI를 갱신한 뒤 재계산하지 않았다. 이제 domain selection 반영 직후 명령 상태를 동기화한다. 선택 count와 current index를 구별한다.

UI와 command가 `effect_group_reasons`의 같은 read-only eligibility를 사용한다. 불가 이유는 KO/EN tooltip/status/accessibility에 제공한다.

| 선택 조건 | 만들기 / 해제 |
| --- | --- |
| 루트의 잠기지 않은 인접 leaf 2개 이상 | 만들기 가능 |
| leaf 하나 / 비인접 루트 | 개수 / draw-order 보존 이유로 불가 |
| 이미 그룹 소속인 멤버 / 다른 그룹 소속 | 기존 one-level 계약상 중첩/그룹 간 묶기 불가, 먼저 해제 안내 |
| 그룹 자체 선택 | 만들기 불가; 그룹 하나를 선택하면 해제 가능 |
| 그룹 또는 멤버가 잠김 | 구조 명령 불가; 잠금 해제 이유 표시 |
| 멤버만 선택해 Ungroup | 지원하지 않음, 그룹 헤더 선택 안내 |
| Visible/Solo | 그룹 생성의 금지 조건이 아님 |
| 서로 다른 transform Parent | group membership와 다르므로 루트 인접 leaf라면 가능; Parent/offset은 보존 |

Duplicate→단일 선택→Ctrl/Shift 다중 선택→생성 버튼, 그룹 선택→해제 버튼을 검증했다. 실제 QTest mouseClick(Ctrl/Shift) 두 케이스도 통과한다. Group/Ungroup은 기존 순서·root order·부모 transform/offset을 보존하고 Undo/Redo/Save/Reload/출력 parity를 검사한다. 기존 Resource Editor Group, Lock/Solo, Keep World/Parent 회귀도 전체 suite 대상이다. 이번 버튼 수정 대상은 Effect Editor의 Resource Layer 목록이며 새 nested grouping 기능이 아니다.

## 5. 신규 회귀 테스트와 실화면 근거

`tests/test_native_regression_repair.py`: 최종 64 cases. 12개 rotation golden, FPS12→24 UI 경로2, output extent1, speed2, Lifetime36, duplicate/group roundtrip1, eligibility8, 실제 modifier mouse2.

수정 전 증거: quarter RGBA2 fail, FPS 변경2 fail, group selection/button1 fail, 12→24 output cache1 fail, dynamic nested label containment1 fail. 모든 정상 Lifetime matrix가 이전부터 실패했다고 주장하지 않는다. native label 폭0도 수정 중 fail→pass를 별도로 확인했다.

이전 중간 전체 실행은 style를 QApplication 전체에 바꿔 unrelated surviving widgets까지 재스타일하는 시험 비용이 커 중단했다. 최종 matrix는 fixture subtree에만 style를 적용하고 deleteLater로 정리한다. 제품 코드를 우회하거나 assertions를 제거하지 않았다.

실제 Windows: isolated synthetic Lifetime 창의 읽기/scroll, Group 창의 만들기/해제 클릭, Ctrl+Z/Ctrl+Y를 관찰했다. 최초 선택2개는 fixture 설정이며 modifier mouse 자체를 native 수동으로 검증했다고 하지 않는다. Qt native widget grab PNG 및 JSON을 저장했다. 모든 파일은 C:\Dev의 새 출력 폴더에만 생성했고 사용자 콘텐츠는 쓰지 않았다. [비교 화면](C:/Dev/pem_native_repair_evidence/COMPARISON.md).

## 6. 전체 테스트/호환성

최종 전체 실행: **1888 passed, 1 warning / 177.57s**, exit0. basetemp `C:\Dev\pem_native_repair_all_verified`. 시작 1824개에 신규 64개가 추가됐다. 앞선 중간 전체 실행도 1884 passed / 170.47s였으며, 이후 추가한 mouse modifier/speed cases까지 최종 전체 재실행에 포함했다.

- compileall(app/tests/tools): exit0.
- app --version: v0.0.25. app --check / run_app.bat --check: exit0.
- git diff --check: exit0. LF→CRLF 안내는 기존 Git 설정의 warning이며 whitespace 오류는 없었다.
- FORMAT22 / keyframe 각도·revolution·데이터 스키마 유지. QML/새 기능/Contact/build/ZIP 미실행.
- pytest cache ACL warning은 기존 환경의 비치명 warning이며 권한/소유권을 변경하지 않았다. Git safe.directory는 각 호출/검증 프로세스에만 임시 지정했다.

## 7. Git 상태 및 남은 수동 QA

UX-2 및 Corrections와 함께 unstaged/uncommitted로 유지했다. add/reset/restore/checkout/clean, commit/tag/push/build/ZIP/PyInstaller 미실행. 사용자 `테스트소스.png`는 수정·삭제·이름 변경·stage하지 않았다. 종료 HEAD는 시작과 같은 `ca9ed1c287022a653b96c2d75f81ea737b94d5f1`, staged0이며 PNG SHA256은 `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`로 동일하다. 생성한 두 native 합성 QA 창도 종료했다.

남은 QA: 실제 사용자 자료에서 동일 Lifetime 중첩 조건 재확인, 서로 다른 OS DPI/다중 모니터/IME/native dark, 모든 parent/2.5D 조작의 수동 체감. 회전 fixture의 RGBA 정확성을 실제 사용자 원본과 동일 조건까지 확인한 것으로 확대하지 않는다. Resource FPS/프레임 수를 편집할 때 기존 키를 자동 retime하는 기능은 구현하지 않았다. FPS 변경은 시간당 샘플 수이며 frame count 증가는 길이 변경일 수 있다는 기존 의미를 유지한다.
