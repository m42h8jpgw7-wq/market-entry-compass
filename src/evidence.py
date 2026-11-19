"""Turn a ranking into checkable evidence: numbers, trends, strengths, risks.

This module feeds two things:
* the rule-based "data briefing" (works without any AI), and
* the AI advisor, which may only use the numbers collected here.
"""

import pandas as pd

from src.config import INDICATORS
from src.profile import StartupProfile

TREND_YEARS = 5


# ----------------------------------------------------------------- formatting
def fmt_value(key: str, value: float) -> str:
    """Human-readable value with unit."""
    if key in ("growth", "stability"):
        return f"{value:.1f} %"
    if key == "purchasing_power":
        return f"${value:,.0f}"
    if key == "market_size":
        return f"{value / 1e9:.2f} bn people" if value >= 1e9 else f"{value / 1e6:,.1f} m people"
    if key in ("digital", "account_ownership", "tertiary", "ict_exports"):
        return f"{value:.0f} %"
    if key == "rule_of_law":
        return f"{value:+.2f}"
    if key in ("mobile_subs", "broadband"):
        return f"{value:.0f} per 100 people"
    if key in ("private_credit", "rnd"):
        return f"{value:.1f} % of GDP"
    if key in ("researchers", "secure_servers"):
        return f"{value:,.0f} per million people"
    return f"{value:,.1f}"


def _goodness(key: str, value: float) -> float:
    """Higher = better for the startup (before any focus inversion)."""
    better = INDICATORS[key]["higher_is_better"]
    if better == "target":
        return -abs(value - INDICATORS[key]["target"])
    return value if better else -value


def _trend(panel: pd.DataFrame, iso3: str, key: str, year: int, now: float) -> dict | None:
    """Change over the last TREND_YEARS years, or None if there is no old value."""
    old_row = panel[(panel["iso3"] == iso3) & (panel["year"] == year - TREND_YEARS)]
    if old_row.empty or pd.isna(old_row.iloc[0][key]):
        return None
    old = float(old_row.iloc[0][key])

    if key == "market_size":
        change = (now / old - 1) * 100
        text = f"{change:+.1f} % since {year - TREND_YEARS}"
    elif key == "purchasing_power":
        change = (now / old - 1) * 100
        text = f"{change:+.0f} % since {year - TREND_YEARS}"
    else:
        change = now - old
        text = f"{fmt_value(key, old)} in {year - TREND_YEARS} -> {fmt_value(key, now)}"

    gain = _goodness(key, now) - _goodness(key, old)
    scale = max(abs(now), abs(old), 1e-9)
    direction = "flat" if abs(now - old) < 0.03 * scale else ("better" if gain > 0 else "worse")
    return {"text": text, "direction": direction, "old": old}


# ------------------------------------------------------------------- evidence
def country_evidence(panel, row: pd.Series, weights: dict, invert, year: int) -> dict:
    """All facts about one country that the briefing and the AI may use."""
    items, missing = [], []
    for key, weight in weights.items():
        if f"pts_{key}" not in row:
            continue
        if pd.isna(row[f"pts_{key}"]):
            missing.append(INDICATORS[key]["label"])
            continue
        spec = INDICATORS[key]
        value = float(row[key])
        points = float(row[f"pts_{key}"])
        items.append(
            {
                "key": key,
                "label": spec["label"],
                "unit": spec["unit"],
                "value": value,
                "value_text": fmt_value(key, value),
                "points": round(points, 1),
                "weight": round(weight, 3),
                "contribution": round(points * weight, 2),
                "inverted": key in invert,
                "trend": _trend(panel, row["iso3"], key, year, value),
            }
        )

    strengths = sorted((i for i in items if i["points"] >= 60),
                       key=lambda i: i["contribution"], reverse=True)[:3]
    risks = sorted((i for i in items if i["points"] < 40),
                   key=lambda i: i["weight"] * (100 - i["points"]), reverse=True)[:3]
    return {
        "iso3": row["iso3"],
        "country": row["country"],
        "rank": int(row["rank"]),
        "score": round(float(row["score"]), 1),
        "coverage": round(float(row.get("coverage", 1.0)), 2),
        "missing": missing,
        "indicators": items,
        "strengths": strengths,
        "risks": risks,
    }


def top_evidence(panel, ranking: pd.DataFrame, weights, invert, year, n: int = 6) -> list[dict]:
    return [country_evidence(panel, ranking.iloc[i], weights, invert, year)
            for i in range(min(n, len(ranking)))]


def evidence_for(panel, ranking, iso3, weights, invert, year) -> dict | None:
    match = ranking[ranking["iso3"] == iso3]
    if match.empty:
        return None
    return country_evidence(panel, match.iloc[0], weights, invert, year)


# ------------------------------------------------------------- rule-based text
def _line(item: dict) -> str:
    note = " (a low value is an opportunity for this focus)" if item["inverted"] else ""
    return (f"**{item['label']}**: {item['value_text']} "
            f"({item['points']:.0f}/100 points){note}")


def country_paragraph(ev: dict) -> str:
    """Markdown explanation for one country, built only from the numbers."""
    parts = [f"**#{ev['rank']} {ev['country']}: {ev['score']:.0f}/100 points**"]

    if ev["strengths"]:
        parts.append("**Why it fits:** " + "; ".join(_line(i) for i in ev["strengths"]) + ".")
    if ev["risks"]:
        parts.append("**Watch out:** " + "; ".join(_line(i) for i in ev["risks"]) + ".")
    else:
        parts.append("**Watch out:** no criterion scores below 40 points.")

    if ev["missing"]:
        parts.append(
            f"**Data gap:** no recent data for {', '.join(ev['missing'])}. The score is based on "
            f"{ev['coverage'] * 100:.0f} % of the weights, so treat it with extra care."
        )

    moves = [i for i in ev["indicators"] if i["trend"] and i["trend"]["direction"] != "flat"]
    moves.sort(key=lambda i: i["weight"], reverse=True)
    if moves:
        shown = [f"{i['label']} {i['trend']['direction']} ({i['trend']['text']})"
                 for i in moves[:3]]
        parts.append(f"**Trend (last {TREND_YEARS} years):** " + "; ".join(shown) + ".")
    return "\n\n".join(parts)


def briefing(profile: StartupProfile, evidence: list[dict], weights: dict,
             year: int, dropped: list[str]) -> str:
    """The full data briefing as markdown (no AI involved)."""
    focus = profile.focus_spec()
    top_weights = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)[:4]
    weight_text = ", ".join(f"{INDICATORS[k]['label']} {w * 100:.0f} %" for k, w in top_weights)

    out = [
        f"### Data briefing for your {profile.industry_label()} startup",
        f"*{focus['label']}.* {focus['text']}",
        f"The most important criteria for your profile: {weight_text}. "
        f"All values are from {year} (World Bank).",
    ]
    for ev in evidence[:3]:
        out.append(country_paragraph(ev))

    out.append(
        "**Read this carefully:** the ranking is a screening tool. It cannot see your product, "
        "local competitors, taxes, licences or language. "
        + (f"Not enough data for: {', '.join(dropped)}." if dropped else "")
    )
    return "\n\n".join(out)
