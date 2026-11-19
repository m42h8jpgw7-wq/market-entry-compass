"""Tests for the institutional layer: pillars, hard filters, methods, robustness,
distance, scenario state and the Excel export. All numbers are invented."""

import io
import json

import numpy as np
import pandas as pd
import pytest

from src.analytics import (add_distance_columns, executive_summary, haversine_km, leave_one_out,
                           robustness, summary_text)
from src.config import BUSINESS_MODELS, BUDGET_MULTIPLIERS, GATES, INDICATORS, INDUSTRIES, INSTITUTIONAL_BLOCK, PILLARS, PRIORITIES, pillar_of
from src.evidence import top_evidence
from src.export import brief_markdown, to_excel
from src.profile import StartupProfile, build_weights
from src.scoring import build_panel, score_year
from src.state import answers_to_params, params_to_answers, scenario_from_json, scenario_to_json
from tests.test_scoring import make_long_data


@pytest.fixture
def ranking():
    panel = build_panel(make_long_data())
    w = {"growth": 0.3, "digital": 0.3, "rule_of_law": 0.2, "stability": 0.2}
    return score_year(panel, 2024, w), w, panel


def profile(priority="balanced"):
    return StartupProfile(industry="fintech", focus="payments", business_model=next(iter(BUSINESS_MODELS)),
                          priority=priority, budget=next(iter(BUDGET_MULTIPLIERS)), stage="Idea")


# ----------------------------------------------------------------- weights
def test_institutional_block_sums_to_one():
    assert sum(INSTITUTIONAL_BLOCK.values()) == pytest.approx(1.0)


@pytest.mark.parametrize("priority", list(PRIORITIES))
def test_weights_sum_to_one_with_block(priority):
    keys = set(INDICATORS) - {"dist_geo", "dist_econ"}
    w, _ = build_weights(profile(priority), keys)
    assert sum(w.values()) == pytest.approx(1.0)
    assert any(k in w for k in INSTITUTIONAL_BLOCK)


def test_safety_gives_block_more_weight_than_growth():
    keys = set(INDICATORS) - {"dist_geo", "dist_econ"}
    share = lambda p: sum(v for k, v in build_weights(profile(p), keys)[0].items() if k in INSTITUTIONAL_BLOCK)
    assert share("safety") > share("balanced") > share("growth")


def test_every_indicator_has_a_valid_pillar():
    for key in INDICATORS:
        assert pillar_of(key) in PILLARS


def test_overrides_zero_removes_indicator():
    keys = set(INDICATORS) - {"dist_geo", "dist_econ"}
    w, _ = build_weights(profile(), keys, overrides={"growth": 0})
    assert "growth" not in w


def test_extra_share_is_respected():
    keys = set(INDICATORS) | {"dist_geo"}
    w, _ = build_weights(profile(), keys, extra={"dist_geo": 0.2})
    assert w["dist_geo"] == pytest.approx(0.2)


# ----------------------------------------------------------------- scoring
def test_gates_remove_countries(ranking):
    _, w, panel = ranking
    r = score_year(panel, 2024, w, gates=[{"key": "market_size", "op": ">=", "value": 20e6}])
    assert "Land DDD" not in set(r["country"])
    assert "Land DDD" in r.attrs["gated"]


def test_gate_passes_missing_data():
    data = make_long_data()
    data = data[~((data.iso3 == "DDD") & (data.indicator == "market_size"))]
    panel = build_panel(data)
    r = score_year(panel, 2024, {"growth": 1.0}, gates=[{"key": "market_size", "op": ">=", "value": 20e6}])
    assert "Land DDD" in set(r["country"])


def test_balanced_punishes_weak_criterion_more(ranking):
    _, w, panel = ranking
    a = score_year(panel, 2024, w, method="arithmetic").set_index("iso3")["score"]
    b = score_year(panel, 2024, w, method="balanced").set_index("iso3")["score"]
    assert (b <= a + 1.0).all()  # +1: the geometric mean floors points at 1


def test_pillar_columns_exist():
    panel = build_panel(make_long_data())
    r = score_year(panel, 2024, {"growth": 0.5, "rule_of_law": 0.5})
    assert any(c.startswith("p_") for c in r.columns)


def test_home_country_is_benchmark_not_ranked():
    panel = build_panel(make_long_data())
    r = score_year(panel, 2024, {"growth": 1.0}, exclude=("BBB",))
    assert "BBB" not in set(r["iso3"])
    assert r.attrs["excluded"][0]["iso3"] == "BBB"


# -------------------------------------------------------------- robustness
def test_robustness_is_deterministic(ranking):
    r, w, _ = ranking
    pd.testing.assert_frame_equal(robustness(r, w), robustness(r, w))


def test_robustness_columns_and_bounds(ranking):
    r, w, _ = ranking
    rb = robustness(r, w)
    assert rb["p_first"].sum() == pytest.approx(1.0)
    assert (rb["rank_best"] <= rb["rank_worst"]).all()
    assert rb["confidence"].isin(["High", "Medium", "Low"]).all()
    assert rb.iloc[0]["country"] == r.iloc[0]["country"]


def test_dominant_country_is_always_first(ranking):
    r, w, _ = ranking
    rb = robustness(r, w)
    assert rb.iloc[0]["p_first"] == 1.0


def test_leave_one_out_shape(ranking):
    r, w, _ = ranking
    loo = leave_one_out(r, w)
    assert len(loo) == len(w)
    assert {"Criterion ignored", "Weight", "New #1", "Leader changes"} <= set(loo.columns)


def test_leave_one_out_finds_pivotal_criterion():
    data = make_long_data()
    data.loc[(data.iso3 == "DDD") & (data.indicator == "digital"), "value"] = 200
    panel = build_panel(data)
    w = {"digital": 0.6, "growth": 0.4}
    r = score_year(panel, 2024, w)
    loo = leave_one_out(r, w)
    assert loo[loo["Criterion ignored"] == INDICATORS["digital"]["label"]]["Leader changes"].iloc[0]


# ---------------------------------------------------------------- distance
def test_haversine_known_distance():
    assert haversine_km((52.5, 13.4), (48.9, 2.35)) == pytest.approx(878, abs=15)  # Berlin-Paris


def test_distance_columns_home_zero():
    panel = pd.DataFrame({"iso3": ["DEU", "FRA"], "year": [2024, 2024], "purchasing_power": [50000, 45000]})
    out = add_distance_columns(panel, "DEU")
    assert out.loc[0, "dist_geo"] == pytest.approx(0, abs=1e-6)
    assert out.loc[1, "dist_geo"] > 500
    assert out.loc[0, "dist_econ"] == pytest.approx(0)


def test_distance_without_home_is_nan():
    panel = pd.DataFrame({"iso3": ["FRA"], "year": [2024], "purchasing_power": [45000]})
    assert add_distance_columns(panel, "").loc[0, "dist_geo"] != add_distance_columns(panel, "").loc[0, "dist_geo"]


# ----------------------------------------------------------------- summary
def test_summary_text_mentions_leader(ranking):
    r, w, _ = ranking
    rb, loo = robustness(r, w), leave_one_out(r, w)
    s = executive_summary(r, rb, loo, 2024, "arithmetic", {})
    text = summary_text(s, r)
    assert r.iloc[0]["country"] in text and "Confidence" in text


# ------------------------------------------------------------------- state
def test_params_roundtrip():
    ans = {"industry": "fintech", "focus": "payments", "business_model": next(iter(BUSINESS_MODELS)),
           "budget": next(iter(BUDGET_MULTIPLIERS)), "priority": "growth", "home": "DEU"}
    assert params_to_answers(answers_to_params(ans)) == ans


def test_bad_params_never_crash():
    assert params_to_answers({"ind": "nonsense"}) is None
    out = params_to_answers({"ind": "fintech", "foc": "zzz", "pri": "zzz", "home": "XXX"})
    assert out["focus"] in INDUSTRIES["fintech"]["focuses"] and out["home"] == "DEU"


def test_scenario_roundtrip_and_validation():
    ans = {"industry": "saas", "focus": "b2b_saas", "business_model": next(iter(BUSINESS_MODELS)),
           "budget": next(iter(BUDGET_MULTIPLIERS)), "priority": "safety", "home": "DEU", "description": "x"}
    text = scenario_to_json(ans, {"method": "balanced", "closeness": 10, "overrides": {"growth": 50}, "gates": {}})
    got, ass = scenario_from_json(text)
    assert got["industry"] == "saas" and ass["method"] == "balanced" and ass["closeness"] == 10


@pytest.mark.parametrize("bad", ["", "not json", "[]", json.dumps({"answers": {"ind": "x"}}), "null"])
def test_bad_scenario_returns_none(bad):
    assert scenario_from_json(bad) is None


def test_scenario_clamps_numbers():
    ans = {"industry": "saas", "focus": "b2b_saas"}
    text = json.dumps({"answers": {"industry": "saas", "focus": "b2b_saas"},
                       "assumptions": {"method": "evil", "closeness": 999, "gates": {"nope": 1}}})
    _, ass = scenario_from_json(text)
    assert ass["method"] == "arithmetic" and ass["closeness"] == 30 and ass["gates"] == {}


# ------------------------------------------------------------------ export
def test_excel_has_expected_sheets(ranking):
    r, w, panel = ranking
    rb, loo = robustness(r, w), leave_one_out(r, w)
    data = to_excel(r, w, {"Industry": "Fintech"}, rb, loo, {"Land X": ["too small"]}, 2024, "2026-11-19")
    sheets = pd.ExcelFile(io.BytesIO(data)).sheet_names
    for name in ("Summary", "Assumptions", "Ranking", "Points per criterion", "Raw values", "Weights",
                 "Robustness", "Pivotal criteria", "Hard filters", "Sources"):
        assert name in sheets


def test_brief_markdown_contains_disclaimer(ranking):
    r, w, panel = ranking
    ev = top_evidence(panel, r, w, frozenset(), 2024, n=3)
    md = brief_markdown({"Industry": "Fintech"}, "summary", r, ev, 2024, "2026-11-19")
    assert "Shortlist" in md and "not investment" in md
