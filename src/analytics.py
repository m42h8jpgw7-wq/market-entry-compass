"""Checks on top of the ranking: how robust is it, and what would change it?

A ranking is only useful for a decision if you know how much to trust it. This
module answers three questions that investment committees ask:

* Robustness: if the weights were a bit different, would the order change?
* Pivotal criteria: which single criterion, if ignored, changes the leader?
* Distance: how far is each market from the home market?
"""

import numpy as np
import pandas as pd

from src.config import INDICATORS
from src.geo import CENTROIDS

# How strongly the weights are shaken in the robustness test. A factor of
# exp(sigma * z) is applied to every weight, z from a standard normal.
UNCERTAINTY = {"low": 0.3, "medium": 0.6, "high": 1.0}


# ---------------------------------------------------------------- robustness
def _scores(points: np.ndarray, mask: np.ndarray, weights: np.ndarray, method: str) -> np.ndarray:
    """Scores for many weight vectors at once. weights: (draws, criteria)."""
    covered = mask @ weights.T                              # (countries, draws)
    covered = np.where(covered > 0, covered, np.nan)
    if method == "balanced":
        logs = np.log(np.clip(points, 1.0, None)) * mask
        return np.exp((logs @ weights.T) / covered)
    return (np.nan_to_num(points) * mask) @ weights.T / covered


def robustness(ranking: pd.DataFrame, weights: dict, draws: int = 1000, sigma: float = 0.6,
               seed: int = 7, method: str = "arithmetic") -> pd.DataFrame:
    """Shake the weights randomly and see how the ranks move.

    Returns one row per country: the base rank, the 10th/90th percentile rank
    over all scenarios, the share of scenarios in which it is #1 and in the
    top 3, and a confidence label (High / Medium / Low). Seeded, so the same
    input always gives the same output.
    """
    keys = [k for k in ranking.attrs.get("active", []) if k in weights and f"pts_{k}" in ranking]
    if ranking.empty or not keys:
        return pd.DataFrame()
    points = ranking[[f"pts_{k}" for k in keys]].to_numpy(dtype=float)
    mask = (~np.isnan(points)).astype(float)
    base = np.array([weights[k] for k in keys], dtype=float)

    rng = np.random.default_rng(seed)
    shaken = base * np.exp(sigma * rng.standard_normal((draws, len(keys))))
    scores = _scores(points, mask, shaken, method)           # (countries, draws)
    ranks = (-np.nan_to_num(scores, nan=-1)).argsort(axis=0).argsort(axis=0) + 1

    out = pd.DataFrame({
        "iso3": ranking["iso3"].to_numpy(),
        "country": ranking["country"].to_numpy(),
        "rank": ranking["rank"].to_numpy(),
        "rank_best": np.percentile(ranks, 10, axis=1).round().astype(int),
        "rank_worst": np.percentile(ranks, 90, axis=1).round().astype(int),
        "p_first": (ranks == 1).mean(axis=1),
        "p_top3": (ranks <= 3).mean(axis=1),
    })
    out["rank_band"] = out["rank_worst"] - out["rank_best"]
    out["confidence"] = [
        _confidence(cov, band) for cov, band in zip(ranking["coverage"], out["rank_band"])
    ]
    return out


def _confidence(coverage: float, band: int) -> str:
    """High: complete data and a stable rank. Low: data gaps or a rank that jumps around."""
    if coverage >= 0.9 and band <= 4:
        return "High"
    if coverage >= 0.8 and band <= 8:
        return "Medium"
    return "Low"


def leave_one_out(ranking: pd.DataFrame, weights: dict, method: str = "arithmetic") -> pd.DataFrame:
    """For every criterion: who would lead if it were ignored?"""
    keys = [k for k in ranking.attrs.get("active", []) if k in weights and f"pts_{k}" in ranking]
    if len(keys) < 2 or ranking.empty:
        return pd.DataFrame()
    points = ranking[[f"pts_{k}" for k in keys]].to_numpy(dtype=float)
    mask = (~np.isnan(points)).astype(float)
    base = np.array([weights[k] for k in keys], dtype=float)
    leader, top3 = ranking.iloc[0]["country"], set(ranking.head(3)["country"])

    rows = []
    for i, key in enumerate(keys):
        w = base.copy()
        w[i] = 0.0
        score = _scores(points, mask, w[None, :], method)[:, 0]
        order = np.argsort(-np.nan_to_num(score, nan=-1))
        new_top3 = [ranking.iloc[j]["country"] for j in order[:3]]
        rows.append({
            "Criterion ignored": INDICATORS[key]["label"],
            "Weight": base[i],
            "New #1": new_top3[0],
            "Leader changes": new_top3[0] != leader,
            "Top 3 changes": set(new_top3) != top3,
        })
    return pd.DataFrame(rows).sort_values("Weight", ascending=False, ignore_index=True)


# ------------------------------------------------------------------ distance
def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance between two (lat, lon) points in km."""
    lat1, lon1, lat2, lon2 = map(np.radians, (*a, *b))
    h = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return float(2 * 6371.0 * np.arcsin(np.sqrt(h)))


def add_distance_columns(panel: pd.DataFrame, home: str) -> pd.DataFrame:
    """Add `dist_geo` (km) and `dist_econ` (gap in log GDP per person) to the panel.

    Two of the four CAGE distances (Ghemawat) can be measured with open data:
    geographic and economic. Cultural and administrative distance cannot, so
    they are not pretended here.
    """
    out = panel.copy()
    if not home or home not in CENTROIDS:
        out["dist_geo"] = np.nan
        out["dist_econ"] = np.nan
        return out
    out["dist_geo"] = out["iso3"].map(
        lambda iso: haversine_km(CENTROIDS[home], CENTROIDS[iso]) if iso in CENTROIDS else np.nan)
    home_income = out[out["iso3"] == home].set_index("year")["purchasing_power"]
    gap = np.log(out["purchasing_power"].clip(lower=1)) - np.log(out["year"].map(home_income).clip(lower=1))
    out["dist_econ"] = gap.abs()
    return out


# ------------------------------------------------------------------- summary
def executive_summary(ranking: pd.DataFrame, robust: pd.DataFrame, loo: pd.DataFrame,
                      year: int, method: str, gated: dict, home_name: str = "") -> dict:
    """The few facts a decision maker reads first, as plain text pieces."""
    top = ranking.iloc[0]
    second = ranking.iloc[1] if len(ranking) > 1 else None
    out = {"leader": top["country"], "score": float(top["score"]),
           "gap": float(top["score"] - second["score"]) if second is not None else float("nan"),
           "runner_up": second["country"] if second is not None else ""}

    if not robust.empty:
        row = robust[robust["iso3"] == top["iso3"]].iloc[0]
        out.update(confidence=row["confidence"], p_first=float(row["p_first"]),
                   p_top3=float(row["p_top3"]), rank_best=int(row["rank_best"]),
                   rank_worst=int(row["rank_worst"]))
        close = robust.sort_values("p_first", ascending=False).head(2)
        out["no_clear_leader"] = bool(len(close) > 1 and close.iloc[0]["p_first"] < 0.5)
    pivotal = loo[loo["Leader changes"]] if not loo.empty else loo
    out["pivotal"] = list(pivotal["Criterion ignored"]) if not pivotal.empty else []
    out["gated_count"] = len(gated)
    out["year"] = year
    out["method"] = method
    return out


def summary_text(s: dict, ranking: pd.DataFrame) -> str:
    """Executive summary as markdown (rule-based, no AI)."""
    top = ranking.iloc[0]
    parts = [f"**{s['leader']}** leads with **{s['score']:.0f}/100** points"
             + (f", {s['gap']:.1f} points ahead of {s['runner_up']}." if s["runner_up"] else ".")]
    if "confidence" in s:
        parts.append(
            f"**Confidence: {s['confidence']}.** In {s['p_first'] * 100:.0f} % of 1,000 simulated weight "
            f"scenarios {s['leader']} is ranked first and in {s['p_top3'] * 100:.0f} % in the top three "
            f"(rank range {s['rank_best']}-{s['rank_worst']})."
        )
        if s.get("no_clear_leader"):
            parts.append("**No clear leader:** the top markets swap places under small weight changes. "
                         "Treat the top group as a shortlist, not as one answer.")
    if s["pivotal"]:
        parts.append("**The answer depends on:** " + ", ".join(s["pivotal"][:3])
                     + ". Ignoring any of these would put another country first.")
    elif "confidence" in s:
        parts.append("**No single criterion decides it:** dropping any one criterion keeps the same leader.")
    weak = [c for c in ranking.attrs.get("active", [])
            if f"pts_{c}" in ranking and pd.notna(top.get(f"pts_{c}")) and top[f"pts_{c}"] < 40]
    if weak:
        worst = min(weak, key=lambda c: top[f"pts_{c}"])
        parts.append(f"**Main weakness of {s['leader']}:** {INDICATORS[worst]['label']} "
                     f"({top[f'pts_{worst}']:.0f}/100 points).")
    if s["gated_count"]:
        parts.append(f"{s['gated_count']} countries were removed by your hard filters.")
    return "\n\n".join(parts)
