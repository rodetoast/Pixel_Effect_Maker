# Pixel Effect Maker Handover

Current checkpoint work targets v0.0.06 / project format v10. Resource and Effect editors keep runtime-only `selected_ids`, `primary_id`, and `anchor_id` in `LayerSelectionState`; none are serialized. Resource selection uses `CompositionLayer.id`. Effect selection uses logical `EffectResourceLayer.id`, with Generated Timeline rows mapped through `generated_layer_id`.

Lock guards model mutation entry points and permits selection, visibility, Solo, unlock, inspection, and exact-state duplicate. Solo uses `visible AND (no solo active OR solo)` only in editor Canvas/playback paths; final render, PNG, sequence, and Bake retain Visibility-only semantics.

Click/Ctrl+Click/Shift+Click and focus-scoped Ctrl+A do not enter Undo history or touch composition revision. Batch Duplicate, reorder, Delete, Lock, Solo, Visibility, Front and Back each use one existing editor Undo command containing before/after selection snapshots. Any locked selected layer rejects structural reorder/delete atomically; duplicate, Solo, Visibility, Lock and Unlock remain allowed. Inspector, Canvas gizmo, property, Auto-Key and keyframe paths target only the Primary layer.
