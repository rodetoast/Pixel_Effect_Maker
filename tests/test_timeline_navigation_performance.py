from time import perf_counter
import pytest

from app.ui.timeline_multi_key import TimelineKey
from app.ui.timeline_time_view import TimelineTimeView,navigation_frame


@pytest.mark.parametrize("key_count",[1000,5000])
def test_navigation_scans_large_visible_key_sets_without_project_work(key_count):
    keys={TimelineKey(f"layer-{index%100}","resource",f"property-{index%10}",index) for index in range(key_count)};started=perf_counter();animated={(key.layer_id,key.property_id) for key in keys};animated_ms=(perf_counter()-started)*1000;started=perf_counter();frames=[key.frame for key in keys];width=TimelineTimeView().fit_width(1200,min(frames),max(frames));fit_ms=(perf_counter()-started)*1000;started=perf_counter();target=navigation_frame(frames,300,1);navigation_ms=(perf_counter()-started)*1000
    assert animated and width>=8 and target is not None and animated_ms<200 and fit_ms<200 and navigation_ms<200
