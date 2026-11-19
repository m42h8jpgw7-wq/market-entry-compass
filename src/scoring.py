"""Turn raw indicators into a 0-100 attractiveness score per country.

Method (kept deliberately simple and explainable):
1. Take the value of every indicator for one year. If a year is missing for a
   country, carry the last known value forward (at most 3 years).
2. Convert each indicator to a 0-100 sub-score ("min-max scaling").
   Extreme outliers are capped at the 5th / 95th percentile first, so that
   one crazy value (e.g. 40 % inflation) does not squash everyone else.
3. Multiply each sub-score by its weight and add everything up.
"""

import pandas as pd

from src.config import DEFAULT_WEIGHTS, INDICATORS


def build_panel(long_data: pd.DataFrame, max_carry_years: int = 3) -> pd.DataFrame:
    """Long table -> one row per (iso3, year) with one column per indicator."""
    panel = long_data.pivot_table(
        index=["iso3", "country", "year"], columns="indicator", values="value"
    ).reset_index()

    keep = ["iso3", "country", "year"] + list(INDICATORS)
    panel = panel.reindex(columns=keep)

    # Make sure every country has a row for every year. Otherwise a year that
    # is completely missing for one country could not be filled.
    names = panel.drop_duplicates("iso3").set_index("iso3")["country"]
    full_grid = pd.MultiIndex.from_product(
        [names.index, sorted(panel["year"].unique())], names=["iso3", "year"]
    )
    panel = (
        panel.drop(columns="country")
        .set_index(["iso3", "year"])
        .reindex(full_grid)
        .reset_index()
    )
    panel["country"] = panel["iso3"].map(names)

    # Fill small gaps: use the last known value of the same country.
    panel = panel.sort_values(["iso3", "year"])
    panel[list(INDICATORS)] = panel.groupby("iso3")[list(INDICATORS)].ffill(
        limit=max_carry_years
    )
    return panel


def _scale_0_100(series: pd.Series, spec: dict) -> pd.Series:
    """Convert one indicator column into 0-100 points."""
    values = series.copy()

    # "target" indicators (inflation): the closer to the target, the better.
    if spec["higher_is_better"] == "target":
        values = -(values - spec["target"]).abs()

    low, high = values.quantile(0.05), values.quantile(0.95)
    if high == low:
        return pd.Series(50.0, index=series.index)

    capped = values.clip(low, high)
    return (capped - low) / (high - low) * 100


def score_year(panel: pd.DataFrame, year: int, weights: dict | None = None) -> pd.DataFrame:
    """Score every country for one year. Returns a ranked table."""
    weights = weights or DEFAULT_WEIGHTS
    total = sum(weights.values())
    weights = {key: value / total for key, value in weights.items()}  # sum to 1

    snapshot = panel[panel["year"] == year].dropna(subset=list(INDICATORS)).copy()
    if snapshot.empty:
        return snapshot

    for key, spec in INDICATORS.items():
        snapshot[f"pts_{key}"] = _scale_0_100(snapshot[key], spec)

    snapshot["score"] = sum(
        snapshot[f"pts_{key}"] * weights[key] for key in INDICATORS
    )
    snapshot = snapshot.sort_values("score", ascending=False).reset_index(drop=True)
    snapshot["rank"] = snapshot.index + 1
    return snapshot


def score_history(panel: pd.DataFrame, weights: dict | None = None) -> pd.DataFrame:
    """Score for every country and every year (used for the time line chart)."""
    frames = [score_year(panel, year, weights) for year in sorted(panel["year"].unique())]
    frames = [frame for frame in frames if not frame.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def latest_complete_year(panel: pd.DataFrame, min_countries: int = 20) -> int:
    """Newest year in which at least `min_countries` have all indicators."""
    complete = panel.dropna(subset=list(INDICATORS)).groupby("year")["iso3"].nunique()
    complete = complete[complete >= min_countries]
    if complete.empty:
        raise ValueError("Not enough complete data. Run: python -m src.fetch_data")
    return int(complete.index.max())


def explain(row: pd.Series, weights: dict | None = None) -> str:
    """Short, rule-based reasoning for one country (every claim is checkable)."""
    weights = weights or DEFAULT_WEIGHTS
    contributions = {
        key: row[f"pts_{key}"] * weights[key] / sum(weights.values())
        for key in INDICATORS
    }
    best = sorted(INDICATORS, key=lambda k: row[f"pts_{k}"], reverse=True)[:2]
    worst = min(INDICATORS, key=lambda k: row[f"pts_{k}"])

    def describe(key: str) -> str:
        label = INDICATORS[key]["label"].split(" (")[0]
        return f"{label} ({row[key]:.1f}; {row[f'pts_{key}']:.0f}/100 points)"

    text = (
        f"{row['country']} ranks #{int(row['rank'])} with {row['score']:.0f}/100 points. "
        f"Strongest: {describe(best[0])} and {describe(best[1])}. "
        f"Weakest: {describe(worst)}."
    )
    # Name every criterion that scores very low, not only one (several can tie).
    risks = [k for k in INDICATORS if row[f"pts_{k}"] < 30]
    if risks:
        names = ", ".join(INDICATORS[k]["label"].split(" (")[0] for k in risks)
        questions = " ".join(INDICATORS[k]["question"] for k in risks)
        text += f" Risk areas (under 30 points): {names}. Check first: {questions}"
    return text
