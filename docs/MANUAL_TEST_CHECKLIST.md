# Pixel Effect Maker v0.0.04 수동 테스트 체크리스트

## Project Defaults & Effect Playback

- [ ] New Project를 열면 600×600, 12 FPS, 12 Frames이며 FPS를 24/30/60으로 바꾸면 Frames도 직접 편집 전까지 같은 값이 된다.
- [ ] Frames를 48로 직접 바꾼 뒤 FPS를 30으로 바꿔도 48 Frames가 유지되고, Dialog를 다시 열면 자동 1초 상태로 초기화된다.
- [ ] 빈 Resource는 300×300, Project FPS, 1초 Frame 수로 시작하고 수동 Frames 편집 뒤에는 FPS와 분리된다.
- [ ] 이미 생성한 Resource가 이후 Project FPS 변경에 따라 강제로 바뀌지 않는다.
- [ ] 600×600, 12 Frames에서 Effect Layer 1/3/5개와 Particle 0/50/100개를 재생해 UI가 입력을 장시간 막지 않는지 확인한다.
- [ ] 재생 시작 직후 아직 준비되지 않은 프레임에서는 최근 준비된 정확 프레임이 유지되고, 준비가 진행되면 자연스럽게 따라오는지 확인한다.
- [ ] 재생 중 Selection, Pan, Zoom 뒤 cache가 유지되고, Opacity/Visibility/Particle/2.5D 편집 시 재생이 정지하며 오래된 프레임이 남지 않는지 확인한다.
- [ ] 재생 프레임과 같은 위치의 Scrub, Bake, PNG Export를 눈으로 비교하고 Save/Load 뒤 프로젝트 픽셀이 바뀌지 않았는지 확인한다.

이 항목들은 실제 Windows GUI에서 아직 수행되지 않았으며 자동/오프스크린 검증과 구분한다.

## Early Preview Build 안내

- [ ] 새 QSettings 상태에서 일반 실행 시 Startup Dialog보다 먼저 안내창이 열린다.
- [ ] 명시적 `.peffect.json` 경로 실행도 프로젝트를 읽기 전에 안내창을 거친다.
- [ ] 종료, 창 닫기와 Escape는 Startup Dialog와 프로젝트 Load 없이 앱을 끝낸다.
- [ ] `확인하고 시작`과 Enter만 시작을 계속한다.
- [ ] `이 빌드에서는 다시 표시하지 않기`를 선택하면 같은 Notice Revision에서 자동 표시되지 않는다.
- [ ] 도움말의 `프로젝트 소개 및 개발 현황…`은 수락 상태와 관계없이 열리고 체크박스나 종료 버튼을 표시하지 않는다.
- [ ] 한국어·영어 전환 뒤 제목, 경고, 목적, 현재 기능, 향후 기능과 버튼이 함께 바뀐다.
- [ ] Windows DPI 100%/125%/150%와 작은 화면에서 세로 Scroll은 가능하고 가로 Scroll이나 잘림은 없다.
- [ ] 중요한 프로젝트 복사본 경고와 앱 v0.0.04, Project Format 8, Early Preview 채널이 표시된다.

## Particle Orbit & Helix Motion

- [ ] Point Spawn에서 Orbit, 반지름 100, 1회전으로 Clockwise/Counter-clockwise를 비교한다.
- [ ] Radius 100→0 수축과 Phase Spread 360의 전체 원 분산을 확인한다.
- [ ] Helix Z, X(YZ), Y(XZ) 축과 Local Perspective 0/증가 결과를 비교한다.
- [ ] Helix 뒤에 Resource Layer Rotation X/Y, Position Z, Perspective가 순서대로 적용되는지 확인한다.
- [ ] Center, Radius Start/End, Start Angle Shift 15°, Axis, Escape, Undo/Redo를 확인한다.
- [ ] Timeline Scrub, 정방향/역방향 Playback, Bake, PNG/Sequence Export 결과를 같은 프레임에서 비교한다.
- [ ] Motion 값 변경 직후 Save가 긴 Sequence 계산 없이 끝나고, 재시작·Load 뒤 metadata와 정확 출력이 유지되는지 확인한다.
- [ ] 여러 레이어에서 Motion 값을 연속 드래그할 때 다른 레이어가 매 입력마다 재합성되지 않고, Release 뒤 정확 출력으로 한 번 확정되는지 확인한다.
- [ ] 재생 헤드가 중간 프레임에 있을 때 Guide와 Helix Axis End가 해당 프레임의 실제 경로를 따라가는지 확인한다.
- [ ] Inspector 280/300/320px, Windows DPI 100/125/150%, 한국어/영어를 확인한다.

이 문서는 사용자가 실제 Windows GUI에서 확인할 항목입니다. 자동 테스트 또는 오프스크린 시작 점검이 통과했더라도 수동 확인 전에는 체크하지 않습니다.

## Resource Layer 2.5D Transform

- Effect Inspector를 280px, 300px, 320px로 조절하고 Single/Particle 양쪽에서 가로 Scroll이나 오른쪽 잘림이 없는지 확인
- 한국어↔영어 전환 및 Windows 100%/125%/150% DPI에서 2열 조작 버튼, 수치 입력, Path, Particle 설정과 세로 Scroll 확인
- Position X/Y/Z, Rotation X/Y/Z, Scale X/Y, Opacity, Pivot, Perspective, Ctrl+Wheel, Reset, 명시적 Keyframe을 한국어·영어에서 확인
- Single과 Particle Emission 각각 X/Y Tilt, Z Rotation, Position Z, Perspective, Content Guide, Preview/Bake/PNG/Sequence Export 확인
- Move XYZ, Rotate XYZ, Scale, Pivot, Shift 15° Snap, Escape, Undo/Redo, Pan/Zoom 및 Handle 겹침 확인
- 서로 다른 Z와 Animated Z의 앞뒤 순서, 같은 Z의 Timeline 순서 유지 확인
- 100%/125%/150% DPI, 극단 X/Y Rotation, 작은/큰 Canvas와 Tooltip 확인

## Resource v5

- [ ] PNG와 다중 프레임 GIF를 가져와 투명도와 frame duration이 유지된다.
- [ ] 일반·Clip Generated·Particle Layer 헤더로 독립 표시 전환이 된다.
- [ ] 숨긴 Layer가 Canvas, 저장, 다시 열기와 PNG Export에 반영된다.
- [ ] Aseprite 미설치 상태에서도 PNG/GIF와 앱 시작이 정상이다.

## Resource Editor Workspace

- [ ] Effect Editor와 Resource Editor를 전환하고 마지막 Workspace가 유효할 때 복원된다.
- [ ] PNG/GIF/ASE/ASEPRITE 및 혼합 다중 파일을 Explorer에서 드롭한다.
- [ ] 일부 파일 실패 시 성공 Resource는 목록과 Preview에 남는다.
- [ ] 정적 PNG와 서로 다른 duration의 GIF/Aseprite가 투명하게 표시·재생된다.
- [ ] Enter, Left/Right, `</>`가 Resource Preview/Timeline에서만 해당 Resource를 조작한다.
- [ ] Pivot Drag, 숫자 입력, 중앙 정렬과 Escape 취소가 Zoom 상태에서도 정확하다.
- [ ] Resource Reimport가 ID·이름·Pivot을 유지하며 실패 시 원본을 유지한다.
- [ ] 사용 중 Resource 삭제가 차단되고 미사용 Resource는 확인 후 삭제된다.
- [ ] 정적·GIF·Aseprite·Animated Resource로 Particle System을 만들고 Preview한다.
- [ ] External Tools에서 Browse, Auto Detect, Validate, Clear와 잘못된 경로 보존을 확인한다.
- [ ] 빈 상태에서는 Import 안내만 표시되고 Composition Timeline과 Inspector가 숨겨진다.
- [ ] Asset 선택 중에는 원본 Preview·Frame Strip·Reimport·리소스 생성만 표시된다.
- [ ] `이 에셋으로 리소스 만들기` 기본 이름과 크기가 원본 파일을 따른다.
- [ ] 만들기 직후 Resource와 Layer가 자동 선택되어 추가 선택 없이 편집할 수 있다.

## Resource Composition

- [ ] 이름 A, 캔버스 64×64, FPS 12, 길이 1초(12프레임), Loop On으로 새 Composition을 만든다.
- [ ] Composition 이름 변경 시 같은 이름이 있으면 안전한 이름이 제안된다.
- [ ] PNG, GIF, Aseprite를 각각 Layer로 추가하고 여러 Layer가 합성된다.
- [ ] Layer 표시 전환과 Start/End 범위가 Preview 및 저장 후 다시 열기에 반영된다.
- [ ] Layer Pivot을 숫자와 캔버스 Drag로 바꿔도 Imported Asset Pivot은 바뀌지 않는다.
- [ ] Composition 삭제는 확인을 요구하고 Particle에서 사용 중이면 차단된다.

## Composition Property와 Keyframe

- [ ] `+ 속성 추가`에서 `회전`과 `spin`으로 Rotation을 찾는다.
- [ ] Position, Rotation, Scale, Opacity만 검색 결과에 나타나고 중복 등록이 차단된다.
- [ ] 첫 프레임 0°, 마지막 프레임 360° 키프레임이 타임라인에 다이아몬드로 표시된다.
- [ ] Linear, Ease In, Ease Out, Ease In/Out의 중간 프레임 결과가 서로 다르다.
- [ ] 선택 프레임 키프레임 삭제 후 기본값 또는 인접 키프레임 평가로 복귀한다.
- [ ] `한 바퀴 회전 추가`로 전체 길이 0°→360° 회전이 즉시 만들어진다.

## Composition 기즈모와 재생

- [ ] Move, Rotate, Scale, Pivot을 확대 및 Pan 상태에서 조작한다.
- [ ] Transform 기즈모 사용 시 해당 속성과 현재 프레임 키프레임이 자동 등록된다.
- [ ] Shift Rotate가 15°에 맞고 Escape가 Drag 시작 전 값으로 복귀한다.
- [ ] Enter로 Composition만 재생·정지되고 12 FPS 간격으로 Canvas와 Timeline이 동기화된다.
- [ ] Loop Off는 마지막 프레임에서 멈추고 수동 프레임 이동은 재생을 정지한다.
- [ ] Rotate Handle 밖을 클릭해도 회전이 시작되지 않는다.
- [ ] 빈 Canvas를 클릭하면 Layer 선택이 해제되고 Timeline 선택도 일치한다.
- [ ] Move는 Layer 내부, Scale은 모서리, Pivot은 십자를 잡았을 때만 시작된다.

## Composition → Effect

- [ ] Particle Resource Picker의 Resource Compositions 그룹에서 A를 선택한다.
- [ ] 여러 Particle이 각자 Random Start와 Playback Speed를 반영해 A 내부 애니메이션을 재생한다.
- [ ] Composition Pivot이 Particle 배치 기준으로 사용된다.
- [ ] Particle Preview, Bake, PNG Preview Sequence Export가 모두 정상이다.
- [ ] 저장·다시 열기 후 Composition과 Particle 참조가 유지된다.
- [ ] Effect 12/24 FPS와 Composition 12/24 FPS 조합에서 실제 시간 속도가 유지된다.
- [ ] Playback Speed 0.5/2.0, Random Start, Loop와 Hold가 Composition에 반영된다.

## 우측 UI와 Wheel

- [ ] 창 너비를 줄여도 우측 입력의 오른쪽이 잘리지 않는다.
- [ ] 좌·중앙·우측 Splitter 폭을 조절할 수 있고 재실행 후 복원된다.
- [ ] 우측 Properties를 세로 스크롤할 수 있으며 불필요한 수평 스크롤이 없다.
- [ ] Hover 상태의 SpinBox, DoubleSpinBox, ComboBox는 Wheel로 값이 바뀌지 않는다.
- [ ] 입력을 클릭하거나 텍스트를 선택한 뒤에도 Wheel로 숫자 값이 바뀌지 않고 상위 패널만 스크롤된다.
- [ ] SpinBox Up/Down 첫 클릭·반복 클릭·길게 누르기와 키보드 Up/Down은 정상이다.
- [ ] 에셋 1개를 가져왔을 때 목록 Hover/선택 행도 정확히 1개만 존재한다.
- [ ] Position과 Scale Card에서 X/Y 입력, 보간, Keyframe과 삭제 버튼이 모두 보인다.
- [ ] Rotation과 Opacity Card가 세로 구조로 표시되고 가로 ScrollBar가 생기지 않는다.
- [ ] 1024×720, 1280×800, 1600×900의 한국어·영어 UI에서 Inspector가 잘리지 않는다.
- [ ] Timeline 높이를 Vertical Splitter로 조절할 수 있고 Asset Inspect 전환 시 상단 영역이 전체 높이를 사용한다.
- [ ] Horizontal/Vertical Splitter 위치가 재실행 후 복원되고 비정상 저장값은 안전하게 복구된다.
- [ ] 투명 여백이 큰 PNG의 초록 선택 경계가 불투명 픽셀 영역에 가까워진다.
- [ ] Windows DPI 100%, 125%, 150%에서 속성 Card와 Effect 사용 버튼 전체 문구가 보인다.

## Clip Generator 기즈모

- [ ] 시작/끝 상태의 Move, Rotate, Scale을 조절할 수 있다.
- [ ] Point, Line, Circle Distribution 핸들과 가이드가 표시된다.
- [ ] Properties 숫자와 기즈모가 양방향으로 동기화된다.
- [ ] Zoom 상태에서도 픽셀 좌표가 정확하고 Move가 정수 픽셀에 맞는다.
- [ ] Shift Rotate가 15°에 맞고 Escape가 현재 Drag를 취소한다.
- [ ] 기즈모 조작만으로 프로젝트 modified 상태가 되지 않는다.

## Legacy Animated Resource

- [ ] 서로 다른 Source 형태의 적용된 Clip Generator에서 Clip을 만든다.
- [ ] Generator를 다시 적용해도 기존 Clip이 자동 변경되지 않는다.
- [ ] 명시적 Clip 업데이트 후 이를 쓰는 Particle Preview가 무효화된다.
- [ ] 저장 후 다시 열어도 Clip 픽셀, FPS, Pivot, 재생 모드가 유지된다.

## Particle System

- [ ] Burst와 Over Time이 구분된다.
- [ ] Point, Line, Circle/Arc, Box 생성 범위가 올바르다.
- [ ] Fixed Direction과 Radial Outward가 구분된다.
- [ ] Count, Spread, Speed, Lifetime, Scale, Rotation, Angular Velocity 범위가 반영된다.
- [ ] Clip Loop/Hold/Once, Clip Speed, Random Start Frame이 반영된다.
- [ ] 같은 Seed는 같은 결과이고 시드 무작위 변경 후 결과가 달라진다.
- [ ] Live Preview가 재생되며 Enter와 프레임 이동 키가 작동한다.
- [ ] Bake 후 다른 일반/Generator/Particle 레이어가 유지된다.
- [ ] Bake 없이 Preview Sequence가 투명 PNG로 번호 순서대로 출력된다.
- [ ] 형식 5 프로젝트를 다시 열어 Particle 설정과 결과가 유지된다.

## Effect Timeline과 직접 조작

- [ ] 눈 아이콘은 표시만 전환하고 레이어 이름 클릭은 선택만 변경한다. 숨긴 레이어도 선택 가능하다.
- [ ] Visibility Undo/Redo 후 아이콘과 Show/Hide Tooltip이 즉시 바뀐다.
- [ ] Resource Editor의 `이펙트에 추가…`에서 컴포지션 레이어와 파티클 시스템을 각각 만든다. 취소하면 모델이 바뀌지 않는다.
- [ ] 컴포지션 레이어 Start/End를 드래그하면 Inspector가 즉시 바뀌고 Undo 한 번으로 전체 Drag가 취소된다.
- [ ] 파티클 시스템 Origin/Direction/Expected End와 Line/Circle/Box Handle을 조작한다.
- [ ] Shift Direction이 15°에 맞고 Escape가 시작값으로 돌아오며 Undo 항목을 만들지 않는다.
- [ ] Preview 정지 상태에서 Path, Spread, Spawn Shape와 최대 세 개 Ghost가 보인다.
- [ ] `편집 가이드 표시`를 끄고 다시 실행해 설정이 유지되는지 확인한다.
- [ ] Guide가 Bake, PNG Preview Sequence와 일반 Export 결과에 포함되지 않는다.
- [ ] 100%/125%/150% DPI와 Canvas Zoom에서 Handle 크기, Hover Cursor와 Pan/Zoom 충돌을 확인한다.

## 실행

- [ ] `run_app.bat`으로 실행된다.
- [ ] 메인 창 제목에 `v0.0.04`가 표시된다.
- [ ] `--check`가 정상 종료된다.
- [ ] `--version`이 `Pixel Effect Maker v0.0.04`를 출력한다.

## 프로젝트

- [ ] 새 프로젝트 설정이 이름·크기·FPS·반복 재생을 포함한 하나의 창에 표시된다.
- [ ] 새 프로젝트를 만들 수 있다.
- [ ] 지정한 캔버스 크기가 올바르게 적용된다.
- [ ] 이름 앞뒤 공백이 제거되고 빈 이름으로 생성할 수 없다.
- [ ] 캔버스 프리셋 선택 시 너비와 높이가 함께 변경된다.
- [ ] 직접 크기를 입력하면 `Custom`으로 전환되고 입력값이 유지된다.
- [ ] 캔버스 `1–1024`, FPS `1–120` 제한이 적용된다.
- [ ] FPS와 반복 재생 설정이 새 프로젝트에 반영된다.
- [ ] 새 프로젝트 대화상자를 취소하면 기존 프로젝트가 유지된다.
- [ ] 프로젝트를 저장할 수 있다.
- [ ] 저장한 프로젝트를 다시 열 수 있다.
- [ ] 미저장 변경 상태에서 종료 경고가 표시된다.

## 레이어

- [ ] 별도의 중복 레이어 패널이 기본 화면에 표시되지 않는다.
- [ ] 통합 타임라인만으로 레이어를 선택하고 추가·삭제할 수 있다.
- [ ] `Shift+N`을 한 번 누르면 새 레이어가 정확히 하나 추가된다.
- [ ] 레이어를 추가할 수 있다.
- [ ] 레이어를 삭제할 수 있다.
- [ ] 마지막 레이어 삭제 시 프로그램이 비정상 종료하지 않고 안내한다.
- [ ] 선택 레이어가 정상적으로 갱신된다.

## 프레임

- [ ] 프레임을 추가할 수 있다.
- [ ] 프레임을 복제할 수 있다.
- [ ] 같은 프레임을 반복 복제해도 `Copy` 문구가 표시되지 않는다.
- [ ] 복제본이 선택한 원본 바로 다음 위치에 삽입된다.
- [ ] 추가·복제·삭제 후 프레임 번호가 `1, 2, 3…`으로 연속 표시된다.
- [ ] 복제본 픽셀을 수정했을 때 원본 픽셀이 함께 변경되지 않는다.
- [ ] `Alt+N`을 한 번 누르면 현재 프레임의 복제본이 정확히 하나 생성된다.
- [ ] `Alt+B`를 한 번 누르면 현재 프레임 다음에 빈 프레임이 생성된다.
- [ ] 프레임을 삭제할 수 있다.
- [ ] 마지막 프레임 삭제 시 프로그램이 비정상 종료하지 않고 안내한다.
- [ ] 프레임 선택이 캔버스에 반영된다.

## 재생

- [ ] 재생과 정지가 가능하다.
- [ ] FPS 변경이 적용된다.
- [ ] 재생 중 프레임이 정상 순환한다.
- [ ] 재생 정지 후 현재 프레임 상태가 정상이다.
- [ ] 재생 상태 문구가 Playing/Stopped, 현재/전체 프레임, FPS를 표시한다.
- [ ] 현재 프레임 번호와 강조 열이 재생에 따라 이동한다.
- [ ] 모든 프레임이 투명해도 재생 여부를 확인할 수 있다.

## 캔버스

- [ ] 투명 체커보드가 표시된다.
- [ ] 마우스 휠로 확대와 축소가 가능하다.
- [ ] 확대 시 픽셀이 흐려지지 않는다.
- [ ] 최소 및 최대 확대 제한이 적용된다.

## 통합 타임라인

- [ ] 세로축에 레이어, 가로축에 연속 프레임 번호가 표시된다.
- [ ] 교차 셀을 선택하면 해당 레이어와 프레임이 동시에 선택된다.
- [ ] 셀 선택이 캔버스와 상태 표시에 함께 반영된다.
- [ ] 프레임 및 레이어 추가·삭제 후 표 크기와 선택 상태가 갱신된다.
- [ ] 표의 가로·세로 스크롤이 정상 동작한다.
- [ ] Effect Library와 Effect Properties 사이에서 캔버스가 정상 표시된다.
- [ ] 통합 타임라인 높이와 실제 선택 사용감이 적절하다.

## 키보드 단축키

- [ ] `Edit > Keyboard Shortcuts…`에서 네 명령의 현재 단축키가 표시된다.
- [ ] 단축키 변경 후 메뉴 표시와 실제 키 동작이 즉시 갱신된다.
- [ ] 프로그램을 다시 실행해도 변경된 단축키가 유지된다.
- [ ] 빈 단축키가 해당 명령의 키 입력을 비활성화한다.
- [ ] 중복 단축키를 적용할 때 충돌 명령 안내가 표시되고 저장되지 않는다.
- [ ] 기본값 복원 후 `Shift+N`, `Alt+N`, `Alt+B`로 돌아간다.
- [ ] 새 프로젝트 등 모달 대화상자 입력 중 편집기 단축키가 오작동하지 않는다.

## Project Settings

- [ ] `File > Project Settings…`가 열리고 기존 Project Info 항목은 없다.
- [ ] 프로젝트 이름 변경 후 창 제목에 반영된다.
- [ ] FPS 변경 후 재생 속도가 즉시 바뀐다.
- [ ] Loop를 끄면 마지막 프레임에서 재생이 멈춘다.
- [ ] Canvas Only로 확대하면 새 공간이 투명하다.
- [ ] Canvas Only로 축소하면 Anchor 기준으로 crop된다.
- [ ] 9개 Anchor 위치가 각각 예상 방향을 보존한다.
- [ ] 축소 적용 전 되돌릴 수 없음 경고가 표시된다.
- [ ] Scale Image and Canvas로 확대·축소할 수 있다.
- [ ] Scale 결과의 픽셀 경계가 흐려지지 않는다.
- [ ] Cancel 시 아직 Apply하지 않은 값이 유지되지 않는다.
- [ ] Apply 후 대화상자가 열린 상태로 유지된다.
- [ ] 저장 후 다시 열었을 때 변경 크기와 픽셀이 유지된다.
- [ ] 앱 버전 `v0.0.03`와 파일 형식 버전 `5`가 구분된다.

## Source Asset

- [ ] 서로 다른 형태의 PNG 여러 개를 가져올 수 있다.
- [ ] RGBA, RGB, 인덱스 컬러와 그레이스케일 PNG가 올바르게 표시된다.
- [ ] 원본 투명도와 크기가 유지된다.
- [ ] Source Asset 선택 시 최근접 썸네일, 크기와 중앙 피벗이 표시된다.
- [ ] 사용 중인 Source Asset 삭제 시 경고가 표시되고 삭제되지 않는다.
- [ ] 미사용 Source Asset 삭제 전에 확인창이 표시된다.
- [ ] 저장 후 원본 PNG를 이동·삭제해도 프로젝트가 다시 열린다.

## Transform Emitter

- [ ] Source Asset이 없을 때 Transform Emitter 추가가 비활성화된다.
- [ ] Point에서 모든 인스턴스가 같은 발생점에 배치된다.
- [ ] Line에서 시작점과 끝점 사이에 인스턴스가 분포한다.
- [ ] Circle에서 전체 원 배치가 가능하다.
- [ ] Circle 시작·끝 각도로 일부 호 배치가 가능하다.
- [ ] Instance Count, Emission Interval, Start Frame과 Lifetime 변경이 반영된다.
- [ ] Position 시작·끝 이동이 반영된다.
- [ ] Rotation 시작·끝 변화가 반영된다.
- [ ] Scale X/Y가 독립적으로 변화한다.
- [ ] 음수 Scale로 가로 또는 세로 반전된다.
- [ ] Horizontal Tilt가 좌우 모서리 배치를 바꾼다.
- [ ] Vertical Tilt가 상하 모서리 배치를 바꾼다.
- [ ] Perspective가 사다리꼴 깊이감을 만든다.
- [ ] Opacity 시작·끝 변화가 원본 alpha와 함께 적용된다.
- [ ] Linear, Ease In, Ease Out 결과 차이를 확인할 수 있다.
- [ ] Reset Settings 후 Generate 전까지 이전 결과가 유지된다.

## 생성 결과

- [ ] Generate 후 Generated Layer와 필요한 프레임이 생성되고 재생된다.
- [ ] 원, 고리, 선, 불규칙 알파 등 여러 소스 형태로 생성된다.
- [ ] 같은 설정으로 재생성한 결과가 동일하다.
- [ ] 파라미터 변경 후 같은 Generated Layer만 교체된다.
- [ ] 일반 레이어와 Source Asset 원본이 유지된다.
- [ ] Generator를 두 개 이상 만들 수 있다.
- [ ] 한 Generator 재생성 시 다른 Generated Layer가 유지된다.
- [ ] Generator 삭제 확인 후 전용 Generated Layer도 함께 삭제된다.
- [ ] 저장·종료·다시 열었을 때 Source, 설정과 생성 결과가 유지된다.
- [ ] Generated Layer를 포함해 PNG 프레임을 내보낼 수 있다.

## Live Preview

- [ ] Auto Preview가 기본 활성화되어 수치 변경 후 잠시 뒤 갱신된다.
- [ ] 여러 값을 빠르게 바꾸면 마지막 값의 Preview만 표시된다.
- [ ] Preview 갱신 중에도 창과 다른 컨트롤을 조작할 수 있다.
- [ ] 갱신 중 이전 정상 Preview가 유지된다.
- [ ] Preview 출력 프레임 전체가 재생된다.
- [ ] Preview가 실제 프로젝트보다 길거나 짧아도 전 프레임을 탐색한다.
- [ ] PREVIEW/미리보기 배지와 상태 문구로 Applied 결과와 구분된다.
- [ ] Apply to Frames 후 실제 Generated Layer가 교체된다.
- [ ] Revert Changes가 마지막 적용 settings로 돌아간다.
- [ ] Reset to Defaults는 Apply 전까지 프로젝트를 변경하지 않는다.
- [ ] Auto Preview를 끄면 수동 Refresh 전까지 렌더하지 않는다.
- [ ] Preview 실패 시 실제 프로젝트 결과가 유지된다.
- [ ] Generator 두 개의 미적용 Draft를 선택 전환 후 복구할 수 있다.

## 프레임 이동

- [ ] `Left`와 `Right`가 한 번에 한 프레임 이동한다.
- [ ] `<`와 `>`가 한 번에 한 프레임 이동한다.
- [ ] Preview 활성 중 Preview 프레임을 이동한다.
- [ ] Preview가 없으면 프로젝트 프레임을 이동한다.
- [ ] 재생 중 프레임 이동 시 먼저 정지한다.
- [ ] 입력 위젯, Source/Generator 목록과 메뉴 탐색을 방해하지 않는다.
- [ ] 단축키 Primary/Alternate 변경과 재실행 유지가 정상이다.

## Properties 직관성

- [ ] 시간 변화값이 Start → End 한 행으로 읽힌다.
- [ ] frame, px, degree, scale/normalized 단위가 표시된다.
- [ ] 모든 주요 Properties와 버튼에 동작 설명 Tooltip이 있다.
- [ ] Pseudo 3D와 Easing 섹션을 접고 펼칠 수 있다.
- [ ] Point/Line/Circle 전환 시 관련 입력만 표시된다.
- [ ] 패널을 Wheel로 스크롤할 때 비포커스 SpinBox 값이 바뀌지 않는다.
- [ ] SpinBox를 클릭해 포커스한 뒤에는 Wheel 값 변경이 가능하다.

## 언어

- [ ] 한국어 시스템에서 한국어가 기본 선택된다.
- [ ] Settings > Language에서 English로 즉시 전환된다.
- [ ] 재실행 후 선택 언어가 유지된다.
- [ ] 메인 메뉴, Effect 패널, Timeline과 주요 대화상자가 번역된다.
- [ ] Tooltip과 Preview/재생 상태가 현재 언어로 표시된다.
- [ ] 프로젝트, Source Asset, Generator 이름은 언어 전환으로 바뀌지 않는다.
- [ ] 사용자 단축키가 언어 전환 후에도 유지된다.

## 재생 제어

- [ ] 메인 화면에서 Enter를 한 번 누르면 재생된다.
- [ ] Enter를 다시 누르면 정지한다.
- [ ] 숫자 키패드 Enter로도 재생과 정지가 전환된다.
- [ ] 타임라인에 일반 선택 포커스가 있을 때 Enter가 동작한다.
- [ ] Animation 상단 메뉴는 남아 있고 Play / Stop Animation 항목은 없다.
- [ ] 재생 버튼, 상태 문구, 타이머 상태가 일치한다.
- [ ] 재생 단축키 변경 후 즉시 적용되고 재실행 후 유지된다.
- [ ] 사용자 지정 재생 키를 적용하면 Enter는 더 이상 재생을 전환하지 않는다.
- [ ] Project Settings의 이름·FPS 입력 중 Enter가 재생을 시작하지 않는다.
- [ ] New Project 입력 중 Enter가 재생을 시작하지 않는다.
- [ ] Keyboard Shortcuts 입력 중 Enter가 재생을 시작하지 않는다.
- [ ] 메뉴를 열고 탐색하는 동안 Enter가 재생을 시작하지 않는다.
- [ ] Loop 켜기·끄기 동작이 예상대로 작동한다.

## Playback Test Project

- [ ] `File > Create Playback Test Project`로 생성할 수 있다.
- [ ] 미저장 프로젝트 교체 확인을 취소하면 기존 프로젝트가 유지된다.
- [ ] 8×8 사각형이 8개 프레임을 따라 움직인다.
- [ ] 재생 상태 문구와 프레임 강조가 실제 픽셀 이동과 일치한다.
- [ ] FPS를 변경하면 재생 속도가 바뀐다.
- [ ] 샘플을 저장하고 다시 열 수 있다.
- [ ] 8개 PNG 프레임을 내보낼 수 있다.

## 타임라인 조밀도

- [ ] `Layer × Frame Timeline` 제목이 표시되지 않는다.
- [ ] 제목 제거 후 불필요한 세로 여백이 줄었다.
- [ ] 레이어 이름, 프레임 번호, 셀과 조작 버튼은 정상 표시된다.

## 내보내기

- [ ] 프레임별 PNG 내보내기가 가능하다.
- [ ] PNG 크기가 프로젝트 캔버스와 일치한다.
- [ ] 투명 배경이 유지된다.
- [ ] 여러 프레임의 파일명이 충돌하지 않는다.

## 창과 오류 처리

- [ ] 창 크기를 변경해도 UI가 심하게 무너지지 않는다.
- [ ] 잘못된 프로젝트 파일을 열 때 오류가 표시된다.
- [ ] 저장 실패 시 오류를 숨기지 않고 안내한다.

## 기본 편집 상호작용

- [ ] Duration 화살표를 빠르게 10회 클릭하거나 길게 눌러도 매 Step이 반영되고 12/24/60 FPS의 Frames와 일치한다.
- [ ] Timeline 폭 20/36/64/96px가 Effect와 Resource에 즉시 적용되고 재시작 후 복원된다.
- [ ] 한국어에서 메뉴, Particle 속성, Resource Editor, Tooltip, 상태·오류 문구를 확인하고 영어 전환 후 사용자 이름이 유지된다.
- [ ] 수치, Keyframe, Full Rotation, Pivot, Frame, Layer, Particle 설정을 Undo/Redo하고 저장 지점의 Clean 상태를 확인한다.
- [ ] Move Free/X/Y, Scale 균등/X/Y, Rotate와 Shift 15°가 Zoom 1/2/4/8 및 Pan 후에도 맞고 Escape가 Drag를 취소한다.
- [ ] Windows DPI 100/125/150%에서 Handle 크기와 Hit-test를 확인한다.

## Windows Native SpinBox

- [x] 96 DPI에서 새 리소스 Width 첫 Up, 반복 Up/Down과 빠른 10회 클릭이 반영된다.
- [x] 선택된 Height 숫자 상태에서 Up 클릭이 즉시 반영된다.
- [x] FPS, Duration, Frames의 네이티브 Up 클릭과 수학적 동기화를 확인했다.
- [x] Windows Qt 플랫폼에서 Mouse Press 유지 Auto Repeat 테스트가 통과한다.
- [x] New Project, Project Settings, Interface Settings, Layer Inspector, Particle/Effect Panel 대표 SpinBox SubControl 테스트가 통과한다.
- [ ] 실제 125% DPI에서 화살표 Hit Area와 반복 클릭을 확인한다.
- [ ] 실제 150% DPI에서 화살표 Hit Area와 반복 클릭을 확인한다.

## Resource Editor V2 회귀

- [ ] 빈 Editor, Asset List, Asset Preview, Composition Canvas에 PNG 한 개와 여러 개를 Drop한다.
- [ ] PNG+GIF, ASE/Aseprite, 대문자 확장자, 지원하지 않는 파일 혼합 Drop의 부분 성공을 확인한다.
- [ ] 64×64 Effect Preview와 Particle Preview 각각에서 Project Canvas를 600×600으로 변경하고 콘솔 예외·Preview Badge가 없는지 확인한다.
- [ ] Resize 후 새 Preview를 다시 만들 수 있고 Canvas·Timeline·현재 Frame이 정상인지 확인한다.
- [ ] 새 Resource Length의 Frames/Seconds 전환, 12→24 FPS 정책, 최소 1 Frame과 Up/Down 반복 입력을 확인한다.
- [ ] Resource→Asset→같은 Resource에서 Layer·Frame·Gizmo·Position/Rotation/Scale·Keyframe과 Undo/Redo가 유지되는지 확인한다.
- [ ] Resource→Effect Editor→Resource Editor 왕복과 언어 전환 후 같은 선택·속성이 유지되는지 확인한다.

## v0.0.04 시작과 스크러빙

- [x] 일반 실행에서 Startup Dialog가 먼저 표시된다. (취소 동작은 미확인)
- [x] 새 프로젝트의 크기, FPS, 초기 프레임 수와 Loop가 편집기에 그대로 반영된다.
- [ ] Startup Dialog에서 정상 프로젝트 열기와 잘못된 파일 오류 후 Dialog 유지가 동작한다.
- [x] Effect Timeline에서 1→12 드래그 후 마지막 프레임이 유지된다. (빠른 왕복은 자동 테스트만 완료)
- [ ] Resource Composition Timeline에서 1→12 드래그 시 Canvas가 연속 갱신된다.
- [ ] Timeline Frame Width 20/36/64/96px에서 드래그 스크러빙이 동작한다.
- [x] 빈 Resource Editor의 두 시작 버튼을 확인하고 빈 리소스 만들기가 동작한다. (실제 파일 가져오기는 미확인)
- [x] 빈 리소스 생성 후 Workspace 왕복 시 자동 Popup 없이 선택한 Resource가 유지된다.

## Tooltip 사용자 확인

- [ ] Main Window의 Workspace, New/Open/Save/Export, Undo/Redo에 마우스를 올려 행동 설명과 현재 단축키를 확인한다.
- [ ] Keyboard Shortcuts에서 Undo/Redo, 재생, 이전·다음 프레임 단축키를 변경한 뒤 기존 Tooltip이 즉시 갱신되는지 확인한다.
- [ ] Effect Timeline의 재생·정지, 프레임·레이어 조작, FPS와 스크러빙 설명을 확인한다.
- [ ] Effect Editor의 Source Import, Preview, Apply, Revert, Reset과 실제 표시되는 Generator/Particle 작업 설명을 확인한다.
- [ ] Resource Editor의 Import, Create Resource, Empty Resource, Reimport, Delete와 Use in Effect 설명을 확인한다.
- [ ] Resource Move/Rotate/Scale/Pivot, Full Rotation, Add/Remove Keyframe, Easing과 세 종류 Pivot 설명을 확인한다.
- [ ] 재생 중 Play Tooltip이 Pause로, Layer 표시 전환 시 Hide/Show 설명이 현재 상태와 일치하는지 확인한다.
- [ ] Particle Resource, Emission, Spawn Shape, Direction, Random Range, Preview, Bake와 Export 설명을 확인한다.
- [ ] Startup, New Project, Project Settings, New Resource, Interface Settings, Keyboard Shortcuts와 External Tools Dialog를 확인한다.
- [ ] 실행 중 한국어↔영어 전환 후 이미 보이던 버튼과 QAction Tooltip이 같은 정보량으로 갱신되는지 확인한다.
- [ ] Tooltip이 너무 빨리 사라지거나 패널 뒤에 가려지지 않고, 기능을 암시하지 않으며, 125%/150% DPI에서 잘리지 않는지 확인한다.

## Loop 회전·레이어 삭제·Wheel

- [ ] 12프레임 Loop Resource의 Full Rotation 마지막 값이 330°이고 반복 경계에서 같은 자세가 연속 표시되지 않는다.
- [ ] 12프레임 Non-loop는 마지막 360°, 2프레임 Loop는 마지막 180°, 역회전은 부호가 반대로 적용된다.
- [ ] 1280px 창에서 Resource Inspector가 약 300px이고 Canvas가 가장 넓으며, 유효한 사용자 Splitter 폭이 재시작 후 유지된다.
- [ ] Composition Layer와 Particle System을 버튼·Layer 메뉴·타임라인 이름 컨텍스트 메뉴로 삭제하고 원본 Resource Composition이 남는다.
- [ ] 삭제 직후 Inspector와 Guide가 정리되고 이전 레이어가 선택되며 Undo/Redo로 모델·픽셀·선택이 왕복한다.
- [ ] SpinBox 위 일반 Wheel과 포커스 후 일반 Wheel은 값이 변하지 않고 패널이 스크롤된다.
- [ ] Ctrl+Wheel은 정수·소수 SpinBox의 `singleStep` 한 단계씩 움직이고 최소·최대 범위를 지킨다.
- [ ] Ctrl+Wheel 사용 후에도 Native Up/Down 첫 클릭·반복 클릭·길게 누르기와 키보드 Up/Down이 정상 동작한다.

## Resource Layer 형식 6

- [ ] Resource Editor에서 `이펙트에 레이어로 추가` 후 Single Resource Layer가 선택된다.
- [ ] Placement Mode를 Particle Emission으로 바꾸고 방출 Origin·Direction·Shape·Preview·Bake·Export를 확인한다.
- [ ] Single과 Particle 설정을 각각 편집한 뒤 모드를 왕복해 양쪽 값이 유지되는지 확인한다.
- [ ] 기존 v5 직접 배치와 Particle 프로젝트를 열어 ID·순서·표시·결과를 확인하고 다른 이름으로 저장해 다시 연다.
- [ ] Add Composition Layer와 Add Particle System이 활성 UI에 남지 않았는지 확인한다.

## Loop Hit Area·Inspector Label·2.5D 성능

- [ ] New Resource에서 Loop 체크 표시와 글자를 각각 클릭해 토글되고, 글자 오른쪽 100px 이상의 빈 공간 클릭은 값을 바꾸지 않는지 확인한다.
- [ ] Loop에 Tab으로 포커스한 뒤 Space로 토글하고 Enter/Create와 Escape/Cancel이 그대로 동작하는지 확인한다.
- [ ] Effect Inspector를 280/300/320px로 맞춰 Single 및 Particle Emission의 모든 값에 화면 라벨이 보이고 가로 Scroll이나 Label/Editor 겹침이 없는지 확인한다.
- [ ] 한국어·영어, Windows 125%·150% 배율에서 Resource, Emission, Spawn Shape, Direction, Random Range와 2.5D/Easing 라벨을 확인한다.
- [ ] Particle Emission을 선택해 Position/Rotation XYZ와 Perspective를 빠르게 드래그하고 입력이 마지막 값에 따라오며 Inspector가 깜박이거나 재생성되지 않는지 확인한다.
- [ ] 조작 중 Guide가 따라오고 Particle Ghost 지연이 조작 후 해제되며 Escape는 복원·Undo 없음, Release는 Undo 하나인지 확인한다.
- [ ] Timeline/Playback/Status에 `사용자 레이어 이름 · 파티클 방출` 또는 `· Particle Emission`이 표시되고 활성 UI에 `Particle System:` 접두사가 없는지 확인한다.
- [ ] 조작 후 재생, Save/Load, Preview, Bake와 PNG Export 결과가 동일한지 확인한다.

## Interactive 2.5D Proxy

- [ ] 600×600 Particle Emission에서 Position/Rotation XYZ, Scale, Pivot, Perspective를 드래그해 화면이 약 30FPS로 최신 포인터를 따라오는지 확인한다.
- [ ] Drag 중 픽셀 가장자리가 부드럽게 보간되지 않고, Release 뒤 정확한 Nearest-Neighbor 결과로 한 번 확정되는지 확인한다.
- [ ] Ctrl+Wheel·키보드 Up/Down을 빠르게 반복한 뒤 입력 중 멈춤이 없고 약 120ms 후 정확 결과가 반영되는지 확인한다.
- [ ] 작은 파티클을 이동할 때 Canvas 전체가 깜박이지 않고 이전 위치 잔상도 남지 않는지 확인한다.
- [ ] Position Z가 다른 Resource Layer 앞뒤를 실제로 넘을 때만 합성 순서가 바뀌며, 같은 순서 안의 Z 조작은 계속 부드러운지 확인한다.
- [ ] Escape는 시작 Transform과 정확 픽셀을 복원하고 Undo를 만들지 않으며, Release는 Undo 하나만 만드는지 확인한다.
- [ ] 조작 중 상세 Particle Ghost/Guide가 유예되고 Release/Escape 뒤 즉시 복원되는지 확인한다.
- [ ] Proxy 활성 직후 Playback, Bake, Save와 PNG/Sequence Export를 실행해 Proxy 화면이 출력이나 프로젝트 파일에 섞이지 않는지 확인한다.

## Interactive Proxy Idle Prewarm

- [ ] 600×600, 표시 Resource Layer 5개에서 레이어 선택 후 잠시 기다린 다음 첫 Gizmo Press가 멈춤 없이 즉시 Drag를 시작하는지 확인한다.
- [ ] 선택 직후 즉시 Drag해도 입력이 Prewarm 완료를 기다리지 않고, 종료 뒤 다음 Drag는 Prewarm Hit가 되는지 확인한다.
- [ ] Timeline을 빠르게 20 Frame 왕복 Scrub해 중간 Frame에서 작업이 쌓이지 않고 마지막 Frame의 첫 Drag만 준비되는지 확인한다.
- [ ] Playback 중 Prewarm이 Canvas를 다시 그리거나 끊지 않고, 정지 후 현재 Frame에서만 준비되는지 확인한다.
- [ ] 선택 레이어의 Position/Rotation/Scale/Perspective를 반복 조작할 때 Underlay/Overlay가 유지되는지 확인한다.
- [ ] 다른 Resource Layer의 표시, Opacity 또는 정확 출력과 Position Z 앞뒤 순서를 바꾼 뒤 올바른 합성으로 갱신되는지 확인한다.
- [ ] Undo/Redo를 빠르게 반복한 뒤 마지막 상태의 첫 Drag와 정확 Release 결과가 일치하는지 확인한다.
- [ ] Prewarm 완료 자체로 Canvas가 깜박이거나 상세 Guide/Ghost가 사라지지 않는지 확인한다.

## Project Save Reliability & Performance

- [ ] PNG/GIF/Aseprite를 각각 Import하고 Resource Composition과 Effect Resource Layer에 연결한 뒤 Save·종료·Load해 ID, Pixel, Pivot, Duration/Tag와 참조를 확인한다.
- [ ] 세 원본 파일을 다른 위치로 옮긴 뒤 프로젝트를 열어 내장 Asset·Composition·Effect가 유지되고 Reimport만 새 경로를 요청하는지 확인한다.
- [ ] Source가 많은 프로젝트에서 첫 Save, 변경 없는 두 번째 Save, 이름만 변경, Pivot만 변경, 한 Source Reimport 후 Save 체감을 비교한다.
- [ ] Save As 취소와 쓰기 불가능한 폴더, 잠긴 대상 파일에서 기존 저장 경로·기존 파일·Dirty 표시가 유지되는지 확인한다.
- [ ] 저장 중 Save/Save As가 비활성화되고 완료 뒤 다시 활성화되며 성공 Status가 실패 시 표시되지 않는지 확인한다.
- [ ] 한국어와 영어에서 폴더/인코딩/Temporary/Atomic Replace 오류 안내가 내부 Traceback 없이 표시되는지 확인한다.

## Effect Gizmo responsiveness

- [ ] 600×600, Resource Layer 5개, Particle 100개에서 2.5D Position/Rotation/Pivot/Perspective를 Cold와 Warm 상태로 각각 100회 움직여 포인터가 먼저 반응하는지 확인한다.
- [ ] Linear Emission과 Orbit/Helix Motion 핸들을 빠르게 움직여 중간 상태가 누적되지 않고 약 33ms latest-wins로 현재 프레임만 갱신되는지 확인한다.
- [ ] 조작 시작 시 Playback이 즉시 정지하고 준비 중이던 다음 프레임 작업이 계속 쌓이지 않는지 확인한다.
- [ ] 조작 중 Project 저장값·다른 레이어·Timeline이 바뀌지 않으며 Inspector 값만 제한된 주기로 따라오는지 확인한다.
- [ ] Release는 Undo 하나와 정확 현재 프레임 하나를 만들고, Escape는 Undo·정확 렌더 없이 시작 상태로 돌아가는지 확인한다.
- [ ] Release 뒤 Undo/Redo 결과를 Direct Render, Bake, PNG와 픽셀 비교한다.
# Project-wide stabilization manual pass

These are real Windows GUI checks and are not claimed by offscreen automation.

- Startup: first run, accept/reject notice, do-not-show, Help reopen, Korean and space-containing paths.
- Project: New/Open, first and repeated Save, Save As, failed-save close, reopen.
- Import: RGBA/RGB/grayscale PNG, transparent/multi-frame GIF, Aseprite success/failure, move original then reopen embedded project.
- Editing: Composition, Single, Particle Linear/Orbit/Helix, 2.5D, keyframes, Undo/Redo.
- Timeline/output: fast scrub, playback/loop/end frame, Preview/Bake/PNG/sequence pixel comparison.
- UI: Korean/English, 100/125/150% DPI, inspector 280/300/320 px, zoom 25/100/400%, focus-sensitive wheel/Delete/Space/Ctrl+Z/Ctrl+Y/Ctrl+S.
