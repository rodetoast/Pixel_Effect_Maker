# Resource Composition Clip & Overscan Audit

Date: 2026-09-08. Actual Windows GUI manual QA: **수행하지 않음**.

1. 프로젝트: `C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker`.
2. 작업 전 HEAD: `e6f0dc4d4afd28ae5b1a775baa9bd27378b00306`.
3. Version: Pixel Effect Maker v0.0.15.
4. FORMAT_VERSION: 12.
5. 작업 전 pytest: 1030 passed, 80.17s.

## UI Polish Checkpoint

6. 명시적으로 Stage한 15개 파일: CHANGELOG.md; app/services/localization_service.py; app/ui/composition_layer_properties_panel.py; app/ui/effect_library_panel.py; app/ui/layout_metrics.py; app/ui/particle_properties_panel.py; app/ui/resource_editor_v2/composition_inspector.py; app/ui/resource_editor_v2/composition_timeline.py; app/ui/resource_layer_transform_panel.py; app/ui/timeline_widget.py; app/ui/timeline_command_bar.py; docs/MANUAL_TEST_CHECKLIST.md; tests/test_editor_layout_polish.py; tests/test_resource_layer_panel_clarity.py; tests/test_timeline_command_bar_layout.py.
7. 제외: 테스트소스.png 및 project/log/cache/build/dist/exe/zip/backup/temp. `git add -A` 사용하지 않음.
8. Commit: `Polish editor command bars and resource layer panel`.
9. Hash: `1bfd865c6396565b9c43d541613b5a58ef590cd9`.
10. 직후 Git: staged 0, 테스트소스.png만 untracked.

## Clip Audit

11. 실제 일반 이동 clip source: Composition Output Bounds. 별도로 2.5D/Parenting의 중간 Composition render target에서도 변형 전 clip 발견.
12. 좌표 공간: Composition Space. source pixel space에서 잘라내는 고정 source clip이나 Widget-space 내부 clip이 아님.
13. 일반 2D: 변형된 destination와 output 교집합을 구한 뒤 composite. 기존 2.5D/Parenting: Composition 크기 local image로 변형 전 clip → world transform → destination clip/composite.
14. Current Composition width/height가 final target의 정확한 범위.
15. Source bounds는 샘플링할 텍스처 영역이며 destination clip이 아님.
16. Layer initial/selection bounds는 final clip으로 사용되지 않음. 다만 기존 중간 local image가 너무 작아 픽셀 손실 가능.
17. QWidget viewport clip은 실제 화면 밖만 제한. 사용자가 본 내부 경계는 QWidget clip이 아님.
18. 이전 Canvas는 paint마다 render_composition_frame(preview=True)을 직접 호출하므로 frame-cache stale clip이 아님. alpha bounds cache는 선택 표시용이며 raster clip과 독립.
19. Root cause: strict final renderer의 Composition-sized RGBA를 편집 Canvas에서도 사용하여 바깥 픽셀을 먼저 소실. 선택 polygon/gizmo는 독립 좌표로 그려져 남음. Checkerboard tile은 이전에 output rect로 clipping되지 않아 끝의 일부 타일이 출력 밖으로 넘칠 수 있었음.
20. 일반 이동은 intended final output clipping + 편집 UX 문제. 2.5D/Parenting 중간 target의 변형 전 clip은 별도 버그로 수정.

## Final Render

21. `render_composition_frame`은 항상 (0,0,width,height) target. source를 변형한 다음 destination를 clip.
22. Export dimensions: Composition width/height 유지, 대표 28×28 검사.
23. Single Effect는 render_composition_frames/current_frame, Particle은 composition_as_clip을 사용. 모두 strict path이며 editor region cache를 참조하지 않음.
24. 기존 2D final sampling 유지. 2.5D/Parenting은 잘못 손실됐던 source pixel이 되살아나는 경우만 의도적 출력 수정. 잘못된 이전 결과까지 동일하다고 주장하지 않음.

## Editor Overscan

25. `render_editor_region`은 UI 전용 helper. model flag/serialization field 없음.
26. `output_frame_rect()` = origin + Composition width/height × zoom.
27. Outside는 palette Shadow alpha 75/255 overlay로 약하게 dim. 픽셀은 계속 보임.
28. Checkerboard는 Composition transparency만 표시하며 output rect에 정확히 clip. 바깥은 어두운 작업 배경.
29. Border는 palette Text 색 2px neutral outline. 기존 녹색/파란색 선택 outline과 구분.
30. Legacy 2D affine 및 공유 2.5D/world projection 후 viewport region에 draw. Parent transform과 소스 피벗 적용.
31. Target 크기는 viewport/zoom. Destination 교집합이 비면 sampling grid 없이 반환. editor region은 16,777,216 pixel 예산 제한.

## Transform

32. Left: 음수 region에서 출력 밖 픽셀 확인.
33. Right: 28px frame 오른쪽 overscan 확인.
34. Top: 음수 Y 확인.
35. Bottom: 출력 아래 픽셀 확인.
36. Rotation: 45/90/-45/720/1080°와 사방 이동 교차 검사.
37. Scale: 2×/0.5×/비균일 × Rotation/Position 검사.
38. Pivot: 옮긴 피벗과 source보다 작은 Composition 및 기존 pivot 회귀 검사.
39. 2.5D: Z, X/Y rotation, perspective 및 기존 Resource/Particle 의미 테스트.

## Parenting / Multi-Transform

40. Parent position: world affine 사용, output 밖 표시.
41. Parent rotation: world affine 사용, 회전된 child 표시.
42. Parent scale: 큰 source를 줄여 출력 안으로 들여올 때 preclip 손실 제거.
43. parent_offset: 변경 없음; 회귀에서 보존 확인.
44. Keep World: 기존 서비스 변경 없음; 전체 parenting 회귀 대상.
45. Multiple layers: 기존 world-space multi edit 이후 Overscan image 갱신.
46. Parent+Child: root만 수정되고 child track은 unchanged.
47. Transform roots: 기존 multi_transform_service 사용, 수학 변경 없음.

## Interaction / Visibility

48. Overscan hit-test: output rect 제한 없음. 모든 layer의 parent prefix 평가 및 effective Group visibility/Solo 일치하도록 수정.
49. Move gizmo: 기존 widget-space handles, output clip 없음.
50. Rotate gizmo: 기존 handles/rings, output clip 없음.
51. Scale gizmo: 기존 projected polygon handles, output clip 없음.
52. Pivot gizmo: 기존 layer pivot marker, output pivot과 독립.
53. start/end: frame 범위 밖 layer는 draw 안 함.
54. visibility: effective_visible 사용.
55. solo: preview_solo_active/preview_soloed 사용; final에는 preview Solo 적용 안 함.
56. lock: editing restriction 유지; renderer는 숨기지 않음.
57. Group: visibility/Solo/lock 기존 의미, 새 transform 없음.

## Undo / Cache

58. Move Undo: output 밖 이동 후 원래 track/value exact 복원.
59. Redo: 이동 위치 및 미리보기 image exact 재현.
60. Selection change: A 이동 중 B 선택 후 final/Undo/Redo에도 A만 수정.
61. Stable ID: 기존 press-time target capture 콜백 변경 없음.
62. Canvas cache: set_context마다 무효화하고 region/frame/revision key 사용. Undo/Redo 및 UI transform refresh가 이 경로를 호출. Hover/반복 paint는 cache 재사용. 최종 resource sequence cache와 완전히 분리.

## Performance

대표 fixture: 640×480 widget, zoom 8, render region 80×60, 8×8 source, inside/partial outside/x=100000 혼합. 수치는 단일 환경 측정이며 성능 보증치 아님.

63. 10 layers: rebuild 1.03ms, warm paint 0.87ms, transform/context update 1.45ms.
64. 50 layers: rebuild 5.37ms, warm paint 0.95ms, update 5.92ms.
65. 100 layers: rebuild 10.45ms, warm paint 0.95ms, update 10.30ms.
66. Fully offscreen: sampling destination를 target와 먼저 교차. 좌표 크기에 비례하는 bitmap 없음. Fractional pivot 중간 이미지는 source 크기+2로 제한.
67. Paint deepcopy: 0. Project clone/reload 없음.
68. Paint serialization/filesystem: 0. Hover paint에서 renderer를 호출하면 실패하도록 테스트.

## Tests / Isolation

69. 수정: app/services/resource_composition_render_service.py, app/services/effect_render_service.py, app/ui/resource_editor_v2/composition_canvas.py, CHANGELOG.md, docs/MANUAL_TEST_CHECKLIST.md.
70. 생성: tests/test_resource_composition_clip.py, tests/test_resource_editor_overscan.py, 이 감사 보고서.
71. 신규 tests: 108 parameterized cases.
72. Clip: strict Composition target와 transformed destination 확인.
73. Overscan: 사방/negative coordinates 및 cached viewport image 확인.
74. Transform: 96개 Position×Rotation×Scale 조합, 2.5D 큰 source 4개 등.
75. Parenting: 큰 source, 이동/회전/축소 parent, 기존 parenting 전체 회귀.
76. Undo: 새 overscan selection-change/Redo image 비교 및 기존 stable-ID 회귀.
77. Export: strict region pixel equality와 composition_as_clip 크기/내용, 기존 export/Effect integration 회귀.
78. Focused regression: 116 passed (추가 overscan + Resource 2.5D Particle 테스트).
79. Full pytest: 1138 passed, 0 failed, 77.80s. 기존 1030개 + 신규 108개.
80. compileall: 성공.
81. --version: v0.0.15 유지.
82. FORMAT_VERSION: 12 유지.
83. --check: 성공. AppData log write sandbox 권한 경고 발생, check 종료 코드 0.
84. run_app.bat: 기본 interpreter 검색은 이 세션에서 실패. 제공된 PIXEL_EFFECT_PYTHON override에 C:\Dev\pixel_effect_test_venv\Scripts\python.exe를 지정해 check 성공. 시스템/launcher 파일 수정 없음.
85. git diff --check: 성공. LF→CRLF 안내만 발생.
86. Serialization: 변경 없음.
87. Group semantics: 변경 없음.
88. Parenting math: 변경 없음.
89. Multi-Transform math: 변경 없음.
90. Rotation Revolution: track 값 변경 없음.
91. Timeline: 변경 없음.
92. Snapping: 변경 없음.
93. Auto-Key: 변경 없음.

## Git / Manual QA / Final

94. 최종 HEAD: 1bfd865c6396565b9c43d541613b5a58ef590cd9.
95. Staged: 0으로 종료.
96. Clip/Overscan commit: 0.
97. Push/Tag/Build/PyInstaller/ZIP/Release: 0.
98. Codex 실제 Windows GUI manual 수행 여부: **수행하지 않음**.
99. Right edge: manual checklist 작성, 사용자 확인 대기.
100. Left edge: manual checklist 작성, 사용자 확인 대기.
101. Top/Bottom: manual checklist 작성, 사용자 확인 대기.
102. Rotation: manual checklist 작성, 사용자 확인 대기.
103. Scale: manual checklist 작성, 사용자 확인 대기.
104. Pivot: manual checklist 작성, 사용자 확인 대기.
105. Parenting: manual checklist 작성, 사용자 확인 대기.
106. Undo/Redo: manual checklist 작성, 사용자 확인 대기.
107. Export: manual checklist 작성, 사용자 확인 대기.
108. 사용자가 본 원인: Composition-sized final image를 editor 작업 Canvas에서도 사용. 선택/gizmo는 독립 draw. 정확한 두 screenshot 원본은 첨부되지 않아 코드 및 재현 fixture로 판정.
109. Clipping bug: 2.5D/Parenting pre-transform intermediate crop 제거. 정상 destination clip 유지.
110. Editor overscan: 적용.
111. Export strict clipping: 유지.
112. Output-frame 시인성: neutral border, inside checkerboard, outside dimming 적용.
113. 남은 위험: Windows DPI/실제 GUI의 색조·선택·gizmo 체감은 사용자 검증 필요. near-plane 밖 invalid quad는 기존 정책대로 표시되지 않음. 성능 fixture보다 큰 source/viewport 및 복잡한 perspective는 추가 실사용 검증 후보.
114. 다음 후보: v0.0.16 Work Area / Loop Preview.
