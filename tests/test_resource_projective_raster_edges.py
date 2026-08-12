from __future__ import annotations

import math

import numpy as np
import pytest

from app.models.effect_resource_layer import EffectLayerTransform3D
from app.services.layer_space_transform_service import projected_layer_quad, transform_layer_space_rgba_frame


def _directional_fixture(size: int = 28) -> np.ndarray:
    y, x = np.indices((size, size))
    pixels = np.empty((size, size, 4), dtype=np.uint8)
    pixels[..., 0] = (x * 7 + y * 3) % 251
    pixels[..., 1] = (x * 2 + y * 11) % 253
    pixels[..., 2] = (x * 13 + y * 5) % 249
    pixels[..., 3] = 255
    pixels[:, -1, :3] = [255, 0, 17]
    pixels[-1, :, :3] = [0, 255, 31]
    return pixels


def _orthographic_reference(source: np.ndarray, axis: str, angle: float) -> np.ndarray:
    height, width = source.shape[:2]
    center_x, center_y = width / 2.0, height / 2.0
    cosine = math.cos(math.radians(angle))
    output = np.zeros_like(source)
    alpha_y, alpha_x = np.nonzero(source[..., 3])
    if not len(alpha_x):
        return output
    left, right = int(alpha_x.min()), int(alpha_x.max()) + 1
    top, bottom = int(alpha_y.min()), int(alpha_y.max()) + 1
    for y in range(height):
        for x in range(width):
            sx = center_x + (x + .5 - center_x) / cosine if axis == "y" else x + .5
            sy = center_y + (y + .5 - center_y) / cosine if axis == "x" else y + .5
            # Keep analytically integral coordinates on the half-open cell to
            # their right/bottom despite cosine floating-point roundoff.
            ix, iy = math.floor(sx + 1e-10), math.floor(sy + 1e-10)
            if left <= sx < right and top <= sy < bottom and 0 <= ix < width and 0 <= iy < height:
                output[y, x] = source[iy, ix]
    return output


@pytest.mark.parametrize("axis", ["x", "y"])
@pytest.mark.parametrize("angle", [-89, -60, -30, -15, -5, -.001, .001, 5, 15, 30, 60, 89])
def test_orthographic_rotation_matches_half_open_pixel_center_reference(axis, angle):
    source = _directional_fixture()
    transform = EffectLayerTransform3D(**{f"rotation_{axis}": angle})
    actual = transform_layer_space_rgba_frame(source, transform)
    expected = _orthographic_reference(source, axis, angle)
    assert np.array_equal(actual, expected)


def _inside_convex_quad(point: np.ndarray, quad: np.ndarray) -> bool:
    edges = np.roll(quad, -1, axis=0) - quad
    relative = point - quad
    crosses = edges[:, 0] * relative[:, 1] - edges[:, 1] * relative[:, 0]
    return bool(np.all(crosses >= -1e-8) or np.all(crosses <= 1e-8))


def _assert_inside_alpha_quad(actual: np.ndarray, source: np.ndarray, transform: EffectLayerTransform3D) -> None:
    alpha_y, alpha_x = np.nonzero(source[..., 3])
    bounds = (int(alpha_x.min()), int(alpha_y.min()), int(alpha_x.max()) + 1, int(alpha_y.max()) + 1)
    quad, valid = projected_layer_quad(bounds, transform, source.shape[1], source.shape[0])
    assert valid.all()
    for y, x in np.argwhere(actual[..., 3] > 0):
        assert _inside_convex_quad(np.array((x + .5, y + .5)), quad)


@pytest.mark.parametrize("axis,angle", [("x", 15), ("x", -60), ("y", 30), ("y", -89)])
@pytest.mark.parametrize("perspective", [.2, .6, 1.0])
def test_perspective_raster_never_writes_outside_projected_source_footprint(axis, angle, perspective):
    source = _directional_fixture()
    transform = EffectLayerTransform3D(**{f"rotation_{axis}": angle}, perspective_strength=perspective)
    actual = transform_layer_space_rgba_frame(source, transform)
    quad, valid = projected_layer_quad((0, 0, source.shape[1], source.shape[0]), transform,
                                       source.shape[1], source.shape[0])
    assert valid.all()
    for y, x in np.argwhere(actual[..., 3] > 0):
        assert _inside_convex_quad(np.array((x + .5, y + .5)), quad)


@pytest.mark.parametrize("axis", ["x", "y"])
def test_near_identity_rotation_does_not_duplicate_right_or_bottom_border(axis):
    source = _directional_fixture()
    angle = .001
    actual = transform_layer_space_rgba_frame(source, EffectLayerTransform3D(**{f"rotation_{axis}": angle}))
    expected = _orthographic_reference(source, axis, angle)
    assert np.array_equal(actual, expected)


@pytest.mark.parametrize("axis", ["x", "y"])
@pytest.mark.parametrize("edge", ["right", "bottom", "bottom_right"])
def test_rotated_boundary_pixels_do_not_streak_from_outside_clamping(axis, edge):
    source = np.zeros((28, 28, 4), dtype=np.uint8)
    if edge == "right": source[:, -1] = [255, 0, 17, 255]
    elif edge == "bottom": source[-1, :] = [0, 255, 31, 255]
    else: source[-1, -1] = [19, 37, 255, 255]
    for angle in (5, 15, 30, 60, 89):
        transform = EffectLayerTransform3D(**{f"rotation_{axis}": angle})
        actual = transform_layer_space_rgba_frame(source, transform)
        _assert_inside_alpha_quad(actual, source, transform)
        if angle != 60:
            assert np.array_equal(actual, _orthographic_reference(source, axis, angle))


@pytest.mark.parametrize("axis", ["x", "y"])
def test_transparent_margin_directional_fixture_has_no_edge_extension(axis):
    source = _directional_fixture()
    source[:2] = 0; source[-1:] = 0; source[:, :2] = 0; source[:, -1:] = 0
    for angle in (5, 15, 30, 60, 89):
        transform = EffectLayerTransform3D(**{f"rotation_{axis}": angle})
        actual = transform_layer_space_rgba_frame(source, transform)
        _assert_inside_alpha_quad(actual, source, transform)
        if angle != 60:
            assert np.array_equal(actual, _orthographic_reference(source, axis, angle))


@pytest.mark.parametrize("axis", ["x", "y"])
def test_small_rotation_transition_is_half_open_and_symmetric(axis):
    source = _directional_fixture()
    assert np.array_equal(transform_layer_space_rgba_frame(source, EffectLayerTransform3D()), source)
    for angle in (.001, .1, 1):
        positive = transform_layer_space_rgba_frame(source, EffectLayerTransform3D(**{f"rotation_{axis}": angle}))
        negative = transform_layer_space_rgba_frame(source, EffectLayerTransform3D(**{f"rotation_{axis}": -angle}))
        assert np.array_equal(positive, _orthographic_reference(source, axis, angle))
        assert np.array_equal(negative, _orthographic_reference(source, axis, -angle))
        assert np.array_equal(positive[..., 3], negative[..., 3])


@pytest.mark.parametrize("size", [1, 2, 3, 27, 28, 29])
def test_identity_pixel_exact_still_passes(size):
    source = _directional_fixture(size)
    assert np.array_equal(transform_layer_space_rgba_frame(source, EffectLayerTransform3D()), source)
