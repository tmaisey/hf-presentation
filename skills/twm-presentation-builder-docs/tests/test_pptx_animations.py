"""Spec: PB-022

Build steps written as native PowerPoint animations (`p:timing`) on a python-pptx slide:
entrance, exit, emphasis and motion-path effects, one click per step, round-tripping through
save → reopen. Every assertion reads the *saved and reopened* file.

Coverage: happy (one click per step, every effect's preset class/id and end state, shared
clicks, order, round trip, schema structure, sample deck) · edge (shape animated twice,
re-writing replaces timing, non-text shapes get no build entry) · negative (foreign shape,
unknown effect, bad params, empty step, empty step list).
"""

from __future__ import annotations

import pytest
from lxml import etree
from pptx.enum.shapes import MSO_CONNECTOR
from pptx.util import Inches

import helper_pptx as h

anim = h.load_script("animations")

# Preset class / id / subtype per effect: the values PowerPoint's preset library uses
# (ECMA-376 Part 1 §19.5.29 presetClass/presetID; ids as PowerPoint saves them).
EXPECTED_PRESETS = {
    "appear": ("entr", "1", "0"),
    "fade_in": ("entr", "10", "0"),
    "disappear": ("exit", "1", "0"),
    "fade_out": ("exit", "10", "0"),
    "transparency": ("emph", "9", "0"),
    "grow_shrink": ("emph", "6", "0"),
    "fill_colour": ("emph", "1", "2"),
    "motion_path": ("path", "0", "0"),
}
PARAMS = {
    "transparency": {"opacity": 0.4},
    "grow_shrink": {"scale": 1.5},
    "fill_colour": {"rgb": "C0392B"},
    "motion_path": {"path": "M 0 0 L 0.25 0.1 E"},
}


def step(shape, effect):
    """One (shape, effect, params) entry with the default test params for `effect`."""
    return (shape, effect, PARAMS.get(effect, {}))


def _set_values(ctn, attr):
    """`p:set` target values for attribute `attr` under an effect cTn."""
    out = []
    for s in ctn.iter(h.P + "set"):
        if s.find("p:cBhvr/p:attrNameLst/p:attrName", h.NS).text == attr:
            out.append(s.find("p:to/p:strVal", h.NS).get("val"))
    return out


# --- happy paths -------------------------------------------------------------------------


def test_each_step_is_one_click_in_order(tmp_path):
    prs, [slide], [shapes] = h.new_deck(3)
    anim.write_steps(slide, [[step(s, "fade_in")] for s in shapes])
    groups = h.click_groups(h.reopen(prs, tmp_path / "d.pptx"))
    assert [[e["spid"] for e in g] for g in groups] == [[str(s.shape_id)] for s in shapes]


@pytest.mark.parametrize("effect", sorted(EXPECTED_PRESETS))
def test_effect_targets_shape_with_powerpoint_preset(tmp_path, effect):
    prs, [slide], [shapes] = h.new_deck(1)
    anim.write_steps(slide, [[step(shapes[0], effect)]])
    sld = h.reopen(prs, tmp_path / "d.pptx")
    [[e]] = h.click_groups(sld)
    assert (e["presetClass"], e["presetID"], e["presetSubtype"]) == EXPECTED_PRESETS[effect]
    assert e["spid"] == str(shapes[0].shape_id)
    assert h.structural_errors(sld) == []


def test_effects_table_covers_the_four_preset_classes():
    assert {c for c, _, _ in anim.EFFECTS.values()} == {"entr", "exit", "emph", "path"}
    assert {k: tuple(map(str, v)) for k, v in anim.EFFECTS.items()} == EXPECTED_PRESETS


def test_entrances_end_visible_and_exits_end_hidden(tmp_path):
    prs, [slide], [shapes] = h.new_deck(4)
    effects = ["appear", "fade_in", "disappear", "fade_out"]
    anim.write_steps(slide, [[step(s, e)] for s, e in zip(shapes, effects)])
    groups = h.click_groups(h.reopen(prs, tmp_path / "d.pptx"))
    ends = [_set_values(g[0]["ctn"], "style.visibility") for g in groups]
    assert ends == [["visible"], ["visible"], ["hidden"], ["hidden"]]
    fades = [
        [(f.get("transition", "in"), f.get("filter")) for f in g[0]["ctn"].iter(h.P + "animEffect")]
        for g in groups
    ]
    assert fades == [[], [("in", "fade")], [], [("out", "fade")]]


def test_fade_out_hides_only_after_the_fade(tmp_path):
    """The hide must not fire before the fade has played, or the fade is invisible."""
    prs, [slide], [shapes] = h.new_deck(1)
    anim.write_steps(slide, [[(shapes[0], "fade_out", {"duration_ms": 800})]])
    [[e]] = h.click_groups(h.reopen(prs, tmp_path / "d.pptx"))
    fade = e["ctn"].find(".//p:animEffect/p:cBhvr/p:cTn", h.NS)
    hide = next(s for s in e["ctn"].iter(h.P + "set")).find("p:cBhvr/p:cTn", h.NS)
    hide_at = int(hide.find("p:stCondLst/p:cond", h.NS).get("delay"))
    assert fade.get("dur") == "800" and 0 < hide_at < 800 <= hide_at + int(hide.get("dur"))


def test_emphasis_and_path_params_reach_the_file(tmp_path):
    prs, [slide], [shapes] = h.new_deck(4)
    effects = ["transparency", "grow_shrink", "fill_colour", "motion_path"]
    anim.write_steps(slide, [[step(s, e)] for s, e in zip(shapes, effects)])
    trans, grow, fill, path = (g[0]["ctn"] for g in h.click_groups(h.reopen(prs, tmp_path / "d.pptx")))
    assert _set_values(trans, "style.opacity") == ["0.4"]
    by = grow.find(".//p:animScale/p:by", h.NS)
    assert (by.get("x"), by.get("y")) == ("150000", "150000")
    clr = fill.find(".//p:animClr", h.NS)
    assert clr.find("p:cBhvr/p:attrNameLst/p:attrName", h.NS).text == "fillcolor"
    assert clr.find("p:to/a:srgbClr", h.NS).get("val") == "C0392B"
    motion = path.find(".//p:animMotion", h.NS)
    assert motion.get("path") == "M 0 0 L 0.25 0.1 E"
    assert [a.text for a in motion.findall("p:cBhvr/p:attrNameLst/p:attrName", h.NS)] == ["ppt_x", "ppt_y"]


def test_several_shapes_share_one_click(tmp_path):
    prs, [slide], [[a, b, c]] = h.new_deck(3)
    anim.write_steps(slide, [[step(a, "fade_in"), step(b, "appear"), step(c, "motion_path")], [step(a, "fade_out")]])
    groups = h.click_groups(h.reopen(prs, tmp_path / "d.pptx"))
    assert [len(g) for g in groups] == [3, 1]
    assert [e["nodeType"] for e in groups[0]] == ["clickEffect", "withEffect", "withEffect"]
    assert [e["spid"] for e in groups[0]] == [str(a.shape_id), str(b.shape_id), str(c.shape_id)]


def test_timing_survives_a_second_python_pptx_round_trip(tmp_path):
    prs, [slide], [shapes] = h.new_deck(2)
    anim.write_steps(slide, [[step(shapes[0], e)] for e in EXPECTED_PRESETS])
    first = h.reopen(prs, tmp_path / "a.pptx")
    from pptx import Presentation

    again = Presentation(tmp_path / "a.pptx")
    second = h.reopen(again, tmp_path / "b.pptx")
    assert etree.tostring(h.timing(first)) == etree.tostring(h.timing(second))
    assert h.structural_errors(second) == []


def test_text_shapes_get_one_build_entry_per_effect_group(tmp_path):
    prs, [slide], [[a, b]] = h.new_deck(2)
    anim.write_steps(slide, [[step(a, "fade_in"), step(b, "fade_in")], [step(a, "fade_out")]])
    tm = h.timing(h.reopen(prs, tmp_path / "d.pptx"))
    blds = {(x.get("spid"), x.get("grpId")) for x in tm.findall("p:bldLst/p:bldP", h.NS)}
    assert blds == {(str(a.shape_id), "0"), (str(b.shape_id), "0"), (str(a.shape_id), "1")}


def test_every_effect_validates_against_pml_schema(tmp_path):
    xsd = h.find_pml_xsd()
    if xsd is None:
        pytest.skip("no transitional pml.xsd found (set PB_OOXML_SCHEMAS)")
    schema = etree.XMLSchema(etree.parse(str(xsd)))
    prs, [slide], [[a, b]] = h.new_deck(2)
    anim.write_steps(slide, [[step(a, e), step(b, e)] for e in EXPECTED_PRESETS])
    sld = h.reopen(prs, tmp_path / "d.pptx")
    assert len(h.click_groups(sld)) == len(EXPECTED_PRESETS)
    assert schema.validate(sld), str(schema.error_log)


def test_sample_deck_exercises_every_effect():
    """Writes the presenter's playback check file (open in PowerPoint, click through)."""
    prs, slides, shapes = h.new_deck(3, n_slides=2)
    a, b, c = shapes[0]
    for shp, label in zip(shapes[0], ["A: fade in, grow, fade out", "B: appear, recolour, path", "C: with B, fade, disappear"]):
        shp.text = label
    anim.write_steps(
        slides[0],
        [
            [step(a, "fade_in")],
            [step(b, "appear"), step(c, "fade_in")],
            [step(a, "grow_shrink"), step(b, "fill_colour")],
            [step(c, "transparency")],
            [step(b, "motion_path")],
            [step(a, "fade_out"), step(c, "disappear")],
        ],
    )
    x, y, z = shapes[1]
    for shp, label in zip(shapes[1], ["each click: one effect", "shrink to 60%", "move down-left"]):
        shp.text = label
    anim.write_steps(
        slides[1],
        [
            [step(x, "appear")],
            [(y, "grow_shrink", {"scale": 0.6})],
            [(z, "motion_path", {"path": "M 0 0 L -0.2 0.3 E"})],
            [(x, "transparency", {"opacity": 0.2})],
        ],
    )
    h.ARTIFACTS.mkdir(exist_ok=True)
    out = h.ARTIFACTS / "pb-022-sample.pptx"
    prs.save(out)
    from pptx import Presentation

    reopened = Presentation(out)
    seen = set()
    for s in reopened.slides:
        assert h.structural_errors(s._element) == []
        seen |= {(e["presetClass"], e["presetID"], e["presetSubtype"]) for g in h.click_groups(s._element) for e in g}
    assert seen == set(EXPECTED_PRESETS.values())


# --- edges -------------------------------------------------------------------------------


def test_shape_animated_twice_gets_distinct_group_ids(tmp_path):
    prs, [slide], [[a]] = h.new_deck(1)
    anim.write_steps(slide, [[step(a, "fade_in")], [step(a, "grow_shrink")], [step(a, "fade_out")]])
    groups = h.click_groups(h.reopen(prs, tmp_path / "d.pptx"))
    assert [g[0]["grpId"] for g in groups] == ["0", "1", "2"]


def test_rewriting_replaces_the_previous_timing(tmp_path):
    prs, [slide], [[a, b]] = h.new_deck(2)
    anim.write_steps(slide, [[step(a, "fade_in")], [step(b, "fade_in")]])
    anim.write_steps(slide, [[step(b, "appear")]])
    sld = h.reopen(prs, tmp_path / "d.pptx")
    assert [[e["spid"] for e in g] for g in h.click_groups(sld)] == [[str(b.shape_id)]]
    assert h.structural_errors(sld) == []


def test_non_text_shape_animates_without_a_build_entry(tmp_path):
    """bldP is a paragraph-build record; PowerPoint writes none for shapes without text."""
    prs, [slide], _ = h.new_deck(0)
    line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(1), Inches(1), Inches(4), Inches(2))
    anim.write_steps(slide, [[step(line, "fade_in")]])
    sld = h.reopen(prs, tmp_path / "d.pptx")
    assert [[e["spid"] for e in g] for g in h.click_groups(sld)] == [[str(line.shape_id)]]
    assert h.timing(sld).findall("p:bldLst/p:bldP", h.NS) == []
    assert h.structural_errors(sld) == []


# --- negatives ---------------------------------------------------------------------------


def test_empty_step_list_writes_no_timing_and_clears_old(tmp_path):
    prs, [slide], [[a]] = h.new_deck(1)
    anim.write_steps(slide, [[step(a, "fade_in")]])
    anim.write_steps(slide, [])
    assert h.timing(h.reopen(prs, tmp_path / "d.pptx")) is None


def test_shape_from_another_slide_raises_and_writes_nothing(tmp_path):
    prs, [s0, s1], [[a], [foreign]] = h.new_deck(1, n_slides=2)
    with pytest.raises(ValueError, match="not on this slide"):
        anim.write_steps(s0, [[step(a, "fade_in")], [step(foreign, "fade_in")]])
    assert h.timing(h.reopen(prs, tmp_path / "d.pptx")) is None


@pytest.mark.parametrize(
    "effect, params",
    [
        ("spin_wildly", {}),
        ("motion_path", {}),
        ("motion_path", {"path": "L 1 1 E"}),
        ("transparency", {"opacity": 1.5}),
        ("grow_shrink", {"scale": 0}),
        ("fill_colour", {"rgb": "red"}),
        ("fade_in", {"duration_ms": 0}),
    ],
)
def test_bad_effect_or_params_raise(effect, params):
    _, [slide], [[a]] = h.new_deck(1)
    with pytest.raises(ValueError):
        anim.write_steps(slide, [[(a, effect, params)]])
    assert h.timing(slide._element) is None


def test_empty_step_raises():
    """A step with no effects would be a dead click in the show."""
    _, [slide], [[a]] = h.new_deck(1)
    with pytest.raises(ValueError, match="empty"):
        anim.write_steps(slide, [[step(a, "fade_in")], []])
