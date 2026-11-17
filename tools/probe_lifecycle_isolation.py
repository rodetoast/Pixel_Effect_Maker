"""Bounded offscreen synthetic lifecycle observations; no user payload or paths."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import argparse
import json
from pathlib import Path
import sys
import tempfile
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QThreadPool
from PySide6.QtTest import QTest
from pytest import MonkeyPatch
import pytest
from app.services import particle_render_service as render
from tests import test_v9_editor_lifecycle_integration as lifecycle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--precede', action='append', default=[])
    parser.add_argument('--attempts', type=int, choices=range(1, 25), default=12)
    parser.add_argument('--output', required=True)
    parser.add_argument('--closed-owner', action='store_true')
    parser.add_argument('--verify-fixed', action='store_true')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(exist_ok=False, parents=True)
    if args.precede:
        code = pytest.main([*args.precede, '-q', '-p', 'no:cacheprovider', '--basetemp='+str(output/'preceding')])
        if code: return int(code)
    observations = []
    for attempt in range(args.attempts):
        if args.verify_fixed:
            with tempfile.TemporaryDirectory(dir=output) as directory:
                lifecycle.test_ui_navigation_state_does_not_dirty_project(Path(directory))
            observations.append(dict(attempt=attempt, contract='PASS'))
            continue
        events = []; phase = ['setup']; owner = [None]
        original = render.render_particle_frame
        def observe(project, *a, **kw):
            before = dict(render.PARTICLE_RENDER_STATS)
            stack = [frame.name for frame in traceback.extract_stack(limit=12)[:-1]]
            result = original(project, *a, **kw)
            if phase[0] != 'setup':
                events.append(dict(phase=phase[0], owner_current=project is owner[0], stack=stack,
                                   delta={k:render.PARTICLE_RENDER_STATS[k]-v for k,v in before.items()}))
            return result
        with tempfile.TemporaryDirectory(dir=output) as directory, MonkeyPatch.context() as patch:
            patch.setattr(render, 'render_particle_frame', observe)
            previous = None
            if args.closed_owner:
                p,_,_,_,_ = lifecycle.production_project(Path(directory), 'orbit', animated=True)
                previous = lifecycle.window_for(Path(directory), p, 'previous')
                previous.select_resource_layer(p.effect_resource_layers[0].id)
                # A pending idle prewarm is not a running thread-pool worker.
                previous.dirty=False; previous._non_undo_dirty=False; previous.close()
            project,_,composition,layer,effect = lifecycle.production_project(Path(directory), 'orbit', animated=True)
            owner[0] = project
            window = lifecycle.window_for(Path(directory), project)
            try:
                editor = lifecycle.select_resource_layer_editor(window, composition, layer)
                assert QThreadPool.globalInstance().waitForDone(2500)
                lifecycle.APP.processEvents()
                before = dict(render.PARTICLE_RENDER_STATS)
                pending = window.interactive_proxy_prewarm._pending is not None
                phase[0] = 'resource_navigation'
                editor.composition_canvas.zoom=2.0; editor.controller.set_frame(8); editor._apply_state(editor.controller.state)
                phase[0] = 'effect_selection'
                window.select_resource_layer(effect.id)
                phase[0] = 'event_dispatch'
                if previous is not None:previous.interactive_proxy_prewarm._timer.start(0)
                window.canvas.zoom=1.5
                lifecycle.APP.processEvents()
                after = dict(render.PARTICLE_RENDER_STATS)
                observations.append(dict(attempt=attempt, baseline_prewarm_pending=pending,
                    navigation_prewarm_pending=window.interactive_proxy_prewarm._pending is not None,
                    delta={k:after[k]-v for k,v in before.items()}, events=list(events)))
            finally:
                phase[0] = 'cleanup'
                for item in (window, previous):
                    if item is not None:
                        item.interactive_proxy_prewarm.cancel(); item.interactive_proxy_prewarm._poll.stop()
                        lifecycle.finish(item); item.deleteLater()
                assert QThreadPool.globalInstance().waitForDone(2500)
                lifecycle.APP.processEvents()
    (output/'observations.json').write_text(json.dumps(observations, indent=2), encoding='utf-8')
    print(json.dumps(observations, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
