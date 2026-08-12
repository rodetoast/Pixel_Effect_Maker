# Resource Pixel Coordinate Convention

This note prevents half-pixel and inclusive/exclusive regressions in Resource Editor rendering and overlays.

## Coordinates

- Array pixel indexes are integers: a 28×28 image has indexes 0..27.
- Each indexed pixel is a cell in source-local outer-edge coordinates: pixel `(x, y)` occupies `[x, x+1) × [y, y+1)`.
- The full `W × H` source rectangle has outer edges `(0,0)`, `(W,0)`, `(W,H)`, `(0,H)`.
- The geometric center and default pivot are `(W/2, H/2)`. Thus 28×28 uses `(14,14)` and 29×29 uses `(14.5,14.5)`.

## Alpha and selection bounds

Alpha scans return half-open bounds `(min_x, min_y, max_x+1, max_y+1)`. Opaque indexes 2..26 therefore yield `[2,27) × [2,27)`. Resource selection/projected quads use these outer edges, not inclusive maximum pixel indexes.

## Raster sampling

Integer-aligned identity orientation uses direct clipped array blitting. This preserves exact RGBA bytes and skips homography. If the destination region has no visible content, transparent RGB bytes are preserved as well.

Rotation, scale, tilt, perspective, or non-integer placement uses an inverse-homography nearest-neighbor sampler. The projected alpha quad is built from half-open source outer edges `(left, top, right, bottom)`, and its destination bounding box is `[floor(min), ceil(max))` on each axis. Every destination pixel is sampled at its geometric center `(x+0.5, y+0.5)`.

The inverse homography produces normalized `u/v` values over the cropped source rectangle. Only `0 <= u < 1` and `0 <= v < 1` are valid; source indexes are `floor(u * crop_width)` and `floor(v * crop_height)`. Exactly `u == 1` or `v == 1`, a zero denominator, and any out-of-range index are transparent. They must never be clipped to the last source row or column. Resource Local Z continues to use the `Ry @ Rx @ Rz` column-vector convention.

## Pivot overlay

`CompositionLayer.pivot_x/y` are source-local outer-edge coordinates. The renderer places that local point at the layer's established composition position. The Canvas marker displays this projected world pivot; it is not part of RGBA output. Changing the local pivot moves the sprite footprint relative to the marker without redefining Position.

The pre-Resource Asset Preview uses the same source-local pivot convention. Its marker is a viewer overlay transformed by Preview zoom and pan; it does not alter source RGBA or become project render content.
