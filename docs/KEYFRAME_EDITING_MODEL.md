# Keyframe Editing Model

This document defines the v0.0.04 / format v9 keyframe contract shared by the Resource and Effect editors.

## Track identity and supported properties

`AnimationTrack.property_id` is the serialized identity. Keys are unique by zero-based frame and are always sorted before serialization.

| Editor | Model | Keyframe-capable properties |
| --- | --- | --- |
| Resource composition layer | `CompositionLayer.tracks` | Position, canonical Local Z `rotation`, Rotation X/Y, Scale, Opacity, Perspective |
| Effect Resource Layer system space | `EffectLayerTransform3D.tracks` | Position X/Y/Z, Rotation X/Y/Z, Scale X/Y, Opacity, Perspective |
| Particle motion | `ParticleMotionSettings.tracks` | Center X/Y/Z, radius start/end, ellipse X/Y, start angle, turns, phase spread, orbit-plane rotation, axis start/end, local perspective |

Resource and Effect pivots are static properties in v9. The UI therefore does not present a false keyframe control for them. Surface Transform tracks can be loaded for compatibility, but the compatibility section does not advertise new key creation.

Particle motion track dictionary keys use the public motion name (`radius_end`), while the contained shared track uses its registered identity (`motion_radius_end`). Resource Local Z remains the canonical `rotation` track and Effect system Local Z is `rotation_z`; aliases are not created.

## Current-frame editing states

Every exposed key button has three states:

- `◇` static: no keys exist. Inspector and gizmo edits change the static/base value.
- `◇` animated, no current key: the evaluated value is displayed and remains editable. The first actual Inspector or Gizmo value delta creates a key at the current frame and writes the edited value.
- `◆` current key: Inspector and gizmo edits update that exact key. Clicking the filled diamond deletes it.

The first key is always explicit. Conditional Auto-Key begins only after that property has at least one key; static properties continue to edit their base value without creating keys. There is no global Auto-Key toggle or recording mode.

Programmatic Inspector refresh, frame scrub, playback, project load, selection, localization, Undo/Redo, painting and worker-result installation never create keys. Loading guards suppress control synchronization signals, and model entry points also ignore unchanged evaluated values.

Explicit Add captures the current evaluated Inspector value and selected easing. Conditional Auto-Key writes the user's edited value directly with the existing default Linear easing, without recording an intermediate evaluated-value key. Repeating `set_keyframe` at the same frame updates the existing key. No duplicate frame can survive normalization or deserialization.

## Delete and move

Deleting the final key preserves that key value as the static value. Resource tracks may remain empty with that default; Effect Transform and Particle Motion remove the empty track and copy the preserved value into the canonical base field.

The Resource timeline supports a small, track-row key drag. The key value and easing are retained, the destination is clamped to `0 .. frame_count - 1`, and a destination already occupied by the same track rejects the move. One completed drag creates one Undo command. This is intentionally not a dope-sheet or curve editor.

The Resource timeline shows every layer track as a child row. Frame 0 maps to the first visible frame column and the last key maps to `frame_count - 1`. Clicking a diamond selects its frame and track row; the normal table selection is the selected-key highlight. The Effect timeline aggregates system and particle-motion keys as diamonds on the owning layer frame cell and lists property identities in its tooltip.

## Evaluation and interpolation

The supported interpolation modes remain Linear, Ease In, Ease Out, and Ease In/Out. Easing belongs to the left key of a segment. Scalar and vector values use the same normalized amount. Angles are ordinary numeric values rather than shortest-path angles, so `0 → 360` performs a full turn.

Before the first key, evaluation holds the first value. After the last key, it holds the last value. At endpoints it returns the exact endpoint value. Renderers, Inspector display, Resource-as-clip evaluation, playback, Bake, and export all consume these model evaluations.

## Undo, cancellation, and synchronization

Add, edit, delete, and move store before/after track or transform values in `EditorValueCommand`. SpinBox edits retain the existing merge IDs; the first conditional Auto-Key and following values therefore form one edit whose Undo removes the new key. A timeline move is a single command.

Gizmo Press captures state but creates no key. The first real delta conditionally creates keys per property track. Release commits one Undo command. Escape restores the captured transform or motion settings, removes every transient key created by the gesture, restores the Timeline marker and adds no Undo command. A combined X/Y gesture may Auto-Key an animated X track while editing a static Y base value because v9 stores these as independent tracks.

Programmatic frame refresh sets controls while their loading guard is active. It must not create keys or Undo entries. Effect renderer work remains revision/frame guarded by the existing preview pipeline; key edits travel through the same cache invalidation and refresh paths as other model edits.

## Save and reload

Format v9 serializes each non-empty track as `property_id`, `default_value`, and ordered `keyframes` containing `frame`, `value`, and `easing`. Resource composition tracks retain empty static tracks where the property card itself is part of the composition model. Effect system and Particle Motion serializers omit empty tracks.

`Project.to_dict()` and `Project.from_dict()` preserve track identities, key order, values, and easing. Deserialization rejects duplicate key frames. No v10 migration is introduced by this pass.

## Audit findings fixed in this pass

- Resource unkeyed animated Inspector edits changed `default_value`, even though keyed evaluation ignored it.
- Resource composition gizmos created keys on static properties and did not distinguish an actual drag delta.
- Effect system gizmos changed base Position/Scale values instead of the current key.
- Effect and Particle Inspectors displayed base motion/transform values rather than current evaluated values on some frame changes.
- Deleting the final key could expose the original default (often zero) instead of preserving the authored value.
- Effect timeline cells did not reveal system or motion keys.

The pass does not add a global Auto-Key toggle/record mode, graph/curve editor, broad dope sheet, or new keyframe-capable properties.
## Continuous rotation revolutions

Rotation values are stored as continuous total degrees; they are never reduced modulo 360. The UI displays complete revolutions plus the residual angle, for example `720° = 2x + 0°` and `-450° = -1x - 90°`. Consequently, linear interpolation from 0° to 720° produces two real revolutions even though both endpoints have the same visual orientation.
