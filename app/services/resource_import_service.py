"""Bounded PNG/GIF embedded resource import with per-frame timing."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence, UnidentifiedImageError

from app.models.animation_clip import AnimationClipAsset
from app.models.source_asset import SourceAsset


MAX_RESOURCE_DIMENSION = 4096
MAX_RESOURCE_PIXELS = 16_777_216
MAX_GIF_FRAMES = 512
MAX_GIF_DECODED_BYTES = 256 * 1024 * 1024


class ResourceImportError(ValueError):
    pass


def _validate_size(width: int, height: int) -> None:
    if width < 1 or height < 1:
        raise ResourceImportError("resource dimensions must be positive")
    if width > MAX_RESOURCE_DIMENSION or height > MAX_RESOURCE_DIMENSION:
        raise ResourceImportError(
            f"resource dimensions exceed {MAX_RESOURCE_DIMENSION} pixels"
        )
    if width * height > MAX_RESOURCE_PIXELS:
        raise ResourceImportError("resource pixel count exceeds the safe import limit")


def import_resource(path: str | Path) -> SourceAsset | AnimationClipAsset:
    source = Path(path)
    extension = source.suffix.lower()
    if extension == ".png":
        try:
            with Image.open(source) as image:
                _validate_size(*image.size)
                pixels = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
        except ResourceImportError:
            raise
        except (OSError, ValueError, UnidentifiedImageError) as exc:
            raise ResourceImportError(f"invalid PNG: {exc}") from exc
        return SourceAsset(
            source.name,
            pixels,
            source_path=str(source),
            source_format="png",
        )

    if extension == ".gif":
        try:
            with Image.open(source) as image:
                _validate_size(*image.size)
                declared_frames = int(getattr(image, "n_frames", 1))
                if declared_frames > MAX_GIF_FRAMES:
                    raise ResourceImportError(
                        f"GIF frame count exceeds the safe limit of {MAX_GIF_FRAMES}"
                    )
                decoded_bytes = image.width * image.height * 4 * declared_frames
                if decoded_bytes > MAX_GIF_DECODED_BYTES:
                    raise ResourceImportError("GIF decoded size exceeds the safe import limit")
                frames: list[np.ndarray] = []
                durations: list[int] = []
                default_duration = image.info.get("duration", 100)
                loop = image.info.get("loop", 0) == 0
                for index, frame in enumerate(ImageSequence.Iterator(image)):
                    if index >= MAX_GIF_FRAMES:
                        raise ResourceImportError(
                            f"GIF frame count exceeds the safe limit of {MAX_GIF_FRAMES}"
                        )
                    _validate_size(*frame.size)
                    frames.append(
                        np.asarray(frame.convert("RGBA"), dtype=np.uint8).copy()
                    )
                    durations.append(
                        max(1, int(frame.info.get("duration", default_duration) or 100))
                    )
                if not frames:
                    raise ResourceImportError("GIF contains no frames")
        except ResourceImportError:
            raise
        except (OSError, ValueError, UnidentifiedImageError) as exc:
            raise ResourceImportError(f"invalid GIF: {exc}") from exc
        return AnimationClipAsset(
            source.name,
            frames,
            fps=max(1, round(1000 / (sum(durations) / len(durations)))),
            frame_durations_ms=durations,
            playback_mode="loop" if loop else "hold",
            loop=loop,
            source_format="gif",
            source_path=str(source),
        )

    raise ResourceImportError(f"unsupported resource type: {extension}")
