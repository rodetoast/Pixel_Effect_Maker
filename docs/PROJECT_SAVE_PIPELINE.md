# Project Save Pipeline

## 흐름과 안전 경계

```text
Save/Save As → 정확 모델 확정 → Project.to_dict → compact JSON/UTF-8
→ 대상 폴더의 unique Temporary File → write → flush → fsync
→ close → os.replace → 조건부 Dirty 해제와 성공 Status
```

저장은 동기식이다. compact codec 적용 후 측정한 600×600 대표 프로젝트도 첫 Save 약 62ms, 변경 없는 Save 약 19ms여서 전체 Model Deep Copy나 복잡한 Background Snapshot을 추가하지 않았다. 실행 중 Save/Save As는 비활성화하고 중복 요청을 거부한다. 동기 호출 동안 Qt Event Loop가 편집 이벤트를 처리하지 않으므로 Snapshot과 Model이 경쟁하지 않는다.

Save As는 성공 후에만 `project_path`를 교체한다. Directory 생성, Model Encoding, Temporary Write/fsync 또는 Atomic Replace 실패 시 Temporary File을 정리하고 기존 대상, 기존 경로와 Dirty 상태를 보존한다. 자동 Backup은 없으며 정상 파일을 먼저 삭제하지 않는다.

## 계측

Windows offscreen 진단값이며 CI 시간 제한이 아니다.

| Fixture | 기존 Nested List + pretty JSON | v7 첫 Save | 변경 없는 Save | Metadata-only | 한 Frame 변경 | Load | v7 크기 | v7 Peak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Small 64² / 12 Project Frames | 895.19ms / 6.37MB | 4.46ms | 1.89ms | 1.58ms | 1.60ms | 8.42ms | 9.1KB | 0.34MB |
| Medium 256² / 24 Frames | 34,434.80ms / 208.71MB | 18.63ms | 5.67ms | 5.62ms | 6.39ms | 20.08ms | 73.6KB | 0.65MB |
| Large 600² / 12 Frames | 미실행(예상 메모리 과다) | 62.32ms | 19.42ms | 18.20ms | 20.72ms | 46.90ms | 214.8KB | 1.95MB |

Medium Legacy 측정의 Pixel List 생성은 1,817.86ms, pretty JSON은 32,616.94ms, Peak Memory는 약 1.16GB였다. v7 첫 Save에서 가장 큰 단계는 checksum+compression을 포함한 `Project.to_dict`이며, 두 번째와 Metadata-only Save의 실제 Frame Encode 호출은 0회다. 한 Frame 변경은 1회다.
