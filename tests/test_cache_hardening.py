import os
from queue import SimpleQueue

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from app.frame_payload_codec import SourceFramePayloadCodec
from app.ui.interactive_proxy_prewarm import InteractiveCompositeCache,ProxyPrewarmFailure,_PrewarmWorker
from app.services import effect_resource_layer_render_service, particle_render_service
from app.services import resource_composition_render_service


APP = QApplication.instance() or QApplication([])


def test_encoded_payload_lru_evicts_oldest_entry():
    codec = SourceFramePayloadCodec(compression_level=0, maximum_cache_bytes=150)
    first = np.zeros((4, 4, 4), dtype=np.uint8)
    second = np.ones((4, 4, 4), dtype=np.uint8)
    codec.encode(first, "first")
    codec.encode(second, "second")
    assert len(codec._cache) == 1
    assert next(iter(codec._cache))[0] == "second"
    assert codec.current_cache_bytes <= codec.maximum_cache_bytes


def test_composite_lru_respects_byte_limit_and_evicts_oldest():
    cache = InteractiveCompositeCache(maximum_bytes=100)
    pixmap = QPixmap(2, 2)
    cache.put((1, "first"), pixmap, pixmap, 80)
    cache.put((1, "second"), pixmap, pixmap, 80)
    assert len(cache) == 1
    assert cache.get((1, "first")) is None
    assert cache.get((1, "second")) is not None
    assert cache.evictions == 1


def test_project_switch_cache_invalidators_clear_all_render_caches():
    resource_composition_render_service._CACHE[("old",)] = []
    effect_resource_layer_render_service._BASE_CACHE["old"] = ((), [])
    effect_resource_layer_render_service._TRANSFORM_CACHE[("old",)] = np.zeros((1,1,4),dtype=np.uint8)
    effect_resource_layer_render_service._TRANSFORM_CACHE_BYTES = 4
    particle_render_service._SPAWN_STATE_CACHE[("old",)] = ()
    particle_render_service._RESOURCE_CLIP_CACHE[("old",)] = object()
    resource_composition_render_service.invalidate_composition_cache()
    effect_resource_layer_render_service.invalidate_effect_resource_layer_base()
    particle_render_service.invalidate_particle_render_caches()
    assert not resource_composition_render_service._CACHE
    assert not effect_resource_layer_render_service._BASE_CACHE
    assert not effect_resource_layer_render_service._TRANSFORM_CACHE
    assert not particle_render_service._SPAWN_STATE_CACHE
    assert not particle_render_service._RESOURCE_CLIP_CACHE


def test_prewarm_worker_failure_is_reported_to_its_queue(monkeypatch):
    from types import SimpleNamespace
    queue = SimpleQueue()
    token = object()
    worker = _PrewarmWorker(SimpleNamespace(token=token), queue)
    monkeypatch.setattr(
        worker, "_run_guarded", lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    worker.run()
    result = queue.get_nowait()
    assert isinstance(result, ProxyPrewarmFailure)
    assert result.token is token
