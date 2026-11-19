"""Tests for the scoring logic, using small invented numbers (test-only data)."""

import pandas as pd

from src.config import INDICATORS
from src.scoring import build_panel, explain, latest_complete_year, score_year


def make_long_data() -> pd.DataFrame:
    """Four fake countries for 2022-2023. 'AAA' is better than 'DDD' everywhere."""
    base = {
        "AAA": dict(growth=6, purchasing_power=60000, stability=2, digital=95, rule_of_law=1.5),
        "BBB": dict(growth=4, purchasing_power=40000, stability=4, digital=80, rule_of_law=0.8),
        "CCC": dict(growth=2, purchasing_power=20000, stability=9, digital=60, rule_of_law=-0.3),
        "DDD": dict(growth=-1, purchasing_power=5000, stability=40, digital=20, rule_of_law=-1.5),
    }
    rows = []
    for iso3, values in base.items():
        for year in (2022, 2023):
            for indicator, value in values.items():
                rows.append(dict(iso3=iso3, country=f"Land {iso3}", indicator=indicator,
                                 year=year, value=value))
    return pd.DataFrame(rows)


def test_best_country_ranks_first_and_worst_last():
    panel = build_panel(make_long_data())
    ranking = score_year(panel, 2023)
    assert ranking.iloc[0]["iso3"] == "AAA"
    assert ranking.iloc[-1]["iso3"] == "DDD"


def test_scores_are_between_0_and_100():
    ranking = score_year(build_panel(make_long_data()), 2023)
    assert ranking["score"].between(0, 100).all()


def test_changing_weights_changes_ranking():
    panel = build_panel(make_long_data())
    only_digital = {k: 0 for k in INDICATORS}
    only_digital["digital"] = 1
    ranking = score_year(panel, 2023, only_digital)
    assert ranking.iloc[0]["iso3"] == "AAA"
    assert ranking.iloc[0]["score"] > ranking.iloc[-1]["score"]


def test_inflation_close_to_target_beats_high_inflation():
    panel = build_panel(make_long_data())
    only_stability = {k: 0 for k in INDICATORS}
    only_stability["stability"] = 1
    ranking = score_year(panel, 2023, only_stability)
    assert ranking.iloc[0]["iso3"] == "AAA"  # 2 % inflation = on target


def test_missing_year_is_filled_with_last_value():
    data = make_long_data()
    data = data[~((data["iso3"] == "BBB") & (data["year"] == 2023))]
    panel = build_panel(data)
    assert not score_year(panel, 2023).empty
    assert "BBB" in score_year(panel, 2023)["iso3"].values


def test_latest_complete_year_and_explanation():
    panel = build_panel(make_long_data())
    assert latest_complete_year(panel, min_countries=4) == 2023
    ranking = score_year(panel, 2023)
    text = explain(ranking.iloc[-1])
    assert "ranks #4" in text and "Weakest" in text
