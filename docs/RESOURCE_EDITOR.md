# Resource Editor V2

Resource Editor V2는 한 화면에서 여러 객체의 속성을 섞지 않고 현재 작업 상태에 필요한 UI만 표시합니다.

```text
Imported Asset → Resource Composition → Particle / Effect → Preview → Bake / Export
```

## 상태

- `EMPTY`: Import 안내와 버튼만 표시합니다.
- `ASSET_INSPECT`: 원본 Preview, 독립 Frame Strip, 형식·크기·프레임 수, Asset Pivot, Reimport와 `Create Resource from This Asset`만 표시합니다.
- `COMPOSITION`: Composition Canvas, Resource Inspector, 전용 Timeline과 `Use This Resource in Effect`을 표시합니다.
- `LAYER_EDIT`: Composition 화면에 선택 경계, Handle 기즈모, Layer Inspector, Property와 `Full Rotation`을 추가합니다.

Controller는 선택한 Asset/Composition/Layer ID와 현재 프레임만 관리합니다. Project의 ResourceComposition이 유일한 데이터 원천이며 별도의 편집 복사본을 만들지 않습니다. Drag 도중 시작 값만 Canvas가 임시로 보관합니다.

## 에셋에서 리소스 만들기

PNG 기본값은 확장자를 제거한 이름, 원본 크기, 12 FPS, 1초, 12프레임과 Loop On입니다. GIF/Aseprite는 원본 크기, 총 duration에서 계산한 FPS·길이와 원본 Loop를 사용합니다.

Create를 누르면 ResourceComposition 생성, Asset Layer 추가, Asset Pivot 복사, Composition/Layer 선택과 Timeline 갱신이 한 동작으로 완료됩니다. 사용자가 에셋을 다시 선택하거나 별도의 Add 버튼을 누를 필요가 없습니다.

## 여러 이미지 Layer 제작

Composition Timeline의 `+ 이미지 레이어 추가` 메뉴는 프로젝트에 가져온 SourceAsset/AnimationClipAsset을 명시적으로 선택해 현재 Resource의 가장 앞 Layer로 추가합니다. Layer 이름은 Source 이름을 따르며 같은 이름은 `(2)`, `(3)`으로 구분합니다. Source 없는 이미지 Layer는 만들지 않습니다.

Timeline의 Layer 목록은 **위=Canvas Front, 아래=Canvas Back**입니다. 위/아래 버튼과 행 Drag & Drop은 실제 source-over 합성 순서를 즉시 바꿉니다. 여러 칸 Drag도 Drop 순간 한 번만 적용되어 Undo 한 단계이며, 같은 위치 Drop이나 취소는 revision·render·Undo를 만들지 않습니다.

`레이어 복제` 또는 Timeline에 포커스가 있을 때 `Ctrl+D`는 선택 CompositionLayer를 원본 바로 앞에 복제합니다. 복제본은 새 stable ID와 `(2)`, `(3)` unique 이름을 얻고 Source Asset ID는 공유하지만 Visibility, 범위, Pivot, Sprite Transform, Track, Keyframe과 Easing은 깊은 복사로 독립됩니다. Add, Duplicate, Remove와 Reorder는 각각 Undo 한 단계이고 Undo/Redo는 같은 복제 ID를 복원합니다. Remove는 CompositionLayer만 제거하고 원본 Asset은 유지하며 마지막 Layer 제거도 허용합니다.

Layer 선택은 Inspector, Gizmo, Selection Box와 Property Timeline row를 함께 전환합니다. 선택 전환 자체는 Composition revision, Render cache, Keyframe 또는 Undo를 변경하지 않습니다.

## Canvas와 기즈모

Canvas는 체커보드, 최근접 이웃, 정수 Zoom, Middle-button Pan과 Composition 경계를 제공합니다. 보이는 Layer는 최상단부터 변환된 polygon으로 hit-test하며 빈 공간을 누르면 선택을 해제합니다. Canvas와 Timeline의 Layer 선택은 같은 Controller 상태를 사용합니다.

- Move: 선택 polygon 내부 Drag
- Rotate: 경계 바깥의 노란 Rotate Handle Drag, Shift 15° 스냅
- Scale: 경계 모서리 Handle Drag, 양수 균등 Scale
- Pivot: Pivot 십자 Drag, Keyframe을 만들지 않음
- Escape: Drag 시작 전 Track/Pivot 상태 복원

Transform Handle Drag는 해당 Track이 없으면 자동 등록하고 현재 프레임 Keyframe을 생성합니다. Handle 밖 클릭은 Transform을 시작하지 않습니다.

## 세 종류의 Pivot

- Asset Pivot: 새 Layer의 초기 Pivot이며 Asset Inspector에서 수정합니다. 기존 Layer에는 전파하지 않습니다.
- Layer Pivot: 해당 Composition Layer의 Rotation/Scale 기준입니다.
- Output Pivot: Composition 전체가 Particle Frame Source로 사용될 때의 기준점입니다.

각 Pivot은 별도 Inspector와 Center 버튼을 사용합니다.

## Timeline과 Property

Asset Frame Strip과 Composition Timeline은 서로 다른 위젯입니다. Composition Timeline은 Layer 범위·표시, Property Track, Keyframe marker, 현재 프레임, 재생과 키프레임 삭제를 제공합니다. Position, Rotation, Scale, Opacity는 검색 Dialog로 필요한 항목만 등록합니다.

`Full Rotation`은 첫 프레임 0°, 마지막 프레임 360°, Linear Keyframe을 만듭니다. 기존 Rotation Keyframe이 있으면 현재 언어로 교체 확인을 요청합니다.

## Effect 연결과 Legacy

`이펙트에 추가…`는 Resource Composition을 컴포지션 레이어로 직접 배치하거나 파티클 시스템 리소스로 사용하는 두 선택을 제공합니다. 컴포지션 레이어는 Start/End 경로를 직접 편집하고, 파티클 시스템은 방출·방향·속도·수명을 적용합니다. 기존 Asset/Animation Clip 직접 Particle 참조는 파일 호환 경로에만 유지합니다.

기존 `app/ui/resource_editor_widget.py`와 Transform Generator 모델은 Legacy 호환을 위해 보존합니다. MainWindow 기본 Workspace는 `app/ui/resource_editor_v2/`만 사용하며 새 Transform Generator 생성 버튼은 숨깁니다. 기존 Generator가 있는 프로젝트에서만 Legacy 영역을 표시합니다.

## 알려진 제한

Composition 중첩, Graph Editor, Keyframe 다중 선택, Layer 다중 선택, Lock/Solo와 Composition 생성 후 안전한 재타이밍은 제공하지 않습니다.
