import json

import pytest
from PIL import Image

from app.models.project import FORMAT_VERSION, Project
from app.services.project_io import ProjectIOError, load_project
from app.services import resource_import_service
from app.services.resource_import_service import ResourceImportError, import_resource


def write_project(tmp_path, data, name="project.peffect.json"):
    path = tmp_path / name
    path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    return path


@pytest.mark.parametrize("contents", ["", "{", '{"format_version":8}'])
def test_incomplete_project_is_rejected(tmp_path, contents):
    path = tmp_path / "bad.peffect.json"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(ProjectIOError):
        load_project(path)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity", "1e9999"])
def test_non_finite_json_number_is_rejected(tmp_path, constant):
    data = Project.create_default().to_dict()
    text = json.dumps(data).replace('"fps": 12', f'"fps": {constant}')
    path = tmp_path / "nonfinite.peffect.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ProjectIOError, match="non-finite"):
        load_project(path)


def test_future_format_has_specific_safe_rejection(tmp_path):
    data = Project.create_default().to_dict()
    data["format_version"] = FORMAT_VERSION + 1
    with pytest.raises(ProjectIOError) as caught:
        load_project(write_project(tmp_path, data))
    assert caught.value.code == "load_future_format"
    assert "newer application version" in str(caught.value)


def test_duplicate_frame_ids_are_rejected(tmp_path):
    project = Project.create_default()
    project.add_frame()
    data = project.to_dict()
    data["frames"][1]["id"] = data["frames"][0]["id"]
    with pytest.raises(ProjectIOError, match="frame IDs must be unique"):
        load_project(write_project(tmp_path, data))


def test_v8_missing_layer_payload_is_rejected_instead_of_filled(tmp_path):
    data = Project.create_default().to_dict()
    data["frames"][0]["layer_pixels"] = {}
    with pytest.raises(ProjectIOError, match="missing layer pixel payloads"):
        load_project(write_project(tmp_path, data))


def test_duplicate_composition_layer_ids_are_rejected(tmp_path):
    data = Project.create_default().to_dict()
    data["resource_compositions"] = [{
        "id": "composition", "name": "C", "width": 8, "height": 8,
        "fps": 12, "frame_count": 1, "loop": True,
        "background_mode": "transparent", "layers": [
            {"id": "duplicate", "name": "A", "source_type": "source_asset", "source_id": "missing", "start_frame": 0, "end_frame": 0},
            {"id": "duplicate", "name": "B", "source_type": "source_asset", "source_id": "missing", "start_frame": 0, "end_frame": 0},
        ],
    }]
    with pytest.raises(ProjectIOError, match="composition layer IDs must be unique"):
        load_project(write_project(tmp_path, data))


def test_png_over_safe_dimension_is_rejected_before_project_mutation(tmp_path, monkeypatch):
    path = tmp_path / "large.png"
    Image.new("RGBA", (2, 2)).save(path)
    monkeypatch.setattr(resource_import_service, "MAX_RESOURCE_DIMENSION", 1)
    with pytest.raises(ResourceImportError, match="dimensions exceed"):
        import_resource(path)


def test_gif_over_safe_frame_count_is_rejected(tmp_path, monkeypatch):
    path = tmp_path / "animated.gif"
    frames = [Image.new("RGBA", (2, 2), (index, 0, 0, 255)) for index in range(2)]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=50)
    monkeypatch.setattr(resource_import_service, "MAX_GIF_FRAMES", 1)
    with pytest.raises(ResourceImportError, match="frame count"):
        import_resource(path)


def test_compact_project_total_pixel_budget_is_enforced(tmp_path):
    data = Project.create_default().to_dict()
    payload = dict(next(iter(data["frames"][0]["layer_pixels"].values())))
    payload["byte_length"] = 64 * 1024 * 1024
    data["frames"] = [
        {"id": f"frame-{index}", "name": "F", "layer_pixels": {data["layers"][0]["id"]: dict(payload)}}
        for index in range(9)
    ]
    with pytest.raises(ProjectIOError, match="safe load limit"):
        load_project(write_project(tmp_path, data))
