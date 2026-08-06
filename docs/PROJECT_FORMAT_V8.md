# Project Format v8

Format v8 adds explicit Particle Motion metadata beneath each `particle_settings` object. It retains the v7 compact frame payload and introduces no new pixel encoding.

```json
{"motion":{"mode":"orbit","center":[0,0,0],"radius_start":64,"radius_end":16,"ellipse_scale":[1,0.6],"start_angle_degrees":0,"turns":2,"direction":"clockwise","phase_spread_degrees":360,"orbit_plane_rotation_degrees":0,"helix_axis":"z","axis_start":-40,"axis_end":80,"perspective_strength":0.25,"easing":{"radius":"Linear","angle":"Linear","axis":"Linear"},"tracks":{},"revision":0}}
```

All numbers must be finite. Radius and ellipse scales are non-negative; local perspective is 0..1. Serialization validates and normalizes Motion before JSON encoding, so NaN/Infinity, invalid enum values, and out-of-range persisted values cannot enter a v8 file. v1-v7 files lack Motion metadata and migrate to identity Linear defaults. The version bump is required because older v7 writers do not preserve unknown nested Particle settings when resaving.

Save/Save As is a metadata boundary: it writes the Motion object and already-existing compact Pixel Payload through the atomic temporary-file/replace path, but does not render a current particle frame, materialize a full sequence, Bake, or Export. Dirty/pending sequence state remains available after serialization. Exact pixel generation occurs only at explicit playback, Bake, and output boundaries.
