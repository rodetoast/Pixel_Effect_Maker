# Editor UX / Information Architecture Recheck

## 1. Baseline / Git

2026-10-02, 프로젝트 `C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker`의 코드·기존 테스트·합성 offscreen Qt 측정을 감사했다. **결론: 단순 padding/compact polish로는 부족하다. Qt Widgets를 유지하면서 Inspector의 탐색·그룹·레이아웃을 구조적으로 개선한다.** 기능 구현이나 Effect 기능 우선순위 재산정은 수행하지 않았다.

| 항목 | 실제 기준 |
|---|---|
| HEAD | `01797ec946ec39c90de34c60253b7802c386c054` |
| Branch | main, origin/main 대비 ahead 44 |
| App / FORMAT | v0.0.25 / 22 |
| Baseline full pytest | 1,732 passed / 99.26s, `C:\Dev\pem_ux_audit_baseline` |
| Staged | 0 |
| 기존 tracked 변경 | docs/EFFECT_AUTHORING_CAPABILITY_AUDIT.md: +16/-0 |
| 기존 untracked | docs/POST_V0_0_25_EFFECT_CAPABILITY_RECHECK.md, tools/recheck_post_v25_capabilities.py, 테스트소스.png |
| 이번 추가 | 본 문서, UI_UX_PRINCIPLES.md, tools/audit_editor_ux.py |

기존 파일은 아래 시작/종료 SHA256이 같으며, 링크 추가도 하지 않았다.

| 파일 | SHA256 |
|---|---|
| EFFECT_AUTHORING_CAPABILITY_AUDIT.md | `8186B3643F5A21670E93F9FC0D2EF5CBFFA88D95112E41F3CC4E198F67B7F2F6` |
| POST_V0_0_25_EFFECT_CAPABILITY_RECHECK.md | `90D2FDF78FB93604BE36E030FC8248423991A450E22AC4472D555D3A7B559779` |
| recheck_post_v25_capabilities.py | `A29B7758013E9E9468B9061BAEB7DA4A43C942659A6FD82C3908DB5CFB485C12` |
| 테스트소스.png | `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564` |

## 2. Current UI Inventory

### 측정 정의와 재현

`tools/audit_editor_ux.py`는 사용자 프로젝트 파일을 열지 않는다. 합성 Project/Resource/Particle, 독립 INI QSettings, offscreen Qt, 명시적으로 로드한 맑은 고딕 9pt를 사용한다. 최종 결과는 `C:\Dev\pem_editor_ux_20261002_evidence\inventory.json`이다. 실제 Windows GUI·모니터 DPI·마우스 클릭 측정이 아니다.

logical control은 Button/Check/Spin/Combo/LineEdit/List/Table/ShortcutEdit/Slider 하나를 1개로 센다. Spin 내부 LineEdit, Combo popup 등 구현 자식은 제외한다. List 항목·Timeline 셀은 control 수가 아니다. checkable GroupBox는 별도 group 수에 포함한다. **layout-visible**은 스크롤 아래쪽도 포함하고, **viewport-intersecting**은 현재 화면과 일부라도 겹치는 수다. 아래 v/c는 layout-visible/constructed다. 독립 미선택 패널의 enabled 수를 실제 편집 가능성 증거로 쓰지 않는다.

```powershell
& C:\Dev\pixel_effect_test_venv\Scripts\python.exe tools/audit_editor_ux.py --output C:\Dev\pem_editor_ux_fresh
```

출력은 repo 밖의 새 폴더만 허용한다. 최초 Sans Serif 실행은 한글 glyph가 없어 시각 근거에서 제외했다. 도구 수정 중 실패한 실행도 최종 증거가 아니다. 최종 실행은 한글 지원 true, 14 panels / 10 dialogs / 36 width-font-state 조건이다. JSON에는 각 패널 sizeHint/minimumSize/minimumSizeHint/content height/group별 위치와 수/visible controls/scroll 범위, 실제 menu 목록과 AST allocation 위치가 있다. AST allocation은 반복문·조건·비활성 legacy를 포함하므로 runtime control 수로 합산하지 않는다.

### 활성 surface 전체

파일은 `app/ui/` 기준이다. 실제 Inspector disclosure는 0이며, hierarchy 그룹 펼치기나 mode별 조건부 표시와 구별했다.

| Surface / 파일·클래스 | 역할·주요 작업 | 현재 control | 스크롤 / 접기 | 폭·높이·반응형 처리 |
|---|---|---|---|---|
| Main Window / main_window.py:MainWindow | Workspace 전환, 선택→편집→재생→저장/출력 | 전환2 + 아래 panel/menu | Inspector 접기0, hierarchy 접기는 별개 | Effect HSplitter, Resource H/VSplitter; 비접힘, 크기 저장; 선택별 stack 교체 |
| Menu / MainWindow._build_menus | 파일·편집·레이어·프레임·뷰·출력·설정·도움말 | top9; separator 제외25 entries, Language submenu 2 leaf 별도 | popup, section 접기 아님 | QAction·shortcut·tooltip; Animation menu entries0 |
| Command bars / timeline_command_bar.py + 각 Timeline | 재생/키 탐색/뷰/보조/구조 | Effect14+table1; Resource21+table1 | bar 자체 scroll0 | commandGroup/commandRole, separator, HBox; 자동 overflow/줄바꿈 없음 |
| Effect Library/Hierarchy / effect_library_panel.py:EffectLibraryPanel/EffectLayerList | Source/Animated 탐색, Resource Layer 생성·선택·순서·그룹·Lock/Solo | 합성 project14/19, legacy generator/후보 수에 따라 가변 | 외부 VScroll + 내부 list; section 접기0 | min280/max360; Source/Clip list 높이56..104; Layer group min250/list min150; HScrollOff |
| Particle Inspector / particle_properties_panel.py:ParticlePropertiesPanel | Particle Resource Layer motion/look/events/transform | 기본 Linear136/167, Helix ON158/167 | VScroll, 접기0 | panel min0, stack min320/max540; WrapAllRows 중심, numeric min70; HScrollOff |
| Single Inspector / composition_layer_properties_panel.py:CompositionLayerPropertiesPanel | Name/Parent/Resource/Placement/경로/2.5D | 독립 미선택62/62, groups5 | VScroll, 접기0 | min0, label wrap/max88..110, 공통 TransformPanel |
| Legacy Transform Emitter / effect_properties_panel.py:EffectPropertiesPanel | 기존 generator Source/Timing/Distribution/Start-End/Draft/Apply | 미선택31/43, Distribution에 따라 가변 | VScroll, 접기0 | 자체 min360, title15px, 수치쌍 min72 |
| Effect Group / group_inspector.py:GroupInspector | Name/children/Visible/Locked/Solo | 4/4 | 자체 scroll/접기0 | QFormLayout, help wrap; Resource에도 동일 부품 |
| Effect Timeline / timeline_widget.py:TimelineWidget | Frame/Layer/Key 선택·재생·스크럽·copy/paste·snap/reveal | 15/15 | table H/VScroll, hierarchy 그룹 접기 | hierarchy label220; table min190/max360; 전체 Timeline 높이와 table 높이는 다름 |
| Effect Viewport / canvas_widget.py:CanvasWidget | 결과/가이드/Gizmo·pan/zoom·선택 | 자식 control0, 직접 제스처 있음 | canvas pan/zoom | min320×320, paint/overlay; 0은 상호작용 부재가 아님 |
| Resource workspace / resource_editor_v2/resource_editor_widget.py:ResourceEditorWidget | Empty/Asset Inspect/Composition/Layer Edit | 활성 자식들의 합; hidden stack 제외 | H/VSplitter + mode별 Timeline | Browser185..340/default205, center min260, Inspector300..520/default320; Timeline min150/default235 |
| Resource Browser / resource_editor_v2/asset_browser_panel.py:AssetBrowserPanel | 원본 asset와 편집 resource를 별도 list로 선택/import/delete | 미선택3/5; 선택시 Delete 추가 | 각 list scroll, 접기0 | 부모 폭 제약, 선택 대상에만 삭제 버튼 표시 |
| Resource Start / ResourceStartPanel | Import 또는 빈 resource 생성 | 2 | scroll/접기0 | 중앙 정렬/stretch; 명확한 시작 흐름 존재 |
| Asset Preview/Strip / asset_inspector_widget.py:AssetPreviewCanvas/AssetFrameStrip | 원본 frame/pivot·pan/zoom·Fit/Actual | strip1 + 부모 Fit/Actual2 | strip scroll | preview min320×260; Pivot은 인접 Inspector |
| Asset Inspector / AssetInspectorWidget | metadata/pivot/center/reimport/createResource | 미선택5/5 | 자체 scroll/접기0 | QFormLayout, 부모 stack; 이번 font sizeHint209×212 |
| Resource Metadata / composition_inspector.py:CompositionInspector | Name/output pivot/info/Use in Effect | 5/5, group1 | 자체 scroll/접기0 | form + wordwrap info, Use minheight36 |
| Resource Layer / composition_inspector.py:LayerInspector | meta/Parent/Pivot/Gizmo/검색형 Property Stack | property0일 때17; Position/Scale/Rotation/Opacity 4 cards일 때35 | VScroll, card 접기0 | numeric min0, card WrapLongRows, mode 2열 grid 높이32; meta는 별도 form |
| Property Search / PropertySearchDialog | registry 검색, 이미 추가한 속성 비활성화 | 4 | list scroll, 접기0 | 검색→목록→Add/Cancel; Particle에는 대응 탐색 구조 없음 |
| Resource Group / GroupInspector | hierarchy-only 편집 | 4 | 위 공통 Group과 동일 | 기존 재사용 사례 |
| Resource Timeline / composition_timeline.py:CompositionTimeline/LayerOrderTable | hierarchy/property keys/playback/snap/multi-key | 22/22 | table H/VScroll, hierarchy 그룹 접기 | min150, hierarchy label220/max360, VSplitter 높이 조절 |
| Resource Preview / composition_canvas.py:CompositionCanvas | overscan/clip/pivot/Gizmo·pan/zoom | 자식 control0, 직접 조작 있음 | canvas 제스처 | min320×240, paint/overlay, Inspector mode 버튼 연계 |
| Status / MainWindow.statusBar + QLabel | playback/선택/임시 결과·거부·경고 | 별도 business control0, label 제외 | statusbar scroll0 | 3/4/5/6초 메시지 등; panel wordwrap 상태 라벨도 존재 |
| Error/validation | QMessageBox/cycle/trail/sub/lifetime/dialog label | 보통 modal OK1 또는 확인/취소2; 상태 label0 | 메시지별 다름 | field 주변/section 하단/창 하단/statusbar/modal 혼재 |

MainWindow의 활성 Resource Editor는 **V2**다. Source 근거: MainWindow `_build_ui` 205..244 / `_build_menus` 277..370, Particle constructor29..123, Resource V2 constructor50..73, LayerInspector67..74 / `_properties`128..164, TransformPanel28..62 / `set_layer`65..77. 기존 legacy 파일이 있다고 활성 화면으로 간주하지 않았다.

### Dialog / context menu

modal exec나 action 클릭 없이 생성·표시만 했다. 설정은 독립 INI다. 앱 소유 dialog의 실제 disclosure 수는 모두0이다. fixed min이 없다는 것이 자동 소형화를 보장하지는 않는다.

| 파일·클래스 | 작업 / control | offscreen actual size / scroll / 제약 |
|---|---|---|
| new_project_dialog.py:NewProjectDialog | Name/Preset/W/H/FPS/Frames/Loop/Create/Cancel9 | 219×279, scroll0, minimumHint 동일; inline validation |
| startup_dialog.py:StartupDialog | 위 + Open Project10 | 296×279, scroll0, inherited form |
| project_settings_dialog.py:ProjectSettingsDialog | General/Canvas/Anchor/Apply19 | 443×611, scroll0, groups3, anchor9개; inline validation/info |
| interface_settings_dialog.py:InterfaceSettingsDialog | Timeline cell width slider/spin/reset/close4 | 295×107, scroll0, minHint226×107 |
| external_tools_dialog.py:ExternalToolsDialog | Aseprite path/browse/detect/validate/clear/OK/Apply/Cancel8 | 274×128, scroll0, status label; 실제 탐지/실행 안 함 |
| keyboard_shortcuts_dialog.py:KeyboardShortcutsDialog | command8×shortcut2 + actions4 =20 | 422×352, scroll0, minHint381×352; duplicate error |
| preview_build_notice_dialog.py:PreviewBuildNoticeDialog | Notice3 / manual overview visible1, constructed2 | 680×620, QScrollArea1; explicit min560×480, screen-aware resize |
| resource_editor_v2/new_resource_dialog.py:NewResourceDialog | Name/W/H/FPS/Frames-or-Duration/Unit/Loop/Create/Cancel visible9, constructed10 | 219×249, scroll0; length stack, Loop maximum-size policy |
| composition_inspector.py:PropertySearchDialog | Search/list/Add/Cancel4 | 278×274, list 내부 scroll, minHint188×152 |
| QFileDialog/QColorDialog/QMessageBox integration | Open/Save/Import/Export folder/RGB/confirm/error | OS/runtime 소유 전체 controls는 미열거; 앱 entrypoint/source만 감사, native/manual 미실행 |

Effect Layer context(`effect_library_panel.py`467..475)는 Duplicate/Delete/Group/Ungroup, Parent 후보/Clear, Visibility/Lock/Solo, Forward/Back, Expand/Collapse다. 일반 leaf는12 actions+eligible parent 수, group은12(Parent 대신 Toggle Expand)다. Resource hierarchy context(`composition_timeline.py:_context_menu`425..439)는 leaf12+eligible parent 수, group11이며 별도 Toggle Expand action 없이 header click으로 그룹을 펼친다. 선택/lock/parent 가능 여부에 따라 enabled가 달라진다. 양 Timeline key context는 Copy/Paste/Delete+Easing4 =7 leaf actions이며 selection/context별 enabled가 다르다. 동적 후보를 고정 control 수로 나타내지 않았다. 이 popup에는 상시 Inspector section 접기가 없다.

### Particle Inspector의 실제 전체 순서와 control

생성 순서가 아닌 **표시 순서**다. v23 LifetimePointEditor가 legacy endpoints를 takeRow/hide/reparent하고, v24 Trail과 v25 Sub-emitter가 Lifetime 앞에 insertWidget된다. 기능 추가에 따라 같은 Inspector가 확장된 구체적 근거다. 숨겨진 endpoint9개는 현역으로 이중 집계하지 않았다.

| 순서 / 표시명·조건 | 전체 control | 사용 빈도 분류 |
|---|---|---|
| Resource Layer | Name/Parent/Placement3 | Always, Parent는 Occasional |
| Particle Resource | Resource/Output Frames/Start Frame3 | Always |
| Emission | One Shot/Cyclic Steady, Period, burst/over_time, Count Min/Max, Duration6 | Frequent |
| Spawn Shape | Shape, OriginXY, LineEndXY, Radius, BoxWH, Start/EndAngle10 | Frequent, shape별 상세 Occasional |
| Direction | fixed/radial, Direction, Spread, Speed Min/Max5 | Frequent, 비Linear에서는 disabled |
| Motion(생성명 Motion Basic) | Mode/Reset2 | Frequent |
| Orbit Center(Orbit/Helix) | CenterXYZ3 | Occasional |
| Orbit Shape(Orbit/Helix) | Radius Start/End, EllipseXY, StartAngle, Turns, Direction, PhaseSpread, PlaneRotation9 | Occasional / Advanced |
| Helix(Helix만) | Axis/AxisStart/End3 | Occasional |
| Interpolation(Motion Interpolation) | Radius/AngleEasing, Helix만 AxisEasing2/3 | Advanced |
| Advanced(Motion Advanced, Orbit/Helix) | LocalPerspective/KeyProperty/KeyEasing/AddKey4 | Advanced |
| Random Range | Lifetime/Scale/Rotation/AngularVelocity/Delay/ClipSpeed 각 Min/Max + RandomStartFrame/Seed14 | Frequent + Advanced 혼재 |
| Rendering | Normal/Additive1 | Frequent |
| Natural Motion | Gravity toggle/strength, Drag toggle/strength, Noise toggle/strength/frequency7 | Occasional, 해당 effect에서는 Frequent |
| Trail | Enable/Duration/SampleEvery/Opacity4 + status | Occasional |
| Sub-emitter | Birth toggle/target, Death toggle/target4 + status | Advanced / Occasional |
| Over Lifetime | Scale/Color enable2 + Scale/Opacity/Color 각각 list/time/value(or RGB)/easing/add/remove6 =20 | Frequent, multi-point 상세 Occasional |
| Advanced(공통 ResourceLayerTransformPanel) | checkable feature-bypass header, control 수와 별도 | Advanced, 화면 접기가 아님 |
| └ System Space Transform | Gizmo6, PositionXYZ/RotationXYZ/ScaleXY/Opacity/Perspective/PivotXY numeric12, animated10×(Easing+Key), Reset1 =39 | Advanced, 배치/Z회전은 Frequent |
| └ Surface Transform(Compatibility) | 동일 numeric12 + Reset1 =13 | Diagnostic / rare, 구형 프로젝트 호환 |
| Footer(group 없음) | RandomizeSeed/RefreshPreview/BakeToFrames/ExportPreviewSequence/RevertChanges5 | Randomize Occasional, 나머지 workflow action / rare |

Linear visible GroupBox15개(중첩2, top-level13), Helix20개(중첩2, top-level18)다. 수동 disclosure는 **0**다. Motion의 조건부 표시와 수동 접기는 다르다. 공통 Advanced 체크는 model의 advanced_transform_enabled를 바꾸면서 advanced_body.setVisible(True)를 유지한다(`resource_layer_transform_panel.py`65..94). UI 펼치기 화살표로 재사용하면 안 된다.

## 3. Major UX Problems

이번 증거만으로 P0(발견/사용을 막는 수준)는 확정하지 않았다. P1은 다음 구조 변경의 우선 범위다. 분류 A=Widgets 자체, B=현재 layout/component, C=style/tokens, D=정보 구조다.

| 우선도 / 실제 문제 | 코드·측정 근거와 영향 | 분류 / polish와의 차이 |
|---|---|---|
| P1 긴 property wall과 위치 상실 위험 | Linear136/Helix158, 접기0, category nav0; 첫 viewport 약7..10 controls. 대부분 화면 밖 | D+B, padding만 줄여 해결하기 어려움 |
| P1 workflow 분단 | Lifetime 기초는 Random Range, Motion은 Direction/Orbit/Natural로 분산. Rendering이 Natural/Trail/Events/Lifetime보다 앞. Trail/Sub가 Lifetime 앞에 삽입 | D, 정보 순서·탐색 입구 재설계 |
| P1 OFF/무관 상세의 면적 점유 | Gravity/Drag/Noise OFF numeric4, Trail OFF numeric3, OFF event target, OFF Scale/Color PointEditor 틀이 남음. Point에서도 전체 Spawn shape fields 상시 배치 | D+B, 기존 Motion 조건부 표시가 개선의 선례 |
| P1 빈도와 시각 우선순위 불일치 | 호환 Surface13, System39를 상시 표시. Random Range14에 수명/시각/delay/seed 혼재 | D, 기능 적용과 화면 표시 상태 분리 |
| P1 중요한 상태가 깊은 곳에 분산 | cycle/trail/sub/lifetime 상태는 해당 section, 선택은 좌측, playback은 Timeline, 일시 failure는 statusbar | D+B, 로컬 설명을 유지하며 상단 요약·이동 입구 필요 |
| P1 선택별 문맥 변화 큼 | Single62/Particle136..158/Group4/Legacy31, Resource metadata5/Layer17+cards. stack 교체를 보완할 안정 category/breadcrumb 부족 | D+B, 필요한 차이는 유지하되 탐색 상태 보존 |
| P2 같은 Advanced 이름·다른 의미 | Motion Advanced와 공통 feature-bypass Advanced; KO에서도 common GroupBox Resource Layer 고정 문자 | D+C, 명명/번역/enable-disclosure 의미 구별 |
| P2 action의 transaction 의미가 약함 | Randomize/Refresh/Bake/Export/Revert가 같은 세로 footer. numeric은 Undo commit, legacy는 draft/preview/apply도 존재 | B+D, Undo 버그를 주장한 것은 아님. adapter 동기화가 있어 Refresh/Revert를 무조건 no-op으로 판단하지 않음 |
| P2 부분적 design system | 공유 metrics/roles는 있지만 margins/font/colors/validation 직값 분산; key30×28 vs34×28 | C+B, 전체 theme가 없다고 단정하지 않음 |
| P2 소형 화면의 명시적 fallback 없음 | 900×600 request가944×697로 확장. 3열 minimum+canvas+Timeline, HBox commandbar | B, 이번 bounds flag0이므로 현재 가로 잘림을 확정하지 않음 |
| P2 playback menu 발견성 | Animation menu는 생성되지만 entries0, Play action/Timeline은 존재 | D+B, 재생 기능이 없다는 뜻은 아님 |
| P3 font 확대 시 다단 label | KO320/150% snapshot에서 Placement 등의 wrap | C+B, 겹침/기능 장애 확인 없이 P0로 높이지 않음 |

**자동 geometry:** 280/320/360 × font100/125/150% × EN/KO × Linear-OFF/Helix-ON =36조건 모두 interactive control body 밖 horizontal bounds flag0. label 글자 elision, popup, disabled 이유 이해, keyboard 도달성까지 검증한 것은 아니다. HScrollOff 자체도 적합성 증거가 아니다.

| EN content height px, width순280/320/360 | 100% | 125% | 150% |
|---|---|---|---|
| Linear, optional OFF, visible136/enabled112 | 6478/6478/6462 | 7536/7516/7496 | 8528/8504/8480 |
| Helix, optional ON, visible158/enabled146 | 7785/7785/7769 | 9087/9067/9007 | 10291/10267/10243 |

KO320은 Linear6488/7484/8632, Helix7795/8995/10371이다. 700px height에서 viewport 내 약7..10개다. 이는 명시 font의 layout 양이며 Windows native 실제 pixel값이 아니다. 설명/헤더/wrap도 높이를 차지하므로 하나의 UI 품질 점수를 만들지 않는다. **OFF여도 상세 면적이 크게 줄지 않는 점**이 핵심이다.

기존 test_editor_layout_density, test_effect_inspector_responsive_layout, test_timeline_command_bar_layout, test_resource_layer_panel_clarity, test_tooltip_audit는 compact·wrap·command grouping·접근성/tooltip을 지켜주는 유효한 polish/reliability다. workflow 발견성·scroll 기억·기능 중요도 검증과는 구별한다.

## 4. Information Architecture Findings

### 사용자 mental model과 현재 배치

| 제작자의 질문 | 현재 위치 | 재분류 |
|---|---|---|
| 무엇을 보여줄까? | Particle Resource, Random Range의 ClipSpeed/RandomStart | Source |
| 언제/어디/얼마나 생성할까? | Emission/Spawn, Random Range의 Delay/Lifetime | Emit, Direction 인접 |
| 어떻게 움직일까? | Direction/Motion/Orbit/Helix, AngularVelocity, Natural Motion | Motion |
| 시간에 따라 모양은? | Random Range Scale/Rotation + 아래 Over Lifetime | Lifetime/Look, 초기값과 over-life 구별 |
| 흔적/이벤트/합성은? | Rendering→Natural→Trail→Sub→Lifetime | Lifetime→Trail→Events→Rendering |
| 레이어 전체 배치/좌표계는? | 뒤쪽 Advanced의 System/Surface | Transform, Compatibility는 rare 상세 |

Lifetime Min/Max는 **생존 시간**, Scale Range/Color curve는 **모양 변화**, System Rotation은 **전체 배치**다. 모두 Lifetime으로 몰아넣지 않는다. UI category가 serialize field/track 이름과 같아야 하는 것도 아니다.

### 실제 코드상 탐색 경로

Effect Editor에서 Resource Layer를 선택하고 Particle Emission으로 둔 상황이다. scroll은 EN280/100%/700px의 section y를 기준으로 한 구조적 추정이지, 실제 mouse 클릭 수가 아니다.

| 작업 | 현재 section path / 명칭 | scroll / 다른 panel |
|---|---|---|
| 수 변경 | Layer→Particle Inspector→Emission→Count Min/Max | section y416, 하단 field는 첫 화면 밖일 수 있음; Inspector 안 |
| Cyclic | Emission→Emission Mode=Cyclic Steady→Cycle Period | 상부, validation 같은 section |
| Gravity | Natural Motion→Gravity→Strength | y3007, 깊은 scroll |
| Noise | Natural Motion→Noise→Strength/Frequency | 깊은 scroll |
| Trail | Trail→Enable→Duration/SampleEvery/Opacity | y3361, 깊은 scroll |
| Color Lifetime | Over Lifetime→Color enable→RGB point list→Value/Easing | y3881, 매우 깊음; QColorDialog 별도 |
| Birth/Death | Sub-emitter→Birth/Death→Target | y3627, 깊음; template 편집은 다른 Layer 선택 |
| Parenting | Resource Layer→Parent Layer | y27, 상부; hierarchy context도 가능, group과 transform parent 구분 |
| Additive | Rendering→Blend Mode=Additive | y2902, 깊음 |
| Export | menu Export→Export PNG Frames→folder→결과; 전용 Export Preview Sequence는 footer | global menu는 scroll 없음, 전용 footer는 최하단, folder popup |

Toolbar Order는 submenu 입구, context는 Bring Forward/Send Back이다. Delete/Remove compact/full label은 대상과 tooltip도 존재한다. 이름이 짧다는 이유로 서로 다른 명령이라고 주장하지 않았다. 향후 공유 command 정의로 정리할 대상이다.

### Design system 감사

| 항목 | 현재 공유 규약/구현 | 부족한 범위 |
|---|---|---|
| tokens | layout_metrics.py의 column minima/defaults, hierarchy220, compact30, Timeline heights | 전체 spacing/type/color/state 체계는 아님 |
| spacing/margins | Particle6/5, group7/8/7/7·v4, ResourceLayer8/6, Metadata10/8, cards6/4/6/5·4 | 비슷한 역할의 직값 분산, 역할별 token 필요 |
| font/header | 여러 panel15px, Overview는 QFont pt 증가 | pixel 고정과 font-relative 혼합; 실제 DPI QA 미실행 |
| height | compact30, Layer action30..32, Resource gizmo32, Use36, key28 | 무조건 같은 높이가 아니라 tool/inline/primary별 기준 |
| buttons/danger | command_group, commandRole primary/secondary/toggle/danger, tooltip/accessibility | 공유 style 적용과 transaction 설명 정비 |
| toggle/combo | Boolean Check, mode Combo, Advanced checkable GroupBox | feature enable과 화면 disclosure 구분, OFF 상세 disable에 그침 |
| numeric | NUMERIC_PROPERTY_SPECS, ScrollSafe/RotationSpinBox, text commit/Ctrl-wheel 정책 | 모든 field가 spec을 쓰지는 않음; Resource％/Effect normalized는 단위 의미를 표시 |
| color | RGB hex/contrast button, QColorDialog, LifetimePointEditor | swatch색은 data로 유지, alpha는 opacity에 별도 편집 |
| selected/disabled | palette highlight, primary marker/bold, keyState, 일부 이유 tooltip | OFF/locked/endpoint/mode 불가 사유를 동일한 로컬 상태 패턴으로 |
| tooltips | tooltip_helper의 번역 설명+현재 shortcut+Ctrl-wheel, 별도 PointEditor/key 설명 | tooltip만으로 category 발견성을 해결할 수 없음 |
| validation/error | #d9534f/#777, key #ffd43b/#74c0fc 직값, label/statusbar/modal | semantic severity token 및 중요 경고의 상부 입구 필요 |

판정은 **design system 전체 부재가 아니라 부분 규약과 공통 부품 위에 Inspector 구조·상태 계층이 부족한 상태**다. 기존 GroupInspector/LifetimePointEditor/TransformPanel/property registry/tooltip_helper/command_group을 활용해야 한다.

## 5. Widgets vs QML Assessment

**선택 A: Widgets 유지 + 구조적 redesign이면 충분하다.** P1은 주로 B/D이고, Widgets 자체 때문에 불가능한 A유형 장애는 확인하지 못했다. 기존 Undo/shortcut/search/model/Canvas를 다시 만드는 이유도 확인되지 않았다.

| 비교 축 | Widgets 개선 | Quick/QML / 이번 판단 |
|---|---|---|
| Dynamic layout / responsive | 이미 wrap/stack/visible/splitter 사용, width별 policy 추가 가능 | declarative layout에 적합하나 잘못된 category는 그대로; 현재 문제는 이동 필요 없음 |
| Animated disclosure / custom controls | 우선 비animation collapse로 충분 | animation/custom visual에 유리할 수 있음; 이번 task의 필수 요구 아님 |
| Theme consistency | semantic tokens + shared widget/stylesheet | Controls style/components로 가능, migration 자체가 일관성은 아님 |
| Drag/drop feedback | 기존 hierarchy/drop/paint overlay 활용 | 시각 피드백 후보지만 model/Undo 계약은 별도 필요 |
| Timeline drawing / Graph | 현재 table/custompaint 유지, 필요시 측정 후 개선; graph는 이번 미구현 | scene graph custom item 후보, Inspector IA 때문에 timeline 교체 불필요 |
| Canvas overlays | 기존 QPainter/Gizmo/overscan 유지 | 좌표/raster/input 계약의 이식 필요 |
| Performance | OFF 상세/업데이트 범위/layout 빈도를 별도 측정 | CPU Particle renderer 자동 가속 보장 없음. QQuickWidget에는 추가 render pass 및 threaded render loop 제한 |
| Python integration | dataclass/service/QUndoStack/signal 직접 활용 | QObject property/signal/slot/model bridge 가능; plain dataclass가 그대로 editable QML model은 아님 |
| Migration cost | UI-only 점진 적용, renderer/schema/Undo 보존 | focus/numeric commit/Auto-Key/multi-select/Lock/Parent 계약을 양 frontend에서 검증 |
| Testability | 현재 1,732 tests/offscreen geometry 활용 | Quick Test/backend contract/hybrid focus QA 추가; QWidget 특정 테스트 변경 필요 |
| Packaging | 기존 PySide 배포 조건 유지 | QML files/import modules/plugins/graphics backend 확인 추가; 이번 build 미실행 |

공식 자료: [QFormLayout wrap](https://doc.qt.io/qt-6/qformlayout.html), [Quick responsive layouts](https://doc.qt.io/qt-6.8/qtquicklayouts-responsive.html), [Python-QML integration](https://doc.qt.io/qtforpython-6/tutorials/qmlapp/qmlapplication.html), [QQuickWidget 성능·stacking 제약](https://doc.qt.io/qt-6/qquickwidget.html), [PySide deployment의 QML 수집](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html). 이는 일반 설계 자료이며 로컬 Qt에 최신 API를 도입한다는 제안이 아니다. project별 비용·적합성 판단은 코드 계약에 근거한 추론이며 비교 benchmark가 아니다.

현재 QML prototype을 milestone에 넣지 않는다. 재설계 Widgets에서도 측정된 toolkit 고유 제약이 남으면 **Particle Inspector 한 화면만** 현재 Widgets/재설계 Widgets/QML 개념안으로 비교할 후보다. 동일 command adapter/data/task/width/font로 Undo/Auto-Key/Ctrl-wheel/focus/IME·CPU/memory·packaging을 비교한다. Shell/Timeline/Renderer 이식을 묶지 않으며 철회 가능한 별도 실험으로 제안한다. 이번 prototype 구현0.

## 6. Recommended Redesign

### Progressive disclosure 비교

| 안 | 장점/발견성 | 단점/scroll/작은 화면 | 기존 변경량 |
|---|---|---|---|
| A single-scroll compact화 | 기존 위치 익숙함, 전체 연속 | OFF 상세 유지시 수천px. search/jump만으로 분단 해소 어려움 | 작음, P1 해결에는 부족 |
| **B workflow accordion + summary** | category와 active 상태를 한 목록에서 확인, 여러 category 동시 열기 | 모두 열면 다시 길어짐; 초기 open 수·jump·선택별 기억 필요. 280px에서도 세로 header 가능 | 중간, 기존 widget/command 재배치+collapse container |
| C category tabs + compact sections | category 내부 scroll 축소, nav 상시 표시 | 숨은 기능 발견 감소, 320px 다수 tab overflow, category 비교 왕복 | 중간~큼, page별 focus/scroll/selection 관리 추가 |

**B를 채택한다.** 상단에 대상 breadcrumb·Placement·warning 수·category 이동 combo/검색 입구를 고정하고, 아래 workflow sections를 둔다. 기존 single-scroll 기반을 쓰되 단순 padding 변경은 아니다. closed header는 이름+active summary+warning을 표시한다. 하나를 열면 나머지가 강제로 닫히는 배타적 accordion은 피한다. layer-id/placement별 category/scroll/focus는 view state로 보존하고 document/dirty/Undo와 분리한다.

### Particle IA 구체안

| category | 현재 기능 재배치 | 초기 상태 / summary 예 |
|---|---|---|
| 공통 header | Name/Parent/Placement/resource명/lock/multi-edit/warning | 상시 간결 표시, Parent 상세 row, 편집 불가 범위 이유 |
| Source | Resource/ClipPlaybackSpeed/RandomStart | 기본 펼침, Spark · speed1× |
| Emit | Count/Cycle/Period/burst-over-time/Duration/Output/Start/Delay/Lifetime + Spawn/Direction | 기본 펼침, 24–32 · Cyclic24f · Circle; shape 관련 field만 표시 |
| Motion | Linear/Orbit/Helix/조건별 details, AngularVelocity, Gravity/Drag/Noise, Motion key 상세 | 기본 접힘, Helix · Gravity · Noise; mode 전환시 관련 상세로 안내 |
| Lifetime / Look | 초기 Scale/Rotation range + Opacity/Scale/Color PointEditor | 기본 접힘, Scale · RGB · Fade; OFF는summary/toggle, ON은editor; Timeline key와 별도 age |
| Trail | Enable/Duration/Interval/Opacity/기존 bound-cost status | OFF 기본 접힘, active summary 유지, 12f / every2f · 0.75 |
| Events | Birth/Death enable/target/validation | 기본 접힘, Death → Impact Spark; OFF target 숨김, invalid는 상단 경고 연결 |
| Rendering | Normal/Additive | compact header selector는 바로 접근, Additive; 상세 page 불필요 |
| Transform / Advanced | 빈번한 Position/RotationZ/Scale basics + Z/RotationXY/Perspective/Pivot/Key; Surface | basics만 선택적 펼침, advanced/compatibility 기본 접힘; nonidentity/animated summary+badge |
| action area | Randomize는 Seed 옆, preview utility/Bake/Export와 Undo 편집 구별 | compact preview/status와 목적별 menu; global Export에서 대상 명확히 |

advanced_transform_enabled는 **기능 적용/Bypass**, 화살표는 **화면 표시**로 서로 다른 control이다. OFF로 기존 값을 버리지 않는다. 호환 nonidentity 상태는 접어도 알 수 있어야 한다. direction speed는 Emit과 Motion에서 한 실제 편집 위치를 갖고 다른 category에서는 이동 입구를 제공하여 중복 state를 만들지 않는다.

### Main layout과 workspace 관계

미변경 shell을 먼저 측정하고 이후 독립 Inspector를 측정했다. window에는 margin/menu/status도 있어 열의 합이 전체 폭과 같지는 않다.

| requested size | Effect Library/Canvas/Inspector | Resource Browser/Center/Inspector | actual / 해석 |
|---|---|---|---|
| 900×600 | 280/320/320 | 185/425/300 | 양쪽944×697로 확대; 명시적인 소형 layout 필요 |
| 1024×768 | 280/380/340 | 185/505/300 | 요청 크기 유지; Effect 중앙 여유 적음, 작업 불능은 미판정 |
| 1280×800 | 280/636/340 | 200/735/311 | 요청 유지, 중앙 약50%/57% |
| 1600×900 | 280/956/340 | 251/924/391 | 요청 유지, splitter 저장과 mode default 영향 |

Effect는 Canvas 아래 full-width Timeline(이번 약284px, table190..360), Resource는 VSplitter(1280에서469/228)로 높이 조절이 명확하다. Layer→우측 Inspector→아래 Timeline의 기본 동선은 자연스럽다. 다만 Resource의 Layer는 Timeline에, Effect hierarchy는 Library 안에 있어 위치가 달라진다. Effect Library는 자산 catalog와 document hierarchy를 함께 담고 외부/내부 scroll이 겹친다.

제안: 두 workspace 모두 좌측 **document Layers**, 중앙 viewport, 우측 Inspector, 아래 Timeline의 역할을 맞추고 library/catalog는 별도 tab 또는 drawer로 둔다. Asset/Resource 구분은 유지하고 Layers와 혼합하지 않는다. 처음부터 library를 상시 네 번째 열로 늘리지 않는다. Source→Use in Effect는 동일 resource-id/name breadcrumb로 연결한다.

1280에서 중앙 약절반 이상을 유지하고 우측 기존320..360을 출발점으로 font/content를 우선한다. 수동 resize를 저장한다. 1024 근처는 catalog 닫기와 command overflow를 명시하고, 낮은 높이는 Timeline 높이 조절/일시 축소 입구를 제공한다. 900 이하 지원 하한은 native 측정 후 정한다. 모두 minWidth0으로 바꾸는 처방은 피한다. Resource300/Effect320 차이도 근거를 확인하고 무조건 통일하지 않는다.

Resource Inspector는 Resource metadata/선택 Layer/Properties를 같은 header로 구별한다. Source/Pivot/Transform/Look/Animation 범주로 기존 검색형 Property Stack을 연결하고, 추가한 속성만 보이는 장점을 유지한다. Asset Inspect는 원본 보기이며 Composition 편집과 구별한다. Timeline Key→Layer/Property Reveal을 기존 nav와 연결하되 Particle Lifetime의 age0..100%와 Timeline frame key는 명시적으로 다른 시간축이다.

### Commands / validation / tokens / reusable components

global은 File/Edit/Export/Settings, document는 Layer/Frame, 보조는 Timeline View/Snap, Inspector는 선택 대상 편집으로 책임을 나눈다. 빈 Animation menu와 workspace-aware 재생 명칭을 후속 사양으로 정리한다. toolbar/context에 동일 command id·대상·disabled 이유를 공유한다. numeric Undo commit과 Preview/Bake/Export·호환 draft의 작용 범위는 문구로 설명하고 색에만 의존하지 않는다.

거부는 해당 row 가까이 유지하고 section badge와 상단 warning count/이동 링크를 둔다. 단순 성공은 statusbar, 파괴 확인/회복하기 어려운 파일 실패는 modal이다. 중요한 오류를 몇 초짜리 statusbar에만 남기지 않는다. 기존 validation/Undo 의미 변경은 이 감사에서 구현하지 않았다.

| component 후보 | 현재 출발점 / 필요한 책임 |
|---|---|
| InspectorSection/ToggleSection/FeatureEnableHeader | Particle _group, 조건부 Motion, TransformPanel; disclosure/enable 분리, summary/badge/view state |
| InspectorRow/NumericRow/ComboRow | 중복 QFormLayout, numeric specs, ScrollSafe; unit/range/commit/buddy/wrap/이유/Auto-Key footer |
| InspectorColorRow | LifetimePointEditor hex/contrast/QColorDialog; RGB-only/alpha 분리, swatch data와 theme 분리 |
| InspectorWarning/EmptyState | cycle/trail/sub/lifetime status, ResourceStartPanel, generator empty; severity/local 설명/상단 연결 |
| CommandBarAction/DangerAction | command_group/commandRole/tooltip_helper/delete; 대상·가능 이유·접근성 |
| 기존 부품 재사용 | GroupInspector/LifetimePointEditor/TransformPanel을 측정 없이 독자 교체하지 않음 |

tokens는 기존 layout_metrics에서 spacing/margin, section/header/font, compact/tool/inline/primary height, key/info/warning/error/danger 색, border/focus/disabled로 점진 확장한다. 직값 역할을 먼저 정리하고 token 이동 후 font/폭 QA한다. swatch 색까지 고정 theme값으로 만들거나 RGB를 일괄 치환하지 않는다. 미래 규칙의 짧은 진입점은 UI_UX_PRINCIPLES.md다.

## 7. Proposed UX Milestones

| 단계 | 범위 | 완료 조건 / 제외 |
|---|---|---|
| UX-1 규약·공통 부품 | semantic tokens, Inspector section/row/enable/summary, command 대상/validation 계층 | 접기로 dirty/Undo 증가0, OFF 값 유지, key/numeric/Ctrl-wheel/IME 보존, EN/KO280..360×font100..150 QA; 앱 전체 교체 제외 |
| UX-2 Particle IA | B안 categories, OFF disclosure, jump/search, layer별 view state | 위10 탐색 task native QA, 접어도 active/호환 상태 발견, Undo/Auto-Key/sub-target/Lock/multi 회귀0; model/renderer/schema/version 변경은 별도 승인 |
| UX-3 Workspace/navigation | Layers/catalog 역할, Resource header/Property Stack, workspace commands, Timeline, compact fallback | 1024/1280/1600+실DPI125/150, viewport/focus/Reveal/Empty-Asset-Composition 전환, splitter 설정 호환 확인 |

3단계 권장이다. QML을 자동 UX-4로 넣지 않는다. Widgets 고유 미해결 제약이 측정된 경우에만 별도 한 화면 prototype proposal을 만든다. 기능 우선순위는 재계산하지 않았고 이번 milestone은 모두 미구현이다.

## 8. Verification / Git / Manual Boundary

| 검증 | 결과 |
|---|---|
| Baseline full suite | 1,732 passed / 99.26s |
| Final full suite | 1,732 passed / 99.59s, C:\Dev\pem_ux_audit_final |
| compileall app/tests/tools | 성공 |
| direct / run_app.bat --check | 각각 exit0, 아래 로그 경고 있음 |
| version / FORMAT | v0.0.25 / 22, 변경 없음 |
| offscreen inventory | 정상 종료, 36조건/14panels/10dialogs, 한글 지원 true |
| git diff --check | 성공, 기존 tracked diff +16/-0만 유지 |
| HEAD / staged / 기존4 SHA256 | 기준과 동일 / 0 / 모두 동일 |
| production/tests 변경 | 0 |
| commit/stage/tag/push/build/ZIP/PyInstaller | 수행하지 않음 |

direct 및 run_app.bat의 --check를 각각 확인했다. sandbox의 AppData 로그파일 쓰기 PermissionError/logging_unavailable 경고가 발생했고 권한이나 log path를 변경하지 않았다. exit0을 정상 로그 생성까지 성공했다는 의미로 해석하지 않는다.

3장의 KO320/Linear/font100/125/150 snapshot을 저장했고 150%를 직접 확인해 label wrap을 관찰했다. 모든 metrics/source allocation/menu trace는 repo 밖 JSON에 있다. 최초 font누락/중간 실패 run은 제외했다. 진단의 logical bounds flag0은 전체 UI clipping·기능 성공·성능 향상 판정이 아니다.

**실Windows native GUI/실모니터 DPI/마우스 task timing/screenreader/high contrast/IME 입력/dropdown/native dialog/실프로젝트의 Undo·replay performance manual QA는 수행하지 않았다.** 후속 QA는10 탐색 task, selection/placement 전환과 scroll 기억, OFF→ON 값 유지, disabled 이유, locked/solo/group/parent/multi, Auto-Key/Undo/text commit/Ctrl-wheel, EN/KO/실DPI, Preview/Bake/Export의 대상을 확인해야 한다.

신규 감사 문서2개와 diagnostic1개는 unstaged/uncommitted로 종료한다. 기존 capability recheck 및 테스트소스.png도 수정/삭제/rename/stage하지 않았다. Effect capability priority 재산정이나 production UI 적용은 이번 결과에 포함하지 않는다.
