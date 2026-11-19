"""Turn raw indicators into a 0-100 attractiveness score per country.

Method (kept deliberately simple and explainable):
1. Take the value of every indicator for one year. If a year is missing for a
   country, carry the last known value forward (the allowed number of years
   is set per indicator in config.py; survey data is published rarely).
2. Convert each indicator to 0-100 points ("min-max scaling"). Extreme
   outliers are capped at the 5th / 95th percentile first, so that one crazy
   value (e.g. 200 % inflation) does not squash everyone else.
3. Multiply each sub-score by its weight and add everything up. The weights
   come from the startup profile (industry, business model, priorities).
"""

import numpy as np
import pandas as pd

from src.config import GATES, INDICATORS, PILLARS, pillar_of


def build_panel(long_data: pd.DataFrame) -> pd.DataFrame:
    """Long table -> one row per (iso3, year), one column per indicator."""
    present = [k for k in INDICATORS if k in set(long_data["indicator"])]

    wide = long_data.pivot_table(
        index=["iso3", "year"], columns="indicator", values="value"
    ).reindex(columns=present)

    names = long_data.drop_duplicates("iso3").set_index("iso3")["country"]
    years = range(int(long_data["year"].min()), int(long_data["year"].max()) + 1)

    # Every country gets a row for every year, so completely missing years
    # can be filled from the last known value.
    grid = pd.MultiIndex.from_product([names.index, years], names=["iso3", "year"])
    panel = wide.reindex(grid).sort_index()

    for key in present:
        carry = INDICATORS[key].get("carry", 3)
        panel[key] = panel.groupby(level="iso3")[key].ffill(limit=carry)

    panel = panel.reset_index()
    panel["country"] = panel["iso3"].map(names)
    return panel[["iso3", "country", "year"] + present]


def available_indicators(panel: pd.DataFrame) -> set[str]:
    return {k for k in INDICATORS if k in panel.columns}


def _scale_0_100(series: pd.Series, key: str, invert: bool = False) -> pd.Series:
    """Convert one indicator column into 0-100 points."""
    spec = INDICATORS[key]
    values = series.astype(float)

    if spec.get("log"):
        values = np.log10(values.clip(lower=1e-6))

    better = spec["higher_is_better"]
    if better == "target":
        values = -(values - spec["target"]).abs()
    elif better is False:
        values = -values
    if invert:
        values = -values

    low, high = values.quantile(0.05), values.quantile(0.95)
    if high == low:
        return pd.Series(50.0, index=series.index)
    return (values.clip(low, high) - low) / (high - low) * 100


def _gate_failures(snapshot: pd.DataFrame, gates: list[dict]) -> dict[str, list[str]]:
    """Countries that break a hard filter -> list of reasons. Missing data passes."""
    failures: dict[str, list[str]] = {}
    for gate in gates or []:
        key, op, limit = gate["key"], gate["op"], gate["value"]
        if key not in snapshot.columns:
            continue
        spec = GATES.get(key, {})
        for row in snapshot[["iso3", "country", key]].itertuples(index=False):
            value = row[2]
            if pd.isna(value):
                continue
            broken = value < limit if op == ">=" else value > limit
            if broken:
                label = INDICATORS[key]["label"]
                shown = value / spec.get("scale", 1)
                wanted = limit / spec.get("scale", 1)
                failures.setdefault(row.country, []).append(
                    f"{label} {shown:,.1f} is {'below' if op == '>=' else 'above'} {wanted:,.1f}"
                )
    return failures


def score_year(
    panel: pd.DataFrame,
    year: int,
    weights: dict,
    invert: set | frozenset = frozenset(),
    exclude: tuple | list = (),
    min_coverage: float = 0.7,
    method: str = "arithmetic",
    gates: list[dict] | None = None,
) -> pd.DataFrame:
    """Score every country for one year. Returns a ranked table.

    Every country in the data set is scaled together (so the home country is a
    fair benchmark), then `exclude` removes countries from the ranking (e.g. the
    home country). If a country lacks some indicators, its score is computed
    from the criteria it has (weights renormalised). Countries whose available
    criteria cover less than `min_coverage` of the total weight are left out.

    method   "arithmetic": weighted average of points (a strength can offset a
             weakness). "balanced": weighted geometric mean (a very weak
             criterion drags the score down, like a weakest-link rule).
    gates    hard filters [{"key", "op", "value"}]; countries failing one are
             removed and listed in `.attrs["gated"]`.

    Side information is stored in `.attrs`: dropped, gated, active, excluded
    (the excluded countries' rows with scores as a list of dicts, a benchmark).
    """
    active = [k for k, w in weights.items() if w > 0 and k in panel.columns]
    total = sum(weights[k] for k in active)
    w = pd.Series({k: weights[k] / total for k in active})

    snapshot = panel[panel["year"] == year].copy()
    if snapshot.empty:
        snapshot.attrs.update(dropped=[], gated={}, active=active, excluded=[])
        return snapshot

    for key in active:
        snapshot[f"pts_{key}"] = _scale_0_100(snapshot[key], key, key in invert)

    pts = snapshot[[f"pts_{k}" for k in active]]
    present = pts.notna()
    covered = (present * w.values).sum(axis=1)  # share of the weight with data
    snapshot["coverage"] = covered
    denom = covered.where(covered > 0)
    if method == "balanced":
        logs = np.log(pts.clip(lower=1.0)).fillna(0)
        snapshot["score"] = np.exp((logs * w.values).sum(axis=1) / denom)
    else:
        snapshot["score"] = (pts.fillna(0) * w.values).sum(axis=1) / denom

    # pillar sub-scores: the same average, restricted to the criteria of one pillar
    for pillar in PILLARS:
        members = [k for k in active if pillar_of(k) == pillar]
        if not members:
            continue
        wp = w[members]
        part = pts[[f"pts_{k}" for k in members]]
        share = (part.notna() * wp.values).sum(axis=1)
        snapshot[f"p_{pillar}"] = (part.fillna(0) * wp.values).sum(axis=1) / share.where(share > 0)

    excluded = snapshot[snapshot["iso3"].isin(exclude)].copy()
    snapshot = snapshot[~snapshot["iso3"].isin(exclude)]

    gated = _gate_failures(snapshot, gates)
    dropped = sorted(snapshot.loc[snapshot["coverage"] < min_coverage, "country"])
    keep = (snapshot["coverage"] >= min_coverage) & ~snapshot["country"].isin(gated)
    snapshot = snapshot[keep].sort_values("score", ascending=False).reset_index(drop=True)
    snapshot["rank"] = snapshot.index + 1
    snapshot.attrs.update(dropped=dropped, gated=gated, active=active,
                          excluded=excluded.to_dict("records"))
    return snapshot


def score_history(panel, weights, invert=frozenset(), exclude=(), min_countries=15, method="arithmetic"):
    """Score for every country and every year (used for the time line chart)."""
    frames = []
    for year in sorted(panel["year"].unique()):
        frame = score_year(panel, int(year), weights, invert, exclude, method=method)
        if len(frame) >= min_countries:
            frames.append(frame[["iso3", "country", "year", "score", "rank"]])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def latest_complete_year(panel, weights, exclude=(), min_countries=20, method="arithmetic") -> int:
    """Newest year in which at least `min_countries` can be scored."""
    for year in sorted(panel["year"].unique(), reverse=True):
        if len(score_year(panel, int(year), weights, exclude=exclude, method=method)) >= min_countries:
            return int(year)
    raise ValueError("Not enough complete data. Run: python -m src.fetch_data")


def excluded_frame(ranking: pd.DataFrame) -> pd.DataFrame:
    """The excluded countries (e.g. home) with their scores, for benchmarking."""
    return pd.DataFrame(ranking.attrs.get("excluded", []))
