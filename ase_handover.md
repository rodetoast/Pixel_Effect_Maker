# Pixel Effect Maker Handover

Current checkpoint targets v0.0.08 / project format v12. Resource `CompositionLayer.parent_id` and logical `EffectResourceLayer.parent_id` are the stable-ID Parenting sources of truth; Generated Effect layers do not duplicate the relation. Format v11 loads with no parent and is only written as v12 on an explicit save. Missing/self/cyclic links are repaired deterministically in memory without automatic save.

Parent world resolution memoizes one 3×3 affine per leaf and frame pass. Inherited components are Position X/Y, Rotation Z and Scale X/Y. Rotation X/Y, Position Z and Perspective remain local visual deformation because the current decomposed 2.5D raster projection cannot exactly compose arbitrary parent 3D transforms. Opacity, visibility, Solo, lock, playback speed, Local Z, Surface Transform, particle spawn/motion and Group membership/order are not inherited.

Set, Clear and Reparent serialize a maintain-world `parent_offset = inverse(new_parent_world) × old_world × inverse(child_local)` at the current playhead, preserving all existing tracks. Cycle checks run both in candidate UI and mutation entry points. Duplicate remaps parent references only when both endpoints are duplicated; dependent parent deletion is rejected unless every dependent child is in the same delete batch. Groups remain organization-only and have no Parent or Transform fields.

Resource and Effect editors keep runtime-only `selected_ids`, `primary_id`, `anchor_id`, and collapse state; none are serialized. Resource selection uses `CompositionLayer.id`. Effect selection uses logical `EffectResourceLayer.id`, with Generated Timeline rows mapped through `generated_layer_id`. Group Visibility affects preview and final output, Group Solo is preview-only, and Group Lock is inherited edit protection without changing child flags.

Leaf Lock guards model mutation entry points and permits selection, visibility, Solo, unlock, inspection, and exact-state duplicate. Leaf Solo uses `visible AND (no solo active OR solo)` only in editor Canvas/playback paths; final render, PNG, sequence, and Bake retain Visibility-only semantics.

Click/Ctrl+Click/Shift+Click and focus-scoped Ctrl+A do not enter Undo history or touch composition revision. Batch Duplicate, reorder, Delete, Lock, Solo, Visibility, Front and Back each use one existing editor Undo command containing before/after selection snapshots. Any locked selected layer rejects structural reorder/delete atomically; duplicate, Solo, Visibility, Lock and Unlock remain allowed. Inspector, Canvas gizmo, property, Auto-Key and keyframe paths target only the Primary layer.

Layer Group Create/Ungroup/Move/Duplicate/Delete preserve flattened back-to-front order. Structural changes reject a locked group or locked descendant atomically. Collapse/expand is runtime-only. Empty groups remain valid save/reload and drop targets.
