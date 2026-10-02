# Pixel Effect Maker v0.0.25 수동 테스트 체크리스트

## v0.0.25 Sub-emitter — 사용자 Windows GUI 승인 필요

Codex Windows native GUI manual: **수행하지 않음**. 아래는 모두 미실행이다.

- [ ] OFF가 v24와 동일한지.
- [ ] 기본 OFF/None에서 Enable → 대상 선택 흐름이 사용 가능하고 선택 전 Undo/dirty가 없는지.
- [ ] KO/EN, 좁은 Inspector/확대 글꼴에서 Sub-emitter가 잘리지 않는지.
- [ ] Birth Flash가 실제 부모 birth 위치/프레임에 생기는지.
- [ ] Death Impact가 마지막 visible L-1 위치에서 다음 프레임에 시작하는지.
- [ ] Parent Trail이 Death를 늦추거나 두 번 발생시키지 않는지.
- [ ] random lifetime/delay/Over Time 부모의 개별 timing을 따르는지.
- [ ] child Burst/Over Time/Delay가 event-relative schedule인지.
- [ ] target absolute Start가 event delay로 추가되지 않는지.
- [ ] Hidden/Solo/Locked target도 template 사용은 유지되는지.
- [ ] Target Layer/Parent/Surface transform은 child에 영향 없는지.
- [ ] Parent Layer/Parent/System/Surface와 2.5D/revolutions가 전체 child에 적용되는지.
- [ ] Birth+Death 동시 및 같은 Target 사용 확인.
- [ ] Target Cyclic은 한 canonical emission만, Target nested events는 실행되지 않는지.
- [ ] Cyclic Parent에서 주기 반복 및 gate prewarm 확인.
- [ ] Sequential/Direct/Reverse/Step/current/full/generated/playback/PNG 시각적 일치 확인.
- [ ] A BirthON→X/DeathOFF→Y, B BirthOFF→Z/DeathON→W 선택·언어·scrub 보존.
- [ ] Enable/Target 네 액션 Undo1/Redo exact; no-op/invalid/refresh0 확인.
- [ ] Target rename display만 변경, duplicate가 기존 target을 retarget하지 않는지.
- [ ] Target Delete 하나의 Undo에 target/모든 surviving references가 함께 복원되는지.
- [ ] Target emitter/source/lifetime/Trail/Blend 변경이 부모 preview/generated에 반영되는지.
- [ ] Save/Reload에서 설정 보존 및 missing target 안전 disable/clear 확인.
- [ ] Child Trail/Multi-point/G/D/N/Normal/Additive full-stack 확인.
- [ ] 4096 visual/8192 stamp 초과 거부, silent drop 없음, output duration 자동 확장 없음.
- [ ] 수백 Parent editing cost 확인; safety limit을 실시간 보장으로 오인하지 않는지.

Collision splash가 아닌 lifetime death diagnostic이다. GUI 승인 전 v25 stage/commit 금지.

## v0.0.24 Sprite Trail — 사용자 Windows GUI 승인 필요

Codex Windows native GUI manual: **수행하지 않음**. 아래는 모두 미실행이다.

- [ ] KO/EN Trail 그룹과 필드, frame suffix, tooltip이 잘림 없이 보이는지.
- [ ] 좁은 Inspector 및 확대 글꼴에서 가로 잘림/중첩 없는지.
- [ ] 기본 OFF/12/2/0.75 및 OFF의 세 값 비활성 상태 확인.
- [ ] OFF로 전환해도 값이 보존되는지.
- [ ] A ON/17/3/0.625와 B OFF/41/5/0.3125를 A→B→A 선택 후 확인.
- [ ] 언어 변경/refresh/Timeline scrub 뒤 A/B 값 유지 확인.
- [ ] Enable/Duration/Interval/Opacity 각각 Undo 1회 및 Redo exact 확인.
- [ ] no-op/invalid/refresh가 Undo나 dirty를 만들지 않는지.
- [ ] Interval >= Duration, 범위 밖 입력이 원래 값으로 복원되는지.
- [ ] 4096 visual-copy 및 8192 stamp 초과 시 명시된 안내 확인.
- [ ] birth frame에 잔상 없음, head 밝기가 이중 렌더되지 않는지.
- [ ] head death 뒤 잔상 유지 및 마지막 유효 age 뒤 소멸 확인.
- [ ] Projectile의 경로 잔상과 느린 fade 확인.
- [ ] Magic Wisp/Comet의 곡선 잔상 확인.
- [ ] Hit Spark와 Sword Slash Helper의 잔상 밀도 확인.
- [ ] Cyclic Ember 첫 gate에 이전 주기 tail-only 잔상 확인.
- [ ] Cyclic static/local 조건에서 주기 반복 확인.
- [ ] Current/Play/Step/Reverse/Seek/Generated/PNG의 시각적 일치 확인.
- [ ] Layer/Parent 이동은 모든 잔상을 함께 이동시키는 current snapshot인지.
- [ ] 2.5D/System/Surface/Rotation Revolution 변환 및 strict output clipping 확인.
- [ ] Save/Reload에서 Trail 설정 보존 및 legacy format20 기본 OFF 확인.
- [ ] 낮은 Count부터 비용을 확인하고, 실시간 보장으로 safety cap을 오인하지 않는지.

Ribbon/world-history는 이번 구현 범위가 아니다. GUI 승인 전 v0.0.24 stage/commit 금지.

## v0.0.23 Multi-point Lifetime — 사용자 Windows GUI 승인 필요

Codex Windows native GUI manual: **수행하지 않음**. 아래 항목은 미실행 체크리스트다.

- [ ] Scale 0→1.2→0의 빠른 peak와 shrink 확인.
- [ ] Opacity 0→1→0 fade-in/out 및 hold 구간 확인.
- [ ] RGB White→Yellow→Red 중간 색과 원본 곱셈 tint 확인.
- [ ] 첫 구간 Ease Out / 다음 Linear의 차이 확인.
- [ ] Add Point가 가장 큰 gap의 midpoint, 평가값, Linear easing으로 생성되는지.
- [ ] Remove는 선택된 내부 지점만 가능하고 선택 없으면 비활성인지.
- [ ] 0%/100% 끝점 시간 수정·삭제가 불가능한지.
- [ ] 중복·crossing·범위 밖 시간이 거부·복원되는지.
- [ ] Add/Remove/Time/Value/RGB/Easing/Enabled 각각 Undo/Redo exact인지.
- [ ] A→B→A 선택, 언어 변경, timeline scrub 뒤 서로 다른 curves 보존.
- [ ] 모든 point/time/value/RGB/easing/enabled Save/Reload 보존.
- [ ] 기존 FORMAT19 2-point 효과가 시각적으로 같은지, Alpha Easing 유지.
- [ ] Cyclic Fire 첫 gate부터 prewarm 입자가 중간 lifetime 상태인지.
- [ ] Cyclic+Gravity+Drag+Noise+세 곡선+Additive full stack 조작 확인.
- [ ] 같은 frame Preview/PNG와 크기/clip/overscan 확인.
- [ ] 좁은 Inspector와 125%/150% 표시 배율에서 선택·입력·버튼이 잘리지 않는지.

GUI 승인 전 v0.0.23 stage/commit/tag/push/build 하지 않는다.

## v0.0.22 Cyclic Steady — 사용자 Windows GUI 확인 필요

Codex Windows native GUI manual: **수행하지 않음**. 아래는 체크리스트이며 통과했다고 표시하지 않는다.

- [ ] 기존 One Shot 프로젝트가 v0.0.21과 시각적으로 같은지 (Normal/Additive).
- [ ] Fire/Ember: 첫 visible frame부터 이전 반복의 파티클이 있는지.
- [ ] Dust: empty→fill ramp 없이 반복되는 분포인지.
- [ ] Rain/Snow: 첫 frame부터 화면 위/중간/아래에 수명상 적절한 파티클이 있는지.
- [ ] frame 5와 5+Period의 local pattern이 같은지.
- [ ] Period 6/12/24 차이와 같은 Seed 패턴 반복의 미감을 확인.
- [ ] Lifetime>Period에서 여러 cycle copies가 함께 표시되는지.
- [ ] frame N playback/direct seek/step 결과가 같은지.
- [ ] One Shot→Cyclic→One Shot 즉시 preview가 갱신되는지.
- [ ] 주기 편집이 preview/generated output을 갱신하는지.
- [ ] Mode/Period 각각 Undo/Redo 한 단계, refresh/no-op는 Undo 없음.
- [ ] Invalid period/birth span/active count는 이전 값으로 돌아가고 이유를 표시하는지.
- [ ] Save/Reload 후 mode/period와 출력 보존.
- [ ] G+D+N+Scale+Color+Opacity+Additive 전체 조합.
- [ ] Parent/parent_offset/Keep World/System/Surface/2.5D/Revolution 보존.
- [ ] gate 전에는 없음, gate 순간에는 prewarm 상태로 등장.
- [ ] N이 Period 배수인 PNG sequence: 마지막 PNG=첫 PNG가 아닌 가상 F(N)=F(0) 계약.
- [ ] Layer/Parent/global tracks가 비주기적이면 전체 seamless가 보장되지 않는다는 설명이 보이는지.

반복 주기는 1..512, 기본24. Count는 주기당 전체 개수이며 Rate API가 아니다.
동시 copy 상한4096은 실시간 FPS 보장이 아니다. 자동 테스트는 자연스러움을 판단하지 않는다.

## v0.0.21 Smooth Positional Noise — Windows 네이티브 GUI에서 사용자 확인 필요 (Codex 미수행)

- [ ] Noise OFF에서 v0.0.20과 같은 경로·픽셀인지 확인한다.
- [ ] Strength 2, Frequency 0.03에서 부드럽고 느린 drift, 0.1에서 조금 빠른 흔들림, 0.5~1.0에서 빠른 변화가 보이는지 확인한다.
- [ ] 새 Particle가 태어나는 프레임에서 Noise 때문에 생성 위치가 튀지 않는지 확인한다.
- [ ] 같은 emitter의 여러 Particle가 동일한 흔들림을 공유하지 않는지, 같은 Seed로 재생하면 각각의 path가 재현되는지 확인한다.
- [ ] 프레임 N까지 재생·N 직접 클릭·frame step·full render·PNG 출력의 위치와 픽셀이 같은지 확인한다.
- [ ] Gravity + Drag + Noise에서 기본 움직임만 감속하고 Gravity와 Noise는 실제 시간대로 계속 진행하는지 확인한다.
- [ ] Smoke/Dust/Ember/Orbit Wisp/Hit Spark 예시에서 Noise가 부드러운 경로 변화인지 확인한다. 유체 난류처럼 보인다고 단정하지 않는다.
- [ ] Gravity + Drag + Noise + Scale + Color + Opacity + Additive를 동시에 켜도 각 채널이 독립적으로 유지되는지 확인한다.
- [ ] Noise 활성화, 강도, 변화 속도 편집이 각각 Undo/Redo 한 단계이고 동일 값/Inspector refresh에는 Undo가 생기지 않는지 확인한다.
- [ ] Layer A Noise ON/3.125/0.0375와 Layer B OFF/8.75/0.2 사이 A→B→A 선택에서 값과 비활성 상태가 보존되는지 확인한다.
- [ ] 저장·재열기에서 Noise가 보존되고 format v17 파일은 Noise OFF로 열리며 열기만으로 원본을 수정하지 않는지 확인한다.
- [ ] Parenting, parent_offset, Keep World, System/Surface Transform, 2.5D에서 Noise 방향·변위가 기존 로컬 motion과 일관적인지 확인한다.
- [ ] Resource Editor Overscan은 편집 미리보기만 확장하고 PNG는 원래 출력 크기로 엄격히 잘리는지 확인한다.

## v0.0.20 Particle Drag — Windows 네이티브 GUI에서 사용자 확인 필요 (Codex 미수행)

- [ ] Drag OFF 및 Drag ON/Strength 0에서 v0.0.19과 같은 경로·픽셀을 확인한다.
- [ ] 빠른 Linear particle에 Drag 0.001, 0.01, 0.1, 0.2를 적용해 이동 간격이 점차 줄고 강도가 클수록 더 빠르게 감쇠하는지 확인한다.
- [ ] 수평 Linear + Gravity + Drag에서 수평 이동은 느려지지만 Gravity의 아래쪽 가속은 계속되는지 확인한다. Drag는 Gravity의 물리적 공기 저항이 아니다.
- [ ] Orbit에서 반지름·중심·초기 위상은 유지되고 회전만 느려지는지 확인한다.
- [ ] Helix에서 반지름·축·초기 위상은 유지되고 회전과 축 방향 진행이 함께 느려지는지 확인한다.
- [ ] 생성 시점이 다른 particle에서 오래된 particle이 더 감쇠되고 새 particle은 초기 속도를 유지하는지 확인한다.
- [ ] 순차 재생 후 프레임 N, 다른 프레임에서 N 직접 클릭, frame step N, export N의 픽셀이 일치하는지 확인한다.
- [ ] Gravity + Drag + Scale + Color + Alpha + Additive 조합이 서로 독립적으로 유지되는지 확인한다.
- [ ] Drag toggle 및 Strength 수락 편집이 각각 Undo/Redo 한 단계인지, 동일 값과 Inspector refresh는 Undo/Dirty를 만들지 않는지 확인한다.
- [ ] Layer A Drag ON/0.1375, Layer B Drag OFF/0.03125 설정 후 A→B→A 선택에서 값과 비활성 값이 정확히 보존되는지 확인한다.
- [ ] 저장·재열기에서 Drag 설정이 유지되고 format v16 파일은 Drag OFF/0으로 열리되 열기만으로 원본이 변경되지 않는지 확인한다.
- [ ] Parenting, parent_offset, Keep World, System/Surface Transform, 2.5D와 Drag를 함께 켜고 경로 이상이 없는지 확인한다.
- [ ] Resource Editor Overscan은 편집 미리보기만 확장하고 최종 PNG는 원래 출력 크기에 엄격히 잘리는지 확인한다.

## v0.0.19 Particle Gravity

- [ ] Gravity OFF에서 기존 v0.0.18 Effect의 trajectory와 픽셀이 같은지 확인한다.
- [ ] 양수 Gravity의 Falling Debris/Hit Spark가 처음 속도를 유지한 채 점점 아래로 휘는지 확인한다.
- [ ] 음수 Gravity의 Rising Ember가 위쪽으로 가속되는지 확인한다.
- [ ] 지속 방출에서 새 Particle과 오래된 Particle의 변위가 각 birth age에 맞게 다른지 확인한다.
- [ ] 재생으로 Frame N에 도달한 위치와 다른 Frame에서 N을 직접 클릭한 위치가 같은지 확인한다.
- [ ] Linear에는 ballistic endpoint가, Orbit/Helix에는 radius·phase·axis를 보존한 전체 drift가 나타나는지 확인한다.
- [ ] Gravity + Scale + Color + Additive를 동시에 켰을 때 네 기능이 독립적으로 유지되는지 확인한다.
- [ ] Gravity toggle과 Strength 입력이 각각 Undo/Redo 한 단계이며 같은 값/refresh에는 Undo가 생기지 않는지 확인한다.
- [ ] A: ON/1.375, B: OFF/-0.625를 설정하고 A→B→A 선택 후 exact하게 보존되는지 확인한다.
- [ ] Save/Reload 후 enabled/strength가 exact하고 format 15 프로젝트는 OFF/0으로 열리는지 확인한다.
- [ ] Parent/parent_offset/Keep World/System/Surface/Rotation X·Y·Z/Perspective와 함께 trajectory를 확인한다.
- [ ] 출력 밖 Particle은 Editor Overscan 계약을 유지하고 최종 PNG는 Composition 크기로 strict clip되는지 확인한다.
- [ ] Windows native GUI manual QA: **수행하지 않음**. 사용자 승인 전 실제 네이티브 클릭/시각 검증은 주장하지 않는다.

## v0.0.18 Particle Additive Blend

- [ ] Particle Emission Resource Layer의 Rendering에서 Normal/Additive 두 항목만 보이고 기본값이 Normal인지 확인한다.
- [ ] 반투명 Particle 여러 개를 같은 위치에 겹쳐 Additive가 Normal보다 밝은/높은 누적 기여도를 만드는지 확인한다.
- [ ] 아래에 어두운 Normal Effect Layer를 두고 위 Particle Layer를 Additive로 바꾸면 최종 Canvas가 실제로 밝아지는지 확인한다.
- [ ] Additive 결과 위에 불투명 Normal Layer를 올리면 기존 Source Over 순서대로 덮이는지 확인한다.
- [ ] source alpha, Particle Opacity, Resource Layer opacity를 각각 낮추어 가산 기여도가 함께 낮아지는지 확인한다.
- [ ] Scale+Color over Lifetime+Additive를 동시에 켜고 각 기능이 서로 값을 초기화하지 않는지 확인한다.
- [ ] Linear/Orbit/Helix, Parenting, System/Surface 2.5D, 여러 회전수에서 경로와 seed는 유지되고 합성만 달라지는지 확인한다.
- [ ] Normal→Additive→Normal 전환 때 Playback/스크럽에 이전 모드의 stale cache frame이 남지 않는지 확인한다.
- [ ] Blend Mode 선택 한 번이 Undo 한 번으로 복원되고 Redo되며, 같은 값을 다시 선택하거나 Inspector refresh/selection만으로 Undo가 생기지 않는지 확인한다.
- [ ] Current Preview, Full Playback, Bake/Generated Output, PNG decoded 결과를 같은 프레임에서 비교한다.
- [ ] 투명 checkerboard 색상이 Additive 계산에 섞이지 않고 최종 RGBA 뒤에서만 표시되는지 확인한다.
- [ ] PNG를 외부 도구에서 열어 baked 픽셀은 같지만 별도 Additive Blend metadata/instruction은 없음을 확인한다.
- [ ] Windows native GUI 수동 QA: **수행하지 않음**. 이 항목들은 사용자 승인 전 실제 Windows 환경에서 확인한다.

## v0.0.17 Particle Color over Lifetime

- [ ] Start Yellow, End Red, Linear로 설정하고 각 Particle이 자신의 birth 시점부터 색이 변하는지 확인한다.
- [ ] 지속 emission에서 같은 Effect frame에 보이는 Particle들이 서로 다른 lifetime 색 진행률을 갖는지 확인한다.
- [ ] Scale 0→1과 Color White→Orange를 함께 켜 두 채널이 서로 초기화하거나 덮어쓰지 않는지 확인한다.
- [ ] Particle opacity를 0.4로 고정하고 Color Lifetime 재생 중 투명도가 임의로 변하지 않는지 확인한다.
- [ ] Linear, Ease In, Ease Out, Ease In/Out의 RGB 변화 속도 차이를 확인한다.
- [ ] sentinel RGB/Easing을 설정하고 다른 Layer 선택 후 돌아왔을 때 exact하게 유지되는지 확인한다.
- [ ] Color picker를 취소하거나 같은 색을 선택했을 때 Dirty/Undo가 생기지 않는지 확인한다.
- [ ] Enable, Start Color, End Color, Easing 각각이 Undo/Redo 한 단계인지 확인한다.
- [ ] Save/Reload 후 enabled/start/end/easing이 exact하고 Alpha Easing도 유지되는지 확인한다.
- [ ] Linear, Orbit, Helix에서 trajectory는 같고 RGB만 lifetime에 따라 바뀌는지 확인한다.
- [ ] Resource Editor Overscan outside artwork 표시와 최종 Effect Export strict clipping이 구분되는지 확인한다.
- [ ] 이 목록은 Windows native GUI 수동 QA용이며 Codex는 실제 Windows native GUI 수동 QA를 수행하지 않았다.

## v0.0.16 Alpha Easing / Scale over Lifetime

- [ ] Particle Alpha Easing을 Ease Out으로 바꾸고 다른 Layer를 선택했다가 돌아와도 Ease Out이 유지되는지 확인한다.
- [ ] 프로젝트를 저장하고 다시 연 뒤 Alpha Easing과 Scale Lifetime의 Enabled/Start/End/Easing이 exact하게 유지되는지 확인한다.
- [ ] Scale over Lifetime을 끄면 Start/End/Easing 입력이 비활성화되고, 다시 켜면 이전 값이 보존되는지 확인한다.
- [ ] Grow: Start 0, End 1, Ease Out에서 각 Particle이 자기 생성 시점부터 커지는지 확인한다.
- [ ] Shrink: Start 1, End 0, Ease In에서 마지막 표시 프레임까지 축소되는지 확인한다.
- [ ] Over Time 방출에서 서로 다른 birth time의 Particle들이 같은 Effect frame에서도 서로 다른 크기 진행률을 보이는지 확인한다.
- [ ] Initial Scale Min/Max가 다른 상태에서 각 Particle의 상대 크기 차이가 lifetime multiplier와 곱해져 유지되는지 확인한다.
- [ ] Linear, Orbit, Helix 각각에서 위치 경로는 유지되고 크기만 lifetime에 따라 바뀌는지 확인한다.
- [ ] Enabled, Start, End, Easing 편집 각각이 Undo 한 번으로 정확히 되돌아가고 Redo되는지 확인한다.
- [ ] 여러 Effect Layer 선택 상태에서는 Primary logical Resource Layer만 Lifetime 설정이 바뀌는지 확인한다.
- [ ] Overscan을 포함한 Resource를 Particle source로 사용했을 때 Resource Editor에서는 출력 영역 밖 artwork가 보이고, 최종 Effect PNG는 Output Frame 크기로 strict clip되는지 확인한다.
- [ ] 이 목록은 Windows native GUI 수동 QA용이며 Codex 자동 테스트가 실제 클릭 검증을 대신하지 않는다.

## v0.0.15 Timeline Snapping

- Resource fixture: Layer A Position X 2/8, Rotation Z 3/10, Layer B Opacity 5/12를 만들고 보이는 다른 Key 근처에서 Snap guide와 1-based target 상태를 확인한다.
- 2/5/8 Multi-Key 묶음을 Frame 14 target 근처로 이동하여 하나의 shared delta와 상대 간격 보존을 확인한다.
- Playhead를 Frame 18에 둔 뒤 Move 및 Alt-drag Duplicate가 Playhead guide에 붙고 source/value/easing이 보존되는지 확인한다.
- earliest Key→Start, latest Key→End를 확인하고 same-track collision 후보는 건너뛰며 valid unsnapped drag를 막지 않는지 확인한다.
- Snap OFF에서 기존 v0.0.14 integer-frame Move/Duplicate가 그대로이고 toggle이 Dirty/Undo를 만들지 않는지 확인한다.
- All/Animated/Selected Reveal 및 Group collapse에서 숨겨진 Key가 target이 되지 않는지 확인한다.
- 8/32/64/160 px-per-frame와 Windows DPI 배율에서 약 8 logical px의 체감 threshold와 guide 위치를 확인한다.
- 실제 Windows GUI 수동 QA는 사용자가 수행하며, Codex 검증은 Qt/QTest offscreen 자동화에 한정된다.

## v0.0.15 Timeline / Editor Command Bar UI Polish

- [ ] Resource Timeline에서 Frame/Playback, Key Navigation, View, Snap, Key Editing과 별도 Layer/Hierarchy/State/Order command bar가 기능군별로 읽히는지 확인한다.
- [ ] Effect Timeline에서 Playback/FPS, Key Navigation, View/Snap과 별도 Frame/Layer Structure command bar가 섞이지 않는지 확인한다.
- [ ] 한국어/English에서 Fit Timeline, Fit Visible Keys, Fit Selected Keys와 Reveal 항목이 축약·혼합 표기 없이 표시되는지 확인한다.
- [ ] 12/24-frame Timeline 오른쪽이 inactive time area로 이어지며 실제 duration, Zoom/Pan, current frame, key selection, Snap guide가 유지되는지 확인한다.
- [ ] 1280×720, 1600×900, 1920×1080에서 command bar 겹침·필수 버튼 잘림·음수 geometry가 없는지 확인한다.
- [ ] Effect Library의 Source/Animation 영역은 필요한 높이를 유지하고 Resource Layer 목록에 5~8 Layer, Group, Parent badge, L/S, 긴 이름을 읽을 공간이 우선 배분되는지 확인한다.
- [ ] Resource Inspector에서 정보/metadata와 Add as Effect Layer CTA가 분리되고, Effect Inspector의 section/row spacing과 짧은 설명 tooltip이 자연스러운지 확인한다.
- [ ] Windows 100%/125%/150% DPI에서 separator, glyph button, Reveal combo, Snap toggle, Timeline inactive area와 양쪽 Inspector scroll을 반복 확인한다.
- [ ] 실제 Windows GUI 수동 QA는 사용자가 수행하며 Codex는 offscreen geometry/QTest 결과만 보고한다.

## v0.0.14 Alt-drag Multi-Key Duplicate

- Resource와 Effect Timeline에서 단일 Key 및 여러 Track/Layer의 선택 Key를 `Alt+Drag`하여 원본은 유지되고 복제본만 생성되는지 확인한다.
- 복제 직후 새 Key 묶음과 Primary counterpart가 선택되어 같은 delta로 연속 복제가 가능한지 확인한다.
- Value, mixed Easing, 720°/1080°/-450° Rotation 값과 상대 Frame 간격이 정확히 유지되는지 확인한다.
- Destination existing/source collision, 최소/최대 Frame 초과, delta 0이 모두 전체 거부되고 Undo/Dirty가 추가되지 않는지 확인한다.
- Drag 중 Alt를 놓아도 Duplicate 모드가 유지되고, Escape가 ghost만 제거하며 Clipboard payload와 Layer selection을 바꾸지 않는지 확인한다.
- 8/64/160 px-per-frame에서 frame delta가 같고, Middle Pan, Marquee, Ctrl+Wheel Zoom, Fit Selected, Previous/Next 및 Reveal이 유지되는지 확인한다.

## v0.0.13 Timeline Navigation & Reveal

- [ ] 특정 Key 위에서 Ctrl+Wheel Up/Down 후 해당 Frame이 화면 X에서 크게 튀지 않고 Playhead와 Key 데이터가 유지되는지 확인한다.
- [ ] Zoom-in 후 Middle Drag와 Shift+Wheel로 시간축만 이동하고 Scrub, Marquee, Key Drag가 시작되지 않는지 확인한다.
- [ ] Fit, Keys, Sel 버튼이 각각 전체 Duration, 보이는 Key 범위, 선택 Key 범위를 적절한 margin으로 표시하는지 확인한다.
- [ ] Ctrl+Alt+Left/Right와 키 이동 버튼이 현재 보이는 Track의 가장 가까운 이전/다음 Key Frame으로만 이동하는지 확인한다.
- [ ] All/Animated/Selected 모드에서 Resource Group ancestor, collapse, Multi-Layer selection과 Parent badge가 유지되는지 확인한다.
- [ ] Effect의 System/Particle/Motion Track 필터가 logical Effect Layer selection을 사용하고 fake Group을 만들지 않는지 확인한다.
- [ ] Filter로 숨겨진 Key selection이 제거되지만 Layer selection, Dirty, Undo, Render 상태는 바뀌지 않는지 확인한다.
- [ ] 좁거나 넓은 Zoom에서 Marquee, Multi-Key Drag, Collision, Copy/Paste Frame 결과가 동일한지 확인한다.

## Timeline Multi-Key Copy / Paste

- [ ] Resource의 여러 Layer/Property에서 6개 이상 Key를 선택하고 Ctrl+C 후 Playhead를 옮겨 Ctrl+V 했을 때 earliest Key가 Playhead에 정렬되고 상대 간격이 유지되는지 확인한다.
- [ ] 붙여넣기 한 번을 Ctrl+Z/Ctrl+Y 한 번으로 전체 제거·복원하고, Redo 전에 시스템 Clipboard를 바꿔도 결과가 같음을 확인한다.
- [ ] Rotation 0°/720°/1080°와 서로 다른 Easing을 함께 Copy/Paste해 값과 Easing이 정확히 유지되는지 확인한다.
- [ ] 대상 중 하나에 기존 Key가 있거나 Timeline 끝을 넘을 때 부분 생성 없이 non-modal 상태만 표시되는지 확인한다.
- [ ] Effect의 System Rotation, Position, Orbit Radius, Helix Axis Key를 함께 Copy/Paste하고 logical Layer identity와 Generated Layer 연결이 유지되는지 확인한다.
- [ ] Resource payload를 Effect에, Effect payload를 Resource에 붙여넣을 때 안전하게 거부되는지 확인한다.
- [ ] Copy 뒤 Layer/Track 삭제, Group collapse, Project New/Open 후 Paste가 crash 없이 일관된 정책으로 처리되는지 확인한다.
- [ ] Timeline 밖의 이름 입력, SpinBox, editable ComboBox에서 Ctrl+C/V가 일반 텍스트 편집으로 동작하는지 확인한다.

## Rotation Revolutions / Advanced Bypass / Ctrl+Wheel

- [ ] Rotation에 `0x + 0°`, `2x + 0°`, `-1x - 90°`를 입력하고 total degree 0/720/-450로 저장·표시되는지 확인한다.
- [ ] 0°→720° Key를 Linear로 재생해 실제 두 바퀴 회전하고 중간값이 360°인지 확인한다.
- [ ] Rotation Gizmo를 359° 경계 너머로 드래그해 361° 이상으로 연속 증가하며 1°로 떨어지지 않는지 확인한다.
- [ ] Effect Advanced OFF에서 System/Surface만 bypass되고 값·Keyframe은 유지되며 ON에서 이전 RGBA가 복원되는지 확인한다.
- [ ] Advanced OFF에서 System Gizmo가 사라지고 Particle Motion은 계속 동작하는지 확인한다.
- [ ] Static/Animated/현재 Key 숫자 입력을 Ctrl+Wheel로 minimum/maximum까지 반복하고 경계 추가 입력에 Undo나 Auto-Key가 생기지 않는지 확인한다.
- [ ] Effect Add/Remove/Reorder 뒤 Ctrl+Wheel, Undo/Redo를 20회 반복해 Unexpected Error가 발생하지 않는지 확인한다.

## Effect Multi-Resource Layer Workflow

- [ ] Slash, Smoke, Spark, Glow Resource를 Effect Library의 명시적 메뉴로 각각 추가하고 선택한 Resource가 정확히 연결되는지 확인한다.
- [ ] Smoke를 두 번 추가해 서로 다른 Effect Layer ID와 고유 기본 이름을 가지며 같은 Resource 원본을 공유하는지 확인한다.
- [ ] Single/Particle Inspector에서 Effect Layer 이름을 바꿔도 Resource 이름은 유지되고 중복 이름이 자동으로 고유해지는지 확인한다.
- [ ] Effect Library 항목에 Visibility, Effect Layer 이름, Resource 이름, Single/Particle Placement가 함께 보이는지 확인한다.
- [ ] 목록 위가 Canvas Front인지 반투명 겹침으로 확인하고 Move Front/Back이 출력·선택을 즉시 갱신하며 Undo/Redo 한 번으로 왕복하는지 확인한다.
- [ ] 1 Single과 Linear/Orbit/Helix Particle 세 Layer를 함께 두고 범위, Visibility, 2.5D Transform, Motion, Keyframe이 서로 섞이지 않는지 확인한다.
- [ ] 선택과 Timeline Scrub만으로 모델, Undo Stack 또는 렌더 Cache revision이 바뀌지 않는지 확인한다.
- [ ] Effect Layer 삭제 후 Resource 원본이 남고 Undo가 전체 설정을 복원하며 마지막 Effect Layer도 안전하게 삭제/복원되는지 확인한다.
- [ ] 사용 중 Resource 삭제가 거부되고 모든 참조 Effect Layer를 제거한 뒤에만 삭제되는지 확인한다.
- [ ] Save/Reload 후 4개 이상 Effect Layer의 순서, 중복 Resource 참조, 이름, Placement, Transform, Motion, Keyframe이 동일한지 확인한다.
- [ ] Direct Preview, Playback, Bake, Project Compose, PNG와 PNG Sequence의 같은 Frame 결과가 일치하는지 확인한다.

## Multi-Image Resource Layer Workflow

- [ ] PNG 에셋 A/B/C를 가져와 하나의 Resource에 세 Layer로 추가하고 각 Layer의 Source 이름과 선택 Highlight가 명확한지 확인한다.
- [ ] 목록 위가 Canvas Front인지 겹친 이미지로 확인하고 위/아래 버튼 변경이 즉시 반영되며 Undo/Redo 한 번으로 왕복하는지 확인한다.
- [ ] A Position, B Rotation X/Y/Z, C Scale/Perspective/Opacity/Pivot를 서로 다르게 바꿔 다른 Layer와 원본 Asset에 섞이지 않는지 확인한다.
- [ ] Layer별 Visibility와 포함형 Start/End 범위를 다르게 두고 Scrub/Playback에서 지정 Frame에만 합성되는지 확인한다.
- [ ] A Rotation, B Position, C Opacity의 첫 Key와 다른 Frame Conditional Auto-Key가 각 Layer의 Diamond/Timeline row에 독립적으로 표시되는지 확인한다.
- [ ] Layer Add/Remove/Reorder를 Undo/Redo하고 Remove 후에도 원본 Asset이 남으며 사용 중 Asset 삭제가 거부되는지 확인한다.
- [ ] Save/Reload 후 Layer 순서, Source, 이름, Transform, Pivot, Visibility, 범위와 Keyframe이 동일한지 확인한다.
- [ ] 완성된 3-Layer Resource를 Effect Single과 Particle에 추가해 내부 합성이 하나의 Resource appearance로 사용되는지 확인한다.

## Keyframe Editing Foundation

- [ ] Resource Rotation Z에 Frame 1 = 0°, Frame 11 = 90° Key를 추가하고 Timeline의 첫 칸과 마지막 칸에 `◆`가 정확히 보이는지 확인한다.
- [ ] Frame 6으로 스크럽해 Inspector와 Canvas가 같은 보간값을 보이고, `◇` Animated/no-current-key 상태에서도 숫자 편집이 가능한지 확인한다.
- [ ] Frame 6에서 실제 값을 바꾸면 `◆` Key 하나가 자동 생성되고, 값 변화 없이 클릭만 하면 Key가 생기지 않는지 확인한다.
- [ ] Frame 6의 `◇`를 눌러 평가값 그대로 Explicit Key 하나를 생성할 수도 있고, 같은 Frame에 중복 Key가 생기지 않는지 확인한다.
- [ ] `◆`를 눌러 현재 Key를 삭제한 뒤 Inspector, Canvas, Timeline marker가 즉시 같이 갱신되는지 확인한다.
- [ ] 마지막 Key를 삭제해도 값이 0으로 튀지 않고 해당 Key 값이 정적 값으로 남는지 확인한다.
- [ ] Resource Timeline의 Key를 빈 Frame으로 Drag해 값/이징은 유지되고 Frame만 이동하는지, 기존 Key 위로의 이동은 거부되는지 확인한다.
- [ ] Key Add, 값 Edit, Move, Delete 각각에서 Undo/Redo가 exact하고, 기즈모 Drag 중 Escape는 Undo를 남기지 않는지 확인한다.
- [ ] Animated/no-key Frame에서 Gizmo Press만 하면 Key가 없고, 첫 Drag delta에 즉시 Timeline `◆`가 나타나며, Escape하면 Key와 Marker가 함께 제거되는지 확인한다.
- [ ] SpinBox 직접 입력, Up/Down, Ctrl+Wheel이 같은 Conditional Auto-Key 정책을 사용하고 일반 Wheel은 값 대신 Inspector를 Scroll하는지 확인한다.
- [ ] SpinBox에 `210`, `-120`, `1.25`를 직접 타이핑하는 동안 Model·Canvas·다이아몬드가 유지되고 Enter 또는 다른 Widget 클릭 시 최종 값이 한 번만 반영되는지 확인한다.
- [ ] Animated/no-current-key 숫자 입력은 타이핑 중 `◇`를 유지하고 최종 Commit에서만 `◆`와 Undo 1개를 만들며, 기존 키 입력도 중간 숫자 없이 한 번만 갱신되는지 확인한다.
- [ ] Effect Single/Particle System Transform의 `◇/◆` 상태와 Timeline diamond가 현재 Frame에 맞고, 현재 Key에서 기즈모가 base가 아닌 Key를 바꾸는지 확인한다.
- [ ] Orbit radius 등 Motion Key를 만든 뒤 Linear → Orbit으로 전환해 Track이 보존되는지 확인한다.
- [ ] Save, 앱 종료, Reload 후 Key frame/value/easing, 대표 Frame RGBA, Bake, PNG Sequence가 저장 전과 같은지 확인한다.

## 2.5D Inspector Architecture

- [ ] Resource Editor의 X/Y/Z 회전, 크기, 피벗, 원근이 기본 Sprite 외형 편집 기능으로 이해되는지 확인한다.
- [ ] Effect Editor의 일반 Particle 흐름에서 System Space와 Surface Transform이 앞에 나와 혼란을 만들지 않는지 확인한다.
- [ ] 기본 접힌 `고급 / Advanced`를 열어 `시스템 공간 변형`과 `표면 변형 (호환성)`의 역할 차이를 설명만 읽고 구분할 수 있는지 확인한다.
- [ ] Surface Transform이 non-identity인 기존 프로젝트에서 Advanced를 닫아도 `표면 변형이 적용됨` 상태가 보이는지 확인한다.
- [ ] `리소스 원근`, `움직임 로컬 원근`, `시스템 원근`, `표면 원근`의 Tooltip이 각각 Sprite, Motion path, System coordinate, post-raster plane을 가리키는지 확인한다.
- [ ] Advanced 접기/펴기만으로 Dirty 표시, Playback 정지·캐시 무효화, Canvas 변화가 발생하지 않는지 확인한다.

## Asset Preview Pivot / Navigation / 2.5D Raster Edge

- [ ] Resource 생성 전 28×28 Asset의 `(14,14)` 및 29×29 Asset의 `(14.5,14.5)` Pivot이 이미지 중앙에 `십자 + 원 + P`로 보인다.
- [ ] Asset Pivot X/Y 입력과 중앙 정렬 버튼이 Preview Marker를 즉시 이동시키며 Source RGBA와 Project render에는 Marker가 포함되지 않는다.
- [ ] Asset 선택 시 24~48 logical-pixel 범위의 여백으로 전체 이미지가 Fit되고, `맞춤`과 `100%` 버튼이 동작한다.
- [ ] Wheel Up/Down이 커서 위치 기준으로 10%~3200% Zoom하고 확대된 Pixel Art가 흐려지지 않는다.
- [ ] Middle Mouse Drag Pan 뒤 이미지와 Pivot Marker가 같은 offset으로 이동하며 Asset Pivot/Dirty 상태는 바뀌지 않는다.
- [ ] Windows DPI 100%, 125%, 150%에서 Fit 여백, Marker 위치, Wheel Zoom, Pan을 확인한다.
- [ ] 28×28 transparent-margin directional fixture를 Rotation X/Y 5°, 15°, 30°, 60°, 89°와 Perspective 0/0.2/0.6/1.0에서 확인해 우측·하단·우하단 색이 Quad 밖으로 늘어나지 않는다.
- [ ] Rotation X/Y 0°, 0.001°, 0.1°, 1° 및 양·음 각도에서 갑작스러운 1px streak, 0.5px Pivot 이동, Local Z plane-normal 회귀가 없다.

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
- [ ] Rotate X/Y/Z 버튼을 각각 선택해 원형 Handle을 실제로 Drag하고 Canvas와 해당 Inspector 숫자가 즉시 함께 변하는지 확인한다.
- [ ] Rotate X/Y를 edge-on ±90°를 지나 계속 Drag해 앱 예외·입력 중단 없이 반대쪽 각도까지 이어지는지 확인한다.
- [ ] Rotate Z를 ±180° 경계 근처에서 조작하고 Shift 15° snap, Release, Undo/Redo와 Escape를 확인한다.
- [ ] Rotation keyframe이 현재 Frame에 있는 경우 해당 Key 값이 바뀌고 다른 Frame의 Key는 유지되는지 확인한다.
- [ ] Zoom 25/100/400%, Pan 적용, Windows DPI 100/125/150%에서 Handle hit area와 조작 방향을 확인한다.

## 2.5D Interaction & Stability Completion

- [ ] Particle 100인 Effect Layer에서 2초 이상 연속 Drag하고 Exact 결과가 늦게 교체되는 동안 Gizmo, 활성 Handle, XYZ 축, Rotation Ring, Motion Guide가 한 번도 사라지지 않는지 확인한다.
- [ ] Linear에서는 Orbit/Helix 그룹이 숨고, Orbit에서는 Helix 축만 숨으며, Helix에서는 필요한 전체 그룹이 표시되는지 확인한다.
- [ ] 한국어/영어 Motion Mode와 회전 방향에 내부 값(`helix`, `counter_clockwise`, `center_x`)이 노출되지 않고 긴 Label이 글자 단위로 줄바꿈되지 않는지 확인한다.
- [ ] Motion 각 항목의 Tooltip과 각도 `°`, 회전 횟수 `회/turns` 단위가 실제 의미와 맞는지 확인한다.
- [ ] 0~1 Opacity/Perspective를 0.95 부근에서 Up, 0.05 부근에서 Down, 범위 밖 직접 입력, Ctrl+Wheel로 조작해 0/1에서 제한되고 앱이 종료되지 않는지 확인한다.
- [ ] 방향성 강한 Sprite를 X 55°, Y 20°, Perspective 활성 상태로 둔 뒤 Z를 0→360° 돌려 Plane 기울기는 유지되고 무늬만 Plane 안에서 도는지 확인한다.
- [ ] 같은 Resource Z 변경 전후 Particle 중심, Linear, Orbit, Helix 경로가 움직이지 않는지 확인한다.
- [ ] Resource Preview, Effect Current Frame, Playback, Bake, PNG, PNG Sequence에서 Local Z Spin 의미가 같은지 확인한다.

## Resource 2.5D Identity / Pivot / Effect X Gizmo

- [ ] `테스트소스.png`(28×28)를 가져와 Source 크기의 Resource를 만든 직후 원본 형태·색·투명 여백이 변하지 않고 오른쪽/아래로 1px 늘어나지 않는지 확인한다.
- [ ] 불투명 픽셀 외곽과 초록 Selection/Projected Box가 맞고 Box 밖으로 픽셀이 삐져나오지 않는지 100%와 400% Zoom에서 확인한다.
- [ ] Pivot Tool에서 `(14,14)`가 28×28 Sprite의 중앙에 `십자 + 원 + P`로 보이며, Pivot X/Y를 바꾸면 Sprite/Selection이 Marker에 대해 즉시 이동하는지 확인한다.
- [ ] Pivot Marker가 Preview/Bake/PNG/Particle Sprite 결과에 포함되지 않고 Zoom 25/100/400%와 Pan 뒤에도 같은 로컬 Pivot을 가리키는지 확인한다.
- [ ] X/Y Tilt와 Local Z Spin 뒤 Pivot Marker, Projected Quad, Z Ring이 같은 평면 수학을 사용하며 비중앙 Pivot을 중심으로 회전하는지 확인한다.
- [ ] Effect Move XYZ의 빨간 X에 Hover해 Layer Space X 이동 설명이 보이고, Motion Guide Handle과 겹쳐도 X를 Drag하면 Layer와 Guide 및 Inspector 위치 X가 함께 변하는지 확인한다.
- [ ] 빨간 X Drag Release는 Undo 하나, Escape는 원래 Position X와 Guide로 복원되고 Undo를 만들지 않는지 확인한다.

## Effect Playback Prebuffer

- [ ] 600×600·12FPS·12프레임·5레이어·Particle 100에서 Play 후 `재생 준비 중… n / 12`가 갱신되고 창 이동과 Stop이 반응하는지 확인한다.
- [ ] 준비 완료 순간 Frame 1부터 재생하며 첫 번째 Loop가 두 번째·세 번째 Loop와 같은 속도로 보이는지 확인한다.
- [ ] 준비 중 Stop, 편집, Gizmo 조작, New/Open을 실행해 늦은 프레임이 설치되거나 재생이 저절로 시작하지 않는지 확인한다.
- [ ] Stop 후 편집 없이 다시 Play하면 준비 표시 없이 즉시 시작하고, Pan/Zoom/Selection 뒤에도 같은지 확인한다.
- [ ] 31프레임 이상 Sequence는 전체 완료를 기다리지 않고 Ready Buffer 뒤 시작하며 underrun에서 UI가 Exact Render로 멈추지 않는지 확인한다.

## Effect Renderer Throughput

- [ ] 600×600·5 Layer·Particle 100 프로젝트에서 Cold Play 준비가 이전 약 1초보다 짧아졌고 첫 Loop가 완전한지 확인한다.
- [ ] 완전 투명, 작은 불투명/반투명, 화면 밖 Resource Layer가 섞인 프로젝트에서 Direct/Playback/Bake/PNG 결과를 비교한다.
- [ ] Single static Resource가 포함된 12프레임 재생을 Stop/Play하고 편집·Undo/Redo 뒤 stale 결과가 보이지 않는지 확인한다.
- [ ] Linear/Orbit/Helix Particle이 겹치는 장면에서 생성 순서와 Z 정렬, 반투명 경계가 이전 저장 결과와 동일한지 확인한다.
- [ ] Rotation X/Y, Perspective, Opacity, Canvas 경계 Crop에서 최근접 픽셀과 Alpha가 변하지 않는지 확인한다.

## Particle Current-frame consistency

- [ ] Orbit/Helix Motion을 변경하고 일반 Save 후 앱을 재시작해 프로젝트를 연 다음, 정지 Timeline의 1~24 Frame을 순서대로 클릭해 Particle이 Spawn 지점으로 되돌아가지 않는지 확인한다.
- [ ] `1 → 12 → 3 → 20 → 7`, 역순, 같은 Frame 반복 스크럽 뒤 최종 Frame이 Playback에서 같은 Frame을 정지한 모습과 같은지 확인한다.
- [ ] Play를 Frame N에서 Stop한 직후와 다른 Frame을 클릭했다가 N으로 돌아온 모습이 동일한지 확인한다.
- [ ] Motion/2.5D Gizmo를 움직이다 즉시 다른 Timeline Frame을 클릭해 이전 Frame의 늦은 Preview가 새 Frame에 나타나지 않는지 확인한다.
- [ ] Linear/Orbit/Helix 각각 Bake와 PNG Sequence를 만들고 Timeline의 대표 Frame과 육안 비교한다.

## Resource Playback Speed Range & Undo

- [ ] Particle Emission의 최소/최대 리소스 재생 속도를 `1/1`로 두고 Min에 2와 3을 직접 입력해 즉시 `2/2`, `3/3`으로 표시되며 경고창이나 Unexpected Error가 없는지 확인한다.
- [ ] `2/4`에서 Max를 1.5로 내려 `1.5/1.5`가 되고 Undo 한 번으로 `2/4`, Redo 한 번으로 `1.5/1.5`가 복원되는지 확인한다.
- [ ] Min/Max 각각 Arrow와 Ctrl+Wheel로 범위를 교차하고 상·하한에서 500회 반복해 invalid pair, 추가 Undo, `_UndoIndexRelay::forward(int)` 오류가 없는지 확인한다.
- [ ] 고유한 프레임의 Animated Resource를 1×, 2×, 3×와 1×~3× 범위로 재생해 source frame advance, loop/hold/once 정책과 deterministic seed가 유지되는지 확인한다.
- [ ] 일반 Rotation/Scale/Opacity, Effect Add/Reorder, Resource 이름 변경에서 Undo/Redo를 반복해 indexChanged와 Dirty 표시가 안정적인지 확인한다.

## Layer Workflow Essentials #1 — Duplicate & Drag Reorder

- [ ] 이미지 3개 Resource에서 Keyframe이 있는 Layer를 버튼과 Timeline 포커스 `Ctrl+D`로 복제해 바로 위에 `(2)`, `(3)` 복제본이 생기고 Inspector/Gizmo가 새 ID를 선택하는지 확인한다.
- [ ] Resource 복제본의 Pivot, Rotation Revolution, Position과 Keyframe/Easing을 바꿔 원본 Track이 변하지 않으며 Undo/Redo가 같은 복제 ID와 순서를 복원하는지 확인한다.
- [ ] Resource 5 Layer의 맨 아래 행을 맨 위로 Drag해 Drop indicator, Canvas Front 합성, Timeline Property row와 선택이 즉시 일치하고 Undo 한 번으로 복원되는지 확인한다.
- [ ] Single/Particle Linear/Orbit/Helix가 섞인 Effect에서 Particle Layer를 복제해 Position, Seed, Radius, Phase를 달리하고 두 결과가 독립인지 확인한다.
- [ ] Effect 10 Layer를 여러 칸 Drag해 이동 중 렌더가 반복되지 않고 Drop 한 번에 Current Frame 합성·Inspector·Timeline이 갱신되는지 확인한다.
- [ ] 같은 위치 Drop과 Escape 취소가 Dirty, revision, render, Undo를 만들지 않으며 Save/Reload 후 Resource/Effect 복제 ID·공유 참조·순서가 동일한지 확인한다.

## Layer Lock / Solo

- [ ] Resource Layer를 잠근 뒤 Transform, 숫자 입력, Auto-Key, Keyframe 추가·이동·삭제, Drag, Front/Back, Delete가 막히고 선택·표시·Solo·복제·잠금 해제가 가능한지 확인한다.
- [ ] 잠긴 Resource Layer를 복제하면 새 ID의 복제본도 Lock/Solo를 유지하고, Undo/Redo가 같은 ID와 선택을 복원하는지 확인한다.
- [ ] Resource에서 Solo 1개/여러 개와 Visibility 조합을 바꿔 `visible AND (no solo OR solo)` 규칙으로 Canvas가 즉시 갱신되는지 확인한다.
- [ ] Effect Single/Particle Linear/Orbit/Helix Layer를 잠근 뒤 Layer/Surface Transform, Spawn, Lifetime, Seed, Playback, Advanced, Motion 및 Track 편집과 Drag/Delete가 막히는지 확인한다.
- [ ] Effect의 잠긴 Layer에서도 Visibility, Solo, Duplicate와 Unlock이 가능하고 Generated Layer ID 관계가 유지되는지 확인한다.
- [ ] Effect에서 여러 배치 방식을 섞어 Multi-Solo와 Visibility를 전환하고 Save/Reload 및 Undo/Redo 후 동일한지 확인한다.
- [ ] Solo가 켜진 상태에서 Canvas에는 Solo Layer만 보이지만 PNG, PNG Sequence와 Bake 결과에는 모든 visible Layer가 포함되는지 픽셀 비교한다.

## v0.0.06 Layer Multi-select

- [ ] Resource Layer 목록과 Timeline에서 Click, Ctrl+Click 추가·제거, 정방향/역방향 Shift 범위, 포커스 상태 Ctrl+A가 같은 stable-ID 선택과 Primary를 표시하는지 확인한다.
- [ ] Resource 연속·비연속 선택에서 Duplicate, Drag, Lock/Unlock, Solo/Unsolo, Show/Hide, Front/Back, Delete가 각각 Undo 하나이며 상대 순서와 선택을 Undo/Redo하는지 확인한다.
- [ ] Effect Single, Particle Linear/Orbit/Helix를 섞어 같은 선택·Batch 동작을 확인하고 logical Layer 선택이 Generated Timeline 행에 동기화되는지 확인한다.
- [ ] 잠긴 Layer가 섞이면 Duplicate, Solo, Visibility, Lock/Unlock은 성공하고 Drag, Delete, Front/Back은 부분 변경 없이 거부되는지 확인한다.
- [ ] 선택되지 않은 행 우클릭은 단일 선택하고, 선택된 행 우클릭은 다중 선택을 유지하며 한국어/영어 Batch 메뉴와 선택 개수 안내가 맞는지 확인한다.
- [ ] 다중 선택에서 Inspector, Gizmo, 숫자 입력과 Auto-Key는 Primary 하나만 변경하고 잠긴 Primary는 모두 차단하는지 확인한다.
- [ ] 다중 선택 전후 PNG, PNG Sequence, Bake 결과가 동일하고 Save/Reload 뒤에는 모델 Batch 결과만 유지되며 선택은 안전한 단일 Primary로 복구되는지 확인한다.
- [ ] 100 Layer 선택과 비연속 Drag에서 UI가 응답하며 no-op Drop은 Dirty, revision, render 또는 Undo를 만들지 않는지 확인한다.

## v0.0.07 Layer Group / Hierarchy

- [ ] 한국어/English와 Windows 100%/125%/150% DPI에서 Resource/Effect Group disclosure, 이름 변경, child 들여쓰기, 접기 동기화와 Group 안/밖 Drag indicator를 확인한다.
- [ ] Root Group reorder, Group 내부 reorder, Root↔Group 및 Group A→Group B 이동, same-parent multi-drag, mixed-parent 거부와 Empty Group 유지·복제·삭제를 확인한다.
- [ ] Group Lock 뒤 child Gizmo/숫자/Auto-Key/Keyframe/Drag/Delete가 차단되고 Select, Visibility, Solo, Duplicate, Unlock, Collapse와 Inspect는 가능한지 확인한다.
- [ ] Group Visibility가 Canvas, Playback, PNG, PNG Sequence와 Bake에 반영되고 child own Visibility를 바꾸지 않는지 픽셀 비교한다.
- [ ] Group Solo가 Canvas에만 적용되고 PNG, PNG Sequence와 Bake에는 영향을 주지 않는지 픽셀 비교한다.
- [ ] Resource Timeline collapse와 Effect logical Group/Generated Timeline mapping이 일치하며 Group 자체 Generated Layer나 Property Track이 생기지 않는지 확인한다.
- [ ] 실제 v10 프로젝트를 열어 leaf 순서와 출력이 유지되는지 확인하고, v11 Save As/Reload 뒤 Group ID, flags, children, root order와 Empty Group이 유지되는지 확인한다.
- [ ] Group 생성 전후, Group 해제 전후의 대표 PNG, PNG Sequence와 Bake 결과를 픽셀 비교한다.
# Project-wide stabilization manual pass

## Resource Composition Clip / Overscan — pending Windows GUI approval

Actual Windows GUI manual QA: not performed.

- [ ] Right edge: move half a sprite outside the frame; entire sprite remains visible, outside pixels dimmed, export strictly clipped.
- [ ] Repeat at left, top and bottom edges, including negative coordinates.
- [ ] Rotate 45°, 90°, -45°, 720° and 1080°; inspect border and corner visibility.
- [ ] Scale 2×, 0.5× and non-uniformly, then move the Layer Pivot and rotate/scale again.
- [ ] Tilt X/Y, change Z/perspective and repeat with a source larger than the Composition.
- [ ] Parent position/rotation/scale and Parent+Child multi-selection: inspect world-space pixels and gizmos outside output.
- [ ] Click overscan pixels to select; drag Move/Rotate/Scale/Pivot handles outside output. Verify hidden/soloed groups and inactive frames.
- [ ] Move A outside, select B, Undo/Redo: only A changes and pixels refresh immediately.
- [ ] Zoom, pan and Fit: neutral frame matches true output; checkerboard remains inside output; outside dimming does not hide sprites.
- [ ] Compare Resource export and Add-to-Effect Single/Particle: dimensions unchanged and overscan pixels absent.
- [ ] Recheck Command Bar groups, compact Resource Layer commands, Lock/Solo labels, Order menu, Fit labels and inactive Timeline area.

These are real Windows GUI checks and are not claimed by offscreen automation.

## v0.0.08 Parenting

- [ ] Resource: Set/Clear/Reparent, parent chain, cycle rejection, rename/reorder, Group move/ungroup, Group duplicate remap, and dependent delete safety.
- [ ] Transform: Position/Rotation Z/Scale inheritance, current-world preservation, parent keyframe playback, child Local editing/Auto-Key, and gizmo drag under rotated/scaled parents.
- [ ] Effect: Layer Space parent with Single and Particle Linear/Orbit/Helix; verify Surface Transform, playback speed, seed, motion, generated-layer mapping, visibility, Solo and lock stay independent.
- [ ] Output: compare Canvas, PNG, PNG Sequence and Bake for parented and no-parent fixtures without render-order changes.
- [ ] UI: Korean/English at 100/125/150% DPI, duplicate names in Parent selectors, Primary-only multi-select behavior, row indicators and context Set/Clear Parent actions.

- Startup: first run, accept/reject notice, do-not-show, Help reopen, Korean and space-containing paths.
- Project: New/Open, first and repeated Save, Save As, failed-save close, reopen.
- Import: RGBA/RGB/grayscale PNG, transparent/multi-frame GIF, Aseprite success/failure, move original then reopen embedded project.
- Editing: Composition, Single, Particle Linear/Orbit/Helix, 2.5D, keyframes, Undo/Redo.
- Timeline/output: fast scrub, playback/loop/end frame, Preview/Bake/PNG/sequence pixel comparison.
- UI: Korean/English, 100/125/150% DPI, inspector 280/300/320 px, zoom 25/100/400%, focus-sensitive wheel/Delete/Space/Ctrl+Z/Ctrl+Y/Ctrl+S.

## v9 Integrated Production Workflow Stability QA

The deterministic model/service and offscreen QTest paths are automated. The following remain real Windows GUI checks and are not claimed by automation.

- [ ] Import a real PNG/GIF/Aseprite file, create a Resource, apply Sprite X/Y tilt, Local Z, Pivot and Perspective, then compare Resource Preview at Fit/100% with the source.
- [ ] Add the Resource as Single, then Particle Linear/Orbit/Helix; visually confirm that Resource tilt changes sprite appearance while System Space moves spawn/path/guide coordinates.
- [ ] Play the 600×600, 12 FPS, 12-frame representative project cold and warm; verify PREPARING→PLAYING, zero visible first-loop hitch/drop, responsive Stop, Pan, Zoom and selection.
- [ ] Drag Resource and Effect XYZ gizmos for 1–2 seconds, change Timeline frame during a pending render, and press Escape; verify no stale frame, hidden handle, extra Undo or transient pixel remains.
- [ ] Save, close the actual application, reopen, scrub sequential/reverse/random frames, Bake, and visually compare direct frame, playback stop frame, PNG and PNG Sequence.
- [ ] Exercise New/Open/Close dirty-project dialogs with Save, Discard and Cancel; repeat A/B project opening while watching for stale guides, pixels or transforms.
- [ ] Open an actual v8 project from an external copy, Save As v9, compare representative frames, and independently confirm the original file hash is unchanged.
- [ ] Repeat the workflow on Windows 100/125/150% DPI and Korean/English UI; confirm Advanced status, four distinct Perspective tooltips and narrow Inspector layout.

## v0.0.09 Multi-Transform

- [ ] Selection: select 2 and 3+ Leaf layers, including hidden, parented/free, Parent+Child, locked mixed and Group mixed selections in both editors.
- [ ] Gizmo: verify one World-space Selection Pivot and Move, Rotation Z, Scale X/Y; confirm no-op creates no Undo and each completed drag creates exactly one Undo.
- [ ] Parenting: repeat World Move under rotated/scaled/different parents and a depth-20 chain; confirm Parent+Child is not transformed twice and `parent_offset` is unchanged.
- [ ] Inspector: verify `—` mixed display, absolute Local Position X/Y, Rotation Z and Scale X/Y edits, conditional batch Auto-Key and one-step Undo/Redo.
- [ ] Primary-only isolation: verify Position Z, Rotation X/Y, Perspective, Opacity, Surface Transform, Particle/Motion and Playback Speed only edit the Primary layer.
- [ ] Effect modes: repeat with Single, Particle Linear, Orbit and Helix; confirm generated IDs, Surface Transform and playback settings do not change.
- [ ] Output: compare Canvas, PNG, PNG Sequence and Bake after Multi Move/Rotate/Scale; confirm Selection Pivot and highlights are editor overlays only.
- [ ] UI: verify handle hit targets, mixed fields, help text and Ctrl+A text selection in Korean/English at Windows 100/125/150% DPI.

## v0.0.10 Hierarchy UX Polish

- [ ] Resource Timeline과 Effect Resource Layer 목록에서 Group row, disclosure, Group child indentation, Property track `└`, Parent `[P: …]` badge를 구분한다.
- [ ] own Lock `L`, inherited Group Lock `L*`, Solo, Visibility, Primary `▌`, selected non-primary `•`가 toolbar 및 모델 상태와 즉시 동기화된다.
- [ ] Empty Group이 `(비어 있음)` / `(Empty)`으로 표시되고 fake child row가 생기지 않는다.
- [ ] 긴 Group/Layer/Parent 이름이 상태 영역을 밀어내지 않고 elide되며 hover tooltip에는 전체 이름과 Parent/Lock 이유가 표시된다.
- [ ] Group row 상단/중앙/하단과 Leaf row 상단/하단 drag가 Before/Into/After indicator와 실제 drop 결과에서 일치한다.
- [ ] Empty Group Into, same-parent multi-drag, Group 간 이동을 확인하고 nested Group, locked subtree, mixed-parent target은 금지 피드백과 함께 거부된다.
- [ ] Leaf, Group, multi-select, parented/no-parent, locked 선택의 context menu section과 enable/disable 상태를 확인한다.
- [ ] 단일 disclosure, 모두 펼치기, 모두 접기 후 selection repair가 일치하고 Save 데이터 및 Undo/Dirty 상태가 변하지 않는다.
- [ ] Parent rename과 Group A→B 이동 직후 badge와 indentation이 갱신되고 `parent_id`/`parent_offset`은 유지된다.
- [ ] 한국어/English 및 Windows 100%/125%/150% DPI에서 L/S/앞/뒤 accessible text, tooltip, focus/selection 표시를 확인한다.

## v0.0.10 Editor Layout & Density Polish

- [ ] 1280×720, 1600×900, 1920×1080에서 Resource Browser, Canvas, Inspector, Timeline을 확인하고 겹침·음수 geometry·필수 조작 잘림이 없는지 확인한다.
- [ ] Resource Browser가 약 205 px, Inspector가 약 320 px, Effect Library가 약 250 px, Effect Inspector가 약 340 px로 시작하고 splitter drag 및 재시작 후 유효한 사용자 폭이 유지되는지 확인한다.
- [ ] 창을 좁힐 때 Canvas가 먼저 줄고 Resource/Effect 좌우 패널의 이름, 핵심 입력 및 vertical scrollbar가 계속 사용 가능한지 확인한다.
- [ ] Resource Timeline 높이와 220 px hierarchy label lane에서 긴 Group/Layer/Parent 이름, L/L*/S/Visibility/Primary 표시가 읽히며 tooltip으로 전체 이름을 확인할 수 있는지 확인한다.
- [ ] Resource Timeline의 Create/Edit, Hierarchy, State, Order 구분과 30 px L/S/앞/뒤 버튼의 hover, focus, click, accessible name/description을 확인한다.
- [ ] Resource Inspector의 metadata label 정렬, 동일 높이 2열 Transform 버튼, 구분된 보조 action, compact property card와 세로 스크롤을 한국어/English에서 확인한다.
- [ ] Effect Timeline의 220 px Layer name column과 증가한 높이에서 긴 Resource Layer 이름, Group child, Parent badge 및 frame cells가 겹치지 않는지 확인한다.
- [ ] Windows 100%/125%/150% DPI에서 위 항목을 반복하고 기존 Create/Delete/Group/Lock/Solo/Reorder/Transform/Keyframe 동작과 Undo/Redo 의미가 바뀌지 않았는지 확인한다.

## v0.0.11 Timeline Multi-Key Editing

- [ ] Resource의 여러 Property row에서 Click, Ctrl toggle, same-track Shift range와 cross-track additive Shift가 Primary Key를 명확히 표시하는지 확인한다.
- [ ] 빈 Property cell에서 marquee를 드래그해 보이는 Key만 선택하고 frame scrub, Layer selection 및 current playhead와 충돌하지 않는지 확인한다.
- [ ] 선택한 Key를 +3/-2 frame 수평 이동하고 상대 간격, 값, Easing과 0°/720°/1080° Rotation 값이 그대로인지 확인한다.
- [ ] 같은 Track의 unselected destination Key와 충돌할 때 전체 이동이 거부되고 부분 이동, Dirty 또는 Undo가 생기지 않는지 확인한다.
- [ ] Alt+Left/Right nudge의 boundary clamp, collision과 키 입력당 Undo 하나를 확인한다.
- [ ] 여러 Track의 Key를 Delete하고 Track별 마지막 Key 값이 static 값으로 보존되며 Undo/Redo 한 번으로 exact 복원되는지 확인한다.
- [ ] 서로 다른 Resource/Effect Transform/Motion Key에 Linear, Ease In, Ease Out, Ease In/Out을 batch 적용하고 no-op은 Undo를 만들지 않는지 확인한다.
- [ ] Resource Group collapse가 숨겨진 Key selection만 제거하며 Key 데이터와 Layer multi-selection은 유지하는지 확인한다.
- [ ] Effect Single/Particle/Orbit/Helix logical Layer의 System/Motion Key를 함께 편집하고 generated ID 또는 fake Group이 생기지 않는지 확인한다.
- [ ] Save/Reload 후 frame/value/easing이 exact하고 runtime Key selection은 저장되지 않으며 FORMAT_VERSION 12가 유지되는지 확인한다.

## v0.0.15 Undo Integrity

These are real Windows GUI checks and are not claimed by offscreen automation.

- [ ] Effect Start Point를 서로 다른 X/Y sentinel에서 드래그하고 Undo/Redo하여 Start만 exact 복원되며 End와 다른 Layer가 유지되는지 확인한다.
- [ ] Effect End Point에 같은 절차를 반복하여 End만 exact 복원되는지 확인한다.
- [ ] Layer A의 Start Point를 편집한 뒤 Layer B를 선택하고 Undo/Redo하여 Layer A만 바뀌는지 확인한다.
- [ ] 이름이 같은 두 Effect Layer를 만들고 한쪽만 편집한 뒤 선택을 바꿔 Undo하여 stable ID 대상만 복원되는지 확인한다.
- [ ] Resource Canvas의 Move/Rotate X/Y/Z/Scale/Pivot를 single/multi selection에서 드래그하고 gesture당 Undo 하나, no-op은 0개인지 확인한다.
- [ ] Resource/Effect Timeline에서 Move, multi-move, Delete, easing, nudge, Paste, Alt Duplicate와 snapped 변형을 실행해 action당 Undo 하나와 exact Redo를 확인한다.

## v0.0.15 Resource Layer Panel Clarity

These are real Windows GUI checks and are not claimed by offscreen automation.

- [ ] 한국어/English에서 상단 `＋ Layer/레이어`, `Duplicate/복제`, `Delete/삭제`와 하단 `Create Group/그룹 만들기`, `Ungroup/그룹 해제`, `Lock/잠금`, `Solo/솔로`, `Order/순서`가 축약 없이 보이는지 확인한다.
- [ ] Order 메뉴에 기존 Bring Forward/앞으로, Send Back/뒤로만 있고 방향 화살표 단독 버튼이나 새 Front/Back command가 생기지 않았는지 확인한다.
- [ ] 선택 없음, Leaf 하나, Leaf 2개, Group 하나, locked/inherited-locked 선택에서 toolbar와 context menu의 enable/disable 상태 및 이유 tooltip이 일치하는지 확인한다.
- [ ] Lock/Solo의 OFF/ON selected appearance, 키보드 focus outline, Tab 순서와 스크린리더 이름·설명이 상태를 명확히 전달하는지 확인한다.
- [ ] 5~8 Layer와 1~2 Group에서 목록이 주 공간을 유지하고 긴 Layer/Parent 이름의 elide, full tooltip, L/L*/S row marker 의미가 유지되는지 확인한다.
- [ ] 1280×720, 1600×900, 1920×1080 및 Windows 100%/125%/150% DPI에서 버튼 잘림·겹침이 없고 목록 높이가 충분한지 확인한다.
- [ ] Duplicate/Delete/Group/Ungroup/Lock/Solo/Order를 toolbar와 context menu 양쪽에서 실행하고 selection, Primary, collapse, parent, visibility, render order 및 Undo/Redo가 기존과 동일한지 확인한다.
