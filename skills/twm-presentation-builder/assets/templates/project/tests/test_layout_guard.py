"""Spec: S-0NN

Always-on layout guard: every slide × step × review size (1920×1080, 1280×720, 1288×598) of the
assembled deck is free of overlap, overflow, off-canvas and occlusion faults, checked by the
presentation-builder skill's ``layout_guard.guard`` (run in-process; it launches Chrome in a worker
thread, so it works beside other sync Playwright fixtures). Replace ``S-0NN`` with every visual
spec this guard covers, adding each id as its slides land.

Coverage: one case per slide, so each slide's spec goes red/green on its own; every step and review
size of that slide.
"""

import pytest

from helper_skill_tools import DECK, REVIEW_SIZES, slide_ids, tool


@pytest.fixture(scope="module")
def report():
    """One guard run over the whole deck, shared by the per-slide cases."""
    assert DECK.is_file(), f"deck missing: {DECK}"
    return tool("layout_guard").guard(DECK, REVIEW_SIZES)


@pytest.mark.parametrize("slide", slide_ids() or ["(no deck yet)"])
def test_slide_is_layout_clean_at_every_step_and_review_size(report, slide):
    faults = [f"{f['slide']}@{f['step']} {f['size']} {f['kind']}: {f['check']}: {f['target']}"
              for f in report["faults"] if f["slide"] == slide]
    assert report["states"] > 0
    assert faults == [], "\n".join(faults)
