# Resource Compositions

Resource Composition은 Imported Asset과 Effect 사이의 재사용 가능한 애니메이션 단위입니다.

```text
Imported Asset → Resource Composition → Particle / Effect → Preview → Bake / Export
```

Composition은 독립적인 이름, 캔버스 크기, FPS, 프레임 수, Loop, 출력 Pivot과 정렬된 Layer 목록을 가집니다. Layer는 SourceAsset 또는 AnimationClipAsset ID를 참조하고 표시 상태, 시작·종료 프레임, 원본 시작 프레임과 Composition 전용 Pivot을 가집니다. Composition 중첩은 허용하지 않아 순환 참조가 생기지 않습니다.

모델 목록은 뒤 항목일수록 앞에 source-over 합성합니다. UI는 이를 뒤집어 목록 위가 Canvas Front가 되도록 표시합니다. Start와 End는 양쪽 끝을 모두 포함하므로 `3..8`은 프레임 인덱스 3, 4, 5, 6, 7, 8에서 보입니다.

CompositionLayer Duplicate는 새 Layer ID를 한 번 생성해 Undo/Redo에서도 그대로 재사용하고 SourceAsset/AnimationClipAsset ID는 공유합니다. 나머지 범위, Visibility, Pivot, Track, Keyframe과 Easing은 값으로 깊은 복사되므로 복제 후 편집은 원본에 영향을 주지 않습니다. 복제본은 원본 바로 앞(model index+1)에 삽입됩니다. Timeline Drag는 UI index를 역순 model index로 변환해 Drop 한 번에 전체 순서 스냅샷을 기록합니다.

주요 Sprite Track은 `position`, 로컬 Z인 `rotation`, `rotation_x`, `rotation_y`, `position_z`, `scale`, `opacity`, `perspective_strength`입니다. 등록하지 않은 Track은 Identity 기본값을 사용합니다. Keyframe은 프레임, 값과 Linear/Ease In/Ease Out/Ease In/Out easing을 저장합니다. 같은 프레임에 다시 기록하면 교체되며 평가 시 항상 프레임 순서로 정렬됩니다.

Renderer는 매 프레임을 투명 `uint8 RGBA` 버퍼에서 새로 시작합니다. Layer 표시·범위를 확인하고, Animated Asset duration을 Composition 시간에 매핑한 다음 Pivot 기준 Position/Rotation/Scale, Opacity와 source-over 합성을 수행합니다. 좌표 샘플링은 최근접 이웃만 사용하고 캔버스 밖은 자릅니다. 원본 Asset과 이전 렌더 결과는 수정하지 않습니다.

Particle 연결에서는 Composition 전체 프레임을 결정적으로 렌더한 AnimationClip-compatible frame source를 사용합니다. Particle age는 먼저 `age / effect_project_fps`로 초 단위가 되고, 여기에 Composition FPS와 Particle Playback Speed를 곱해 `floor`한 프레임을 선택합니다. 따라서 Effect와 Composition FPS가 달라도 실제 재생 시간이 유지됩니다. Random Start를 더한 뒤 Loop/Once/Hold를 적용합니다.

캐시 키는 Composition ID, revision, 크기, FPS와 프레임 수이며 Composition 또는 참조 원본이 바뀌면 무효화합니다. 캐시는 저장 데이터가 아니므로 프로젝트를 다시 열면 재생성됩니다.

현재 형식 9는 Composition의 Layer 순서, Source 참조, 범위, Visibility, Pivot과 모든 Track/Keyframe을 저장합니다. 이번 Multi-Image 흐름은 기존 필드만 사용하므로 형식 변경이 없습니다. 파일을 여는 것만으로 디스크의 원본 프로젝트를 다시 쓰지 않습니다.
