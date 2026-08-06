# Particle Orbit & Helix Motion

## Modes, coordinates, and spawn centers

Linear preserves `position = start + velocity * age`. Orbit/Helix replace Direction, Spread, and Speed for position only; timing, lifetime, resource playback, scale, Z rotation, and opacity still apply. X points right, Y points down, and positive Z points toward the user. Every Point/Line/Box/Circle spawn point is its particle's motion center plus the configured center offset.

## Orbit evaluation

For normalized life `t = age / lifetime`, radius, angle, and axis use independent Linear/Ease In/Ease Out/Ease In/Out curves. `radius = lerp(radius_start, radius_end, radius_t)`. Since screen Y grows down, clockwise has a positive sign and counter-clockwise a negative sign. `angle = start + sign * turns * 360 * angle_t + phase`. The ellipse is `(cos(angle)*radius*ellipse_x, sin(angle)*radius*ellipse_y)`, followed by plane rotation. Turns are never shortest-path interpolated.

Phase uses SHA-256 over seed, particle ID, and the `motion-phase` domain. It consumes no legacy RNG values, so Linear random ordering and pixel output remain unchanged and scrub order cannot affect results.

## Helix axes

Helix Z maps the ellipse to XY and travel to Z. Helix X maps the ellipse to YZ and travel to X. Helix Y maps the ellipse to XZ and travel to Y. At zero degrees the radial direction is +X for Z/Y axes and +Y for X. Rotation direction is viewed from the positive axis toward the origin.

## Projection, sorting, and output

Local Perspective reuses the Resource Layer focal mapping and near-plane ratio. One factor moves the billboard center and scales the sprite, with bounded near-plane behavior. Sprites remain billboards. Particles are stably sorted by local Z ascending; equal Z retains creation order. Linear skips sorting. Exact frames feed Preview, Playback, Bake, and export, then the Resource Layer 2.5D transform.

## Editing, caches, and limits

Reset Motion restores base values without deleting tracks. Canvas paths sample the production evaluator (32-256 points); Shift snaps Start Angle to 15 degrees; release makes one undo step and Escape cancels. Motion-only edits reuse resource clips and spawn state, render the latest current frame at about 30 FPS, and leave full sequence generation lazy.

This release does not add meshes, lighting, shadows, sprite X/Y rotation, tangent-facing sprites, GPU/OpenGL particles, a graph editor, or a motion preset library.

## Reference performance (non-CI)

On the development Windows environment with a 600×600 canvas, five visible layers, 100 Helix particles, and one current frame: spawn-cache lookup 0.022 ms, motion evaluation 0.472 ms, stable depth sort 0.007 ms, particle base composite 17.593 ms, common 2.5D transform 3.905 ms, five-layer Effect composite 94.329 ms, Canvas paint cycle 100.154 ms, guide sampling 0.493 ms, and Inspector update 0.175 ms. These wall-clock observations are diagnostic, not pass/fail thresholds.
