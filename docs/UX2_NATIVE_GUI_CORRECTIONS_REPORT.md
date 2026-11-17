# UX-2 Native GUI Corrections & Visual Quality Pass

## 1. Baseline/Git 및 재현 조건

- 프로젝트: `C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker`. 기존 UX-2 변경 위에 누적했으며 이전 수정과 사용자 파일을 보존했다.
- 시작/종료 HEAD: `ca9ed1c287022a653b96c2d75f81ea737b94d5f1`, main ahead 46. staged 0. 버전 v0.0.25, FORMAT_VERSION 22 유지. 검증 Qt 6.11.1.
- Python: `C:\Dev\pixel_effect_test_venv\Scripts\python.exe`.
- 시작 full pytest는 1784 passed / 1 failed / 2 warnings(159.39s). 기존 `test_gizmo_updates_only_changed_inspector_field_without_layout`의 40ms 타이머 관찰에서 records가 비어 실패했다. 단독 재실행 및 이후 전체 실행은 통과했다. 시작부터 1785개가 모두 통과했다고 기록하지 않는다. 이 타이머 테스트의 동작 계약을 완화하지 않았다.
- 사용자 스크린샷 4장을 직접 확인했다. 별도 합성 프로젝트에서 Trail/Events, Source, Layer controls, 원본 검은 픽셀을 포함한 gizmo 화면을 재현했다. 사용자 프로젝트/이미지는 열거나 저장하지 않았다.
- Windows native 합성 Inspector: KO, 폭 420, Malgun Gothic 125% font. OS DPI 자체를 변경한 검증은 아니다. 자동 geometry는 KO/EN, 폭 280/320/360, font 100/125/150%, light/synthetic dark를 검사했다.

## 2. Screenshot 문제별 실제 원인과 수정

| 화면 | 판정 | 실제 원인과 수정 / 검증 경계 |
| --- | --- | --- |
| #1 복제와 삭제 사이 세로 요소 | 해결 | 실제 `QFrame.VLine` + Sunken 구분선이었다. 해당 divider를 제거하고 spacing으로 대체했다. 상태/순서 영역의 별도 구분선은 유지했다. Add primary / Duplicate secondary / Delete destructive / Lock·Solo toggle 역할을 부여했다. |
| #2 Source 제목·첫 필드 충돌, 긴 명칭, 파란 헤더, raw enum | 해결 | 하위 layout에 widget 전체 rect를 강제 지정해 native GroupBox 제목/contents inset을 무시했다. 강제 geometry 경로를 제거하고 Qt layout 제약에 맡겼다. 단일 열 label/editor, 짧은 최소·최대 속도/시작 무작위 이름, 부모 없음/한꺼번에/점 등 표시명을 적용했다. enum itemData는 불변이다. 속성과 명령은 작업 GroupBox로 분리했다. |
| #3 불투명 선택 사각형 | 부분 해결 | painter brush가 이전 marker/handle의 불투명 상태로 남은 채 scale/guide rect를 그려 내부까지 채웠다. NoBrush와 save/restore로 해결하고 선·핸들을 줄였다. paint/RGBA/export 테스트와 합성 화면은 통과했지만 해당 실제 사용자 아트에서 native drag/zoom 체감 검증은 남았다. 원본 검은 픽셀은 제거하지 않았다. |
| #4 Trail 입력·상태와 Events/Rendering 겹침 | 해결 | 수동 minimum-height 캐시와 부모 QWidgetItem의 오래된 HFW가 실제 펼친 높이와 달랐다. 예: Trail 실제 최소 251인데 부모 item HFW 70, 다음 Events가 Trail 내부 y에 배치됐다. 수동 pixel 높이 캐시를 없애고 살아 있는 HFW/constraints/updateGeometry를 사용한다. 같은 widget을 같은 부모 layout index에 재삽입해 layout-item 캐시를 갱신한다. editor/값/연결을 재생성하지 않는다. 정상 event loop의 화면 좌표 충돌 검사 및 제한된 native 접기/펼치기에서 재발하지 않았다. |

Label의 vertical Fixed 정책 및 wordWrap 뒤 sizePolicy 재설정도 HFW를 방해했다. Preferred와 올바른 설정 순서를 사용하고 summary/status를 wrap한다. Row spacing은 공통 token 6이며, 이것으로 높이 오류를 가린 것이 아니다. 섹션 높이는 내용과 폰트에 따라 계산한다.

기존 offscreen 검사가 놓친 이유: x bounds/minimum-height 중심이었고, 숨겨진 창의 descendant layout을 강제 activate해 실제 부모의 stale item cache를 우회했다. 새 검사는 창을 show하고 정상 event loop 뒤 mapToGlobal 기준 section/sibling/label/editor/status/GroupBox title을 검사한다.

Gizmo의 시각 반경 3(활성 5), outline 1.25와 hit radius 12를 분리했다. 논리 화면 좌표 token이며 zoom/DPR을 중복 곱하지 않는다. 기존 View의 편집 가이드 숨김으로 gizmo/guide/proxy 표시와 hit도 숨긴다. Renderer/data 경로는 바꾸지 않았다.

## 3. UI Design System 및 적용 변화

- Section header: native non-checkable auto-raise QToolButton과 arrow로 접기 상태를 표현한다. feature ON과 disclosure를 구별한다. 파란 전체 checked 채움을 제거했다. custom header QSS는 native 검사에서 접힌 Events의 검은 막대 및 font/palette 고정 문제가 보여 최종 코드에서 제거했다. native hover/focus/disabled와 상속 font/palette를 유지한다.
- Typography: label 위/editor 아래, 설명은 wrap, 짧은 KO/EN 표시명과 정확한 tooltip을 병행한다. 제목은 API/접근성에 원문을 유지하고 긴 EN 표시를 Transform/Lifetime/Events로 줄였다.
- Hierarchy: 값과 선택 대상을 우선하고 summary/info는 PlaceholderText, warning/error는 기존 semantic 상태를 유지한다. 동적 palette 변경에도 warning 색을 갱신한다.
- Commands: Add는 scoped primary token, Delete는 scoped danger token과 명시적 삭제 label/기존 disabled 이유를 유지한다. Duplicate·상태·순서·그룹의 기존 command 연결과 가능 조건은 그대로다. 앱 전체 reskin은 하지 않았다.
- Source Actions: 기존 Preview/Bake/Export/Revert 버튼 인스턴스와 접근 경로를 유지한다. 도움말과 검색 결과에서 선택 emitter의 Preview PNG와 전역 전체 Effect PNG를 구별한다. Undo와 파일 출력의 의미를 합치지 않는다.
- 공통 규칙은 `UI_UX_PRINCIPLES.md`, component는 `inspector_components.py`, token은 `layout_metrics.py`에 반영했다.

## 4. 최신 디자인 사례 비교와 적용 근거

공식 제품 문서와 커뮤니티 제안을 구별했다. 관련 자료를 조사해 패턴을 선택했으며 다른 도구의 UI를 그대로 이식하지 않았다.

| 참고한 패턴 / 근거 | 적용 여부 | 적용하지 않은 범위와 이유 |
| --- | --- | --- |
| [Blender 4.5 Properties](https://docs.blender.org/manual/en/4.5/editors/properties_editor.html), [4.5 UI release notes](https://developer.blender.org/docs/release_notes/4.5/user_interface/): context/search/tab visibility | 선택 대상 context와 기존 검색·Jump·reveal 유지, 섹션 위계 보정 | 별도 세로 tab 체계를 추가하지 않았다. 기존 8 workflow를 중복시킬 이유가 없다. |
| [Godot Inspector proposal #12270](https://github.com/godotengine/godot-proposals/issues/12270) (2025-04-18): 긴 Inspector scroll 부담 | 검색/reveal와 안정된 section navigation으로 대응 | proposal은 open 커뮤니티 제안이지 Godot core 확정 기능이 아니다. 새로운 top-level tab 구현은 하지 않았다. |
| [Inspector Tabs community addon](https://godotengine.org/asset-library/asset/3951) (2026-05-24), [editor style guide](https://contributing.godotengine.org/en/latest/development/engine/editor_style_guide.html) | tab 또는 jump-scroll 관점과 검색의 전체 문맥 유지를 참고 | addon 의존성/탭 전환을 도입하지 않았다. 기존 Jump와 검색으로 현재 범위를 충족한다. |
| [Aseprite 1.3.18](https://blog.aseprite.org/2026/07/22/aseprite-v1318/), [Timeline](https://www.aseprite.org/docs/timeline/), [Frame duration](https://www.aseprite.org/docs/frame-duration/) | 이미지 우선, 맥락별 command와 값/작업 구분, overlay 간섭 축소 | timing/ms/frame 모델은 이번 범위 밖이며 수정하지 않았다. 1.3.18은 2026-07-22 릴리즈이며 전체 최신판이라고 단정하지 않는다. |
| [Unity 6 Graph Toolkit window](https://docs.unity.com/en-us/engine/6000.6/manual/extending-the-editor/gtk-index/landing-graph-interface/graph-window): Canvas/Blackboard/Inspector/overlay 역할 분리 | 소스 입력과 출력 작업을 분리하고 canvas는 아트 우선 | Graph/Blackboard/node 편집기는 새 기능이므로 미도입. |
| [Qt 6 layout management](https://doc.qt.io/qt-6.8/layout.html), [QScrollArea](https://doc.qt.io/qt-6.8/qscrollarea.html): HFW/updateGeometry/dynamic constraints | native contents rect, HFW, 제약과 invalidation에 기반한 수정 | toolkit 이전/QML/고정 높이 workaround 미도입. 이번 관찰은 앱의 레이아웃 캐시 문제이며 Qt 자체 버그로 확정하지 않는다. |

## 5. Geometry/Visual/Interaction Tests

- 신규 `test_inspector_visual_quality.py`: 36개 조합(2언어×3폭×3font×2palette) + Source title/actions 1개. 각 조합에서 Linear/Helix, Trail OFF/ON, 접기/펼치기, Jump/검색 reveal, A→B→A, resize/font 갱신을 검사한다. document snapshot 불변, enum 값과 표시명 분리도 확인한다.
- 실제 화면 좌표로 sibling/section 수직 교차, label/editor/status 간 충돌, containment, native title/첫 필드, HFW를 확인한다. 최종 probe KO/EN/dark geometry issues는 모두 빈 목록이다.
- 신규 `test_gizmo_visual_overlay.py` 2개: 불투명 brush를 의도적으로 상속시킨 paint에서도 interior 불변, save/restore, 작은 visual과 12 hitbox 분리, hide 시 hit 불가, project/raw RGBA/export PNG 디코드 픽셀 불변을 검사한다. legacy/resource/guide 경로를 포함한다.
- 기존 Enter/Tab/focus-out/Ctrl-wheel/numeric commit/Undo/Auto-Key/Parent/Trail/Sub-emitter 등의 regression을 전체 실행에 포함했다. disclosure 자체는 view-only다. 실제 native IME/모든 입력 장치 검증과 자동 테스트는 구별한다.
- 최종 관련 focused suite: 90 passed / 23.41s. 신규 테스트는 총 39개다.
- 합성 before/after, KO/EN/dark, Source, gizmo 표시/숨김, Layer PNG를 직접 시각 검토했다. 최신 비교 문서: `C:\Dev\pem_ux2_native_corrections_evidence\COMPARISON.md`. 자동 geometry 수치만으로 시각 합격을 선언하지 않았다.
- 별도 실제 Windows 합성 창에서 Trail 및 Events 접기/펼치기 후 입력·상태·다음 section 배치를 관찰했다. 최종 native 비체크 헤더에서는 검은 막대가 사라지고 펼침 후에도 충돌이 없었다. QA 창은 종료했다. 저장한 비교 PNG들은 offscreen이며 native 캡처로 표시하지 않는다.

## 6. Full Regression/Compatibility

최종 코드 전체 실행: **1824 passed, 1 warning / 148.33s**, exit 0. basetemp `C:\Dev\pem_ux2_native_corrections_complete`.

| 확인 | 결과 |
| --- | --- |
| `python -m compileall -q app tests tools` | exit 0 |
| `python -m app.main --version` | Pixel Effect Maker v0.0.25, exit 0 |
| `python -m app.main --check` | exit 0 |
| `run_app.bat --check` (지정 Python override) | exit 0 |
| `git diff --check` | exit 0; 기존 LF→CRLF 안내만 존재 |
| staged files | 0 |

유일한 pytest warning은 기존 `.pytest_cache` 디렉터리 쓰기 ACL 거부다. 테스트 결과 실패가 아니며 권한/소유권을 변경하지 않았다. Git 소유권 경고는 호출/하위 테스트 프로세스의 임시 safe.directory 설정으로 처리했다. global Git 설정은 바꾸지 않았다.

App/FORMAT version, model enum, 저장·renderer semantics, timing, 기능 enable/bypass 의미는 유지했다. 새 particle feature/Collision/QML 이전 없음. renderer service/model 파일 수정 없이 editor overlay paint와 UI layout/표시/테스트를 변경했다. 사용자 아트/프로젝트를 변환하거나 저장하지 않았다.

## 7. Git 및 남은 Native Windows QA

- UX-2 전체를 **unstaged/uncommitted**로 유지했다. stage/commit/tag/push/build/release 미실행. HEAD 불변, staged 0. 기존 미커밋 파일을 삭제하거나 되돌리지 않았다.
- `테스트소스.png` SHA256은 `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`로 동일하다.
- 실제 native 검증은 합성 KO Inspector와 제한된 접기/펼치기다. 실제 사용자 프로젝트의 gizmo drag, Keep World/2.5D 체감, 모든 폭·언어·OS 100/125/150% DPI 및 다중 모니터 이동, native dark/high-contrast, IME, 파일/색상 대화상자의 수동 QA는 남았다. 자동 테스트 통과를 이 항목의 native 완료로 대체하지 않는다.
- 사용자 스크린샷 #3의 실제 아트·작업환경 확인은 부분 해결로 남기며, 나머지 세 화면의 수정 완료도 위 합성/native 관찰 범위 안에서의 판정이다. production 승인이나 체크포인트 생성을 뜻하지 않는다.
