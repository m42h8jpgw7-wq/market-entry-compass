"""Export: an Excel workbook that an analyst can audit, and a one-page brief.

The workbook contains everything needed to reproduce the ranking: the
assumptions, the weights, the raw values, the points per criterion and the
source of every indicator.
"""

import io
from datetime import date

import pandas as pd

from src.config import INDICATORS, PILLARS, pillar_of
from src.evidence import fmt_value

DISCLAIMER = (
    "Screening tool based on public national-level data. It is not a forecast and not "
    "investment, legal or tax advice. It cannot see competitors, licences, taxes, language, "
    "culture, regional differences or your product."
)


def scorecard_frames(ranking: pd.DataFrame, weights: dict) -> dict[str, pd.DataFrame]:
    """Tables behind the ranking, as plain data frames."""
    keys = [k for k in weights if f"pts_{k}" in ranking]
    pillar_cols = {f"p_{p}": PILLARS[p] for p in PILLARS if f"p_{p}" in ranking}

    summary = ranking[["rank", "country", "score", "coverage"] + list(pillar_cols)].rename(
        columns={"rank": "Rank", "country": "Country", "score": "Score (0-100)",
                 "coverage": "Data coverage", **pillar_cols})
    points = ranking[["rank", "country"] + [f"pts_{k}" for k in keys]].rename(
        columns={"rank": "Rank", "country": "Country",
                 **{f"pts_{k}": INDICATORS[k]["label"] for k in keys}})
    raw = ranking[["rank", "country"] + keys].rename(
        columns={"rank": "Rank", "country": "Country", **{k: INDICATORS[k]["label"] for k in keys}})
    weight_table = pd.DataFrame([
        {"Criterion": INDICATORS[k]["label"], "Pillar": PILLARS[pillar_of(k)],
         "Weight": weights[k], "Unit": INDICATORS[k]["unit"],
         "Question": INDICATORS[k]["question"]}
        for k in sorted(keys, key=lambda x: weights[x], reverse=True)])
    return {"ranking": summary, "points": points, "raw": raw, "weights": weight_table}


def sources_table(weights: dict, retrieved: str = "") -> pd.DataFrame:
    rows = []
    for key in sorted(weights, key=lambda k: weights[k], reverse=True):
        spec = INDICATORS[key]
        derived = spec.get("derived")
        rows.append({
            "Criterion": spec["label"],
            "Source": "Derived from home country and country centres" if derived else "World Bank",
            "Indicator code": "derived" if derived else spec["code"],
            "Unit": spec["unit"],
            "Direction": ("closer to " + str(spec.get("target")) + " is better"
                          if spec["higher_is_better"] == "target"
                          else ("higher is better" if spec["higher_is_better"] else "lower is better")),
            "Gap fill (years)": spec.get("carry", 0),
            "Retrieved": retrieved,
        })
    return pd.DataFrame(rows)


def assumptions_table(profile_lines: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame({"Assumption": list(profile_lines), "Value": list(profile_lines.values())})


def to_excel(ranking: pd.DataFrame, weights: dict, profile_lines: dict[str, str], robust: pd.DataFrame,
             loo: pd.DataFrame, gated: dict, year: int, retrieved: str = "") -> bytes:
    """Build the workbook and return its bytes."""
    frames = scorecard_frames(ranking, weights)
    ranking_sheet = frames["ranking"].copy()
    if not robust.empty:
        extra = robust.set_index("country")[["rank_best", "rank_worst", "p_first", "p_top3", "confidence"]]
        extra.columns = ["Best rank (10 %)", "Worst rank (90 %)", "Share ranked #1", "Share in top 3", "Confidence"]
        ranking_sheet = ranking_sheet.join(extra, on="Country")

    summary = pd.DataFrame({
        "Item": ["Tool", "Created", "Data year", "Data source", "Countries ranked", "Disclaimer"],
        "Value": ["Market Entry Compass", date.today().isoformat(), year,
                  f"World Bank open data, retrieved {retrieved or 'n/a'}", len(ranking), DISCLAIMER],
    })

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        assumptions_table(profile_lines).to_excel(writer, sheet_name="Assumptions", index=False)
        ranking_sheet.to_excel(writer, sheet_name="Ranking", index=False)
        frames["points"].to_excel(writer, sheet_name="Points per criterion", index=False)
        frames["raw"].to_excel(writer, sheet_name="Raw values", index=False)
        frames["weights"].to_excel(writer, sheet_name="Weights", index=False)
        if not robust.empty:
            robust.drop(columns=["iso3"]).to_excel(writer, sheet_name="Robustness", index=False)
        if not loo.empty:
            loo.to_excel(writer, sheet_name="Pivotal criteria", index=False)
        if gated:
            pd.DataFrame([{"Country": c, "Removed because": "; ".join(r)} for c, r in gated.items()]
                         ).to_excel(writer, sheet_name="Hard filters", index=False)
        sources_table(weights, retrieved).to_excel(writer, sheet_name="Sources", index=False)
        _format(writer)
    return buffer.getvalue()


def _format(writer) -> None:
    """Readable widths, frozen header row, percent and one-decimal formats."""
    from openpyxl.styles import Alignment, Font, PatternFill

    header_fill = PatternFill("solid", start_color="0B1F3A")
    for sheet in writer.book.worksheets:
        sheet.freeze_panes = "A2"
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = header_fill
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        for column in sheet.columns:
            width = max(len(str(c.value)) if c.value is not None else 0 for c in column[:60])
            sheet.column_dimensions[column[0].column_letter].width = min(max(width + 2, 10), 70)
        titles = [c.value for c in sheet[1]]
        for index, title in enumerate(titles, start=1):
            fmt = None
            if title in ("Data coverage", "Weight", "Share ranked #1", "Share in top 3"):
                fmt = "0%" if title != "Weight" else "0.0%"
            elif sheet.title in ("Ranking", "Points per criterion") and title not in ("Rank", "Country", "Confidence"):
                fmt = "0.0"
            if fmt:
                for row in sheet.iter_rows(min_row=2, min_col=index, max_col=index):
                    row[0].number_format = fmt


def brief_markdown(profile_lines: dict[str, str], summary_md: str, ranking: pd.DataFrame,
                   evidence: list[dict], year: int, retrieved: str = "", ai_text: str = "") -> str:
    """One-page brief as markdown, ready to paste into a memo or a pre-read."""
    lines = ["# Market entry screening: brief", "",
             f"Created {date.today().isoformat()} | World Bank data, reference year {year}"
             + (f", retrieved {retrieved}" if retrieved else ""), "",
             "## Assumptions", ""]
    lines += [f"- **{k}:** {v}" for k, v in profile_lines.items()]
    lines += ["", "## Summary", "", summary_md, "", "## Shortlist", "",
              "| Rank | Country | Score | Data coverage |", "|---|---|---|---|"]
    for row in ranking.head(10).itertuples():
        lines.append(f"| {int(row.rank)} | {row.country} | {row.score:.0f} | {row.coverage * 100:.0f} % |")
    lines += ["", "## Top markets in detail", ""]
    for ev in evidence[:3]:
        lines.append(f"### #{ev['rank']} {ev['country']} ({ev['score']:.0f}/100)")
        if ev.get("pillars"):
            lines.append("; ".join(f"{k} {v:.0f}" for k, v in ev["pillars"].items()))
        for item in ev["strengths"]:
            lines.append(f"- Strength: {item['label']}: {item['value_text']} ({item['points']:.0f}/100)")
        for item in ev["risks"]:
            lines.append(f"- Risk: {item['label']}: {item['value_text']} ({item['points']:.0f}/100)")
        if ev["missing"]:
            lines.append(f"- Data gap: {', '.join(ev['missing'])}")
        lines.append("")
    if ai_text:
        lines += ["## AI analysis", "", ai_text, ""]
    lines += ["## Limits", "", DISCLAIMER, ""]
    return "\n".join(lines)
