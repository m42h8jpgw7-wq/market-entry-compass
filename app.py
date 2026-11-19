"""Market Entry Compass - find the best first foreign market for your startup.

Start with:  streamlit run app.py
"""

import hashlib
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.advisor import AdvisorError, stream_advice
from src.analytics import (
    UNCERTAINTY, add_distance_columns, executive_summary, leave_one_out, robustness, summary_text,
)
from src.config import (
    BUDGET_MULTIPLIERS, BUSINESS_MODELS, DATA_FILE, GATES, INDICATORS, INDUSTRIES, PILLARS, PRIORITIES,
    pillar_of,
)
from src.evidence import briefing, country_paragraph, evidence_for, top_evidence
from src.evidence import fmt_value
from src.export import DISCLAIMER, brief_markdown, scorecard_frames, sources_table, to_excel
from src.state import answers_to_params, params_to_answers, scenario_from_json, scenario_to_json
from src.geo import CENTROIDS
from src.profile import StartupProfile, build_weights
from src.scoring import (
    available_indicators, build_panel, latest_complete_year, score_history, score_year,
)

from src.ui import (
    AMBER, BLUE, CSS, GLOBE_BG, GLOBE_LAND, GLOBE_LINE, GLOBE_SCALE, INK, LINE, MUTED,
    badge, chips, hero, kpis, memo, question, ranking_table, tile, top_picks, topbar,
)

st.set_page_config(page_title="Market Entry Compass", page_icon="🧭", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data
def load_panel() -> pd.DataFrame:
    return build_panel(pd.read_csv(DATA_FILE))


def country_names(panel: pd.DataFrame) -> dict:
    return panel.drop_duplicates("iso3").set_index("iso3")["country"].to_dict()


# ------------------------------------------------------------------- data
if not Path(DATA_FILE).exists():
    st.error("No data found yet. Run this in the terminal first:  python -m src.fetch_data")
    st.stop()

panel = load_panel()
names = country_names(panel)
have = available_indicators(panel)

# ------------------------------------------------------------- guided questions
STEPS = ["industry", "focus", "customers", "money", "priority", "home", "details"]
ss = st.session_state
ss.setdefault("step", 0)
ss.setdefault("done", False)
ss.setdefault("ans", {"business_model": "b2b", "budget": "low", "priority": "balanced",
                      "home": "DEU", "description": "", "notes": "", "industry_name": ""})
ans = ss["ans"]
ss.setdefault("picked", set())  # answers the user chose, so no card starts out highlighted

# A shared link or an uploaded scenario can fill in the answers and skip the questions.
if "loaded" not in ss:
    ss["loaded"] = True
    preset = params_to_answers(st.query_params)
    if preset:
        ans.update(preset)
        ss["done"] = True
if "pending_scenario" in ss:
    new_answers, new_assumptions = ss.pop("pending_scenario")
    ans.update(new_answers)
    ss["done"] = True
    ss["a_method"] = new_assumptions["method"]
    ss["a_close"] = int(new_assumptions["closeness"])
    for gate_key, gate in GATES.items():
        ss[f"g_on_{gate_key}"] = gate_key in new_assumptions["gates"]
        ss[f"g_val_{gate_key}"] = float(new_assumptions["gates"].get(gate_key, gate["default"] * gate["scale"])
                                        / gate["scale"])
    for w_key, pct in new_assumptions["overrides"].items():
        ss[f"w_{ans['industry']}_{ans['focus']}_{w_key}"] = int(pct)


def choose(field: str, value: str, jump: int | None = None):
    """Save an answer and go to the next question."""
    if field == "industry" and ans.get("industry") != value:
        ans.pop("focus", None)
        if value == "other":
            ans["focus"] = "general"
    ans[field] = value
    ss["picked"].add(field)
    ss["step"] = jump if jump is not None else ss["step"] + 1


def go_back():
    step = ss["step"] - 1
    if STEPS[step] == "focus" and ans.get("industry") == "other":
        step -= 0  # "other" still shows the name question on this step
    ss["step"] = max(step, 0)


def tiles(field: str, options: list[tuple[str, str, str]], columns: int = 3):
    """Big clickable choices. options = [(value, title, description)]."""
    for start in range(0, len(options), columns):
        row = st.columns(columns, gap="small")
        for col, (value, title, desc) in zip(row, options[start:start + columns]):
            with col.container(key=f"tile_{field}_{value}"):
                st.markdown(tile(title, desc), unsafe_allow_html=True)
                st.button("Choose", key=f"btn_{field}_{value}", width="stretch",
                          type="primary" if field in ss["picked"] and ans.get(field) == value else "secondary",
                          on_click=choose, args=(field, value))


def show_results():
    ss["done"] = True


def edit_answers():
    ss["done"] = False
    ss["step"] = 0


if not ss["done"]:
    step = ss["step"]
    if step == 0:
        st.markdown(hero(), unsafe_allow_html=True)
    else:
        st.markdown('<div class="mec-hero"><div class="brand">Market Entry Compass</div></div>',
                    unsafe_allow_html=True)
    with st.container(key="wizard"):
        st.progress((step + 1) / len(STEPS))
        top_l, top_r = st.columns([1, 4])
        top_r.markdown(f'<div class="mec-step" style="text-align:right">Question {step + 1} of {len(STEPS)}</div>',
                       unsafe_allow_html=True)
        if step > 0:
            top_l.button("Back", key="back", type="tertiary", on_click=go_back)

        name = STEPS[step]
        if name == "industry":
            st.markdown(question("What kind of startup do you have?",
                                 "Pick the closest match. If nothing fits, choose \"Something else\"."),
                        unsafe_allow_html=True)
            tiles("industry", [(k, v["label"], v["description"]) for k, v in INDUSTRIES.items()])

        elif name == "focus":
            ind = INDUSTRIES[ans["industry"]]
            if ans["industry"] == "other":
                st.markdown(question("What industry are you in?",
                                     "Just a few words. We then compare countries on the criteria every startup needs."),
                            unsafe_allow_html=True)
                ans["industry_name"] = st.text_input("Your industry", value=ans.get("industry_name", ""),
                                                     placeholder="e.g. farming technology, legal services, gaming")
                st.button("Continue", type="primary", on_click=choose, args=("focus", "general"))
            else:
                st.markdown(question(f"What exactly does your {ind['label'].lower()} startup do?",
                                     "Pick the closest match. You can change it later."),
                            unsafe_allow_html=True)
                tiles("focus", [(k, v["label"], v["text"]) for k, v in ind["focuses"].items()])

        elif name == "customers":
            st.markdown(question("Who will pay for your product?"), unsafe_allow_html=True)
            tiles("business_model", [(k, v["label"], v["hint"]) for k, v in BUSINESS_MODELS.items()])

        elif name == "money":
            st.markdown(question("How much money do you have to expand abroad?",
                                 "A small budget makes safe, predictable countries more important."),
                        unsafe_allow_html=True)
            tiles("budget", [(k, v["label"], v["hint"]) for k, v in BUDGET_MULTIPLIERS.items()])

        elif name == "priority":
            st.markdown(question("What matters most when choosing a country?"), unsafe_allow_html=True)
            tiles("priority", [(k, v["label"], v["hint"]) for k, v in PRIORITIES.items()])

        elif name == "home":
            st.markdown(question("Where is your startup based today?",
                                 "We leave this country out, because you are looking for a foreign market."),
                        unsafe_allow_html=True)
            options = sorted(names, key=names.get) + ["(none)"]
            ans["home"] = st.selectbox("Home country", options,
                                       index=options.index(ans["home"]) if ans["home"] in options else 0,
                                       format_func=lambda k: "Another country" if k == "(none)" else names[k])
            st.button("Continue", type="primary", on_click=choose, args=("home", ans["home"]))

        elif name == "details":
            st.markdown(question("Anything else we should know?",
                                 "Optional. The more you tell us, the better the written advice. You can skip this."),
                        unsafe_allow_html=True)
            ans["description"] = st.text_area(
                "What does your startup do, and for whom?", value=ans.get("description", ""), height=130,
                placeholder="e.g. We help small online shops get paid within 24 hours instead of 30 days.")
            ans["notes"] = st.text_input(
                "Limits or wishes", value=ans.get("notes", ""),
                placeholder="e.g. our team speaks English and German; no budget for licences this year")
            st.button("Show my results", type="primary", on_click=show_results)
    st.stop()


# ------------------------------------------------------------------ results
profile = StartupProfile(
    industry=ans["industry"], focus=ans["focus"], business_model=ans["business_model"],
    priority=ans["priority"], budget=ans["budget"], description=ans["description"],
    home_country="" if ans["home"] == "(none)" else ans["home"], extra_notes=ans["notes"],
    industry_name=ans["industry_name"],
)
industry, focus = profile.industry, profile.focus
focuses = INDUSTRIES[industry]["focuses"]
home = profile.home_country
home_name = names.get(home, "")

# the answers live in the page address, so a result can be shared as a link
params = answers_to_params(ans)
if dict(st.query_params) != params:
    st.query_params.from_dict(params)

META = {}
try:
    META = json.loads(Path(DATA_FILE).with_name("meta.json").read_text())
except (OSError, ValueError):
    pass
retrieved = META.get("retrieved", "")

head_l, head_r = st.columns([5, 1], vertical_alignment="center")
head_l.markdown(topbar(f"World Bank open data, {META.get('years', '')}"
                       + (f", retrieved {retrieved}" if retrieved else "")), unsafe_allow_html=True)
head_r.button("Change answers", on_click=edit_answers, width="stretch")
st.markdown(chips([
    profile.industry_label(), focuses[focus]["label"] if industry != "other" else "General criteria",
    f"Customers: {BUSINESS_MODELS[profile.business_model]['label']}",
    f"Budget: {BUDGET_MULTIPLIERS[profile.budget]['label']}",
    f"Priority: {PRIORITIES[profile.priority]['label']}",
    f"Based in: {home_name or 'another country'}",
]), unsafe_allow_html=True)

# --------------------------------------------------------------- assumptions
# Everything an analyst may want to change sits here, above the results.
if home:
    panel = add_distance_columns(panel, home)
    have = have | {"dist_geo", "dist_econ"}
base_weights, _ = build_weights(profile, have)

with st.expander("Assumptions: scoring method, filters, weights"):
    a1, a2, a3 = st.columns(3, gap="large")
    method = a1.radio(
        "How to combine the criteria", ["arithmetic", "balanced"], key="a_method",
        format_func=lambda m: {"arithmetic": "Weighted average", "balanced": "Balanced (weakest link)"}[m],
        help="Weighted average: a strength can offset a weakness. Balanced (weighted geometric mean): "
             "a very weak criterion pulls the score down, so one-sided markets rank lower.")
    uncertainty = a2.select_slider(
        "How unsure are the weights?", list(UNCERTAINTY), value="medium", key="a_unc",
        format_func=str.capitalize,
        help="Used for the robustness test: the weights are shaken by this much to see if the order changes.")
    closeness = a3.slider(
        "Closeness to home counts", 0, 30, 0, step=5, key="a_close", format="%d %%", disabled=not home,
        help="Adds a criterion for geographic and economic distance from your home country. "
             "0 % ignores distance." if home else "Choose a home country to use this.")

    st.markdown("**Hard filters.** Countries that fail a filter are removed, not just scored lower.")
    gate_cols = st.columns(len(GATES), gap="medium")
    gates = []
    for col, (gate_key, gate) in zip(gate_cols, GATES.items()):
        if gate_key not in have:
            continue
        on = col.checkbox(gate["label"], key=f"g_on_{gate_key}")
        value = col.number_input(gate["unit"], min_value=float(gate["min"]), max_value=float(gate["max"]),
                                 value=float(gate["default"]), step=float(gate["step"]),
                                 key=f"g_val_{gate_key}", disabled=not on, label_visibility="visible")
        if on:
            gates.append({"key": gate_key, "op": gate["op"], "value": value * gate["scale"]})

    st.markdown("**Weights.** Make a criterion count more or less than suggested (100 % keeps it).")
    wcols = st.columns(3)
    for i, (key, w) in enumerate(sorted(base_weights.items(), key=lambda kv: kv[1], reverse=True)):
        wcols[i % 3].slider(f"{INDICATORS[key]['label']} (suggested {w * 100:.0f} %)", 0, 200, 100,
                            step=10, format="%d %%", key=f"w_{industry}_{focus}_{key}",
                            help=INDICATORS[key]["question"])

overrides = {}
for key in base_weights:
    pct = st.session_state.get(f"w_{industry}_{focus}_{key}", 100)
    if pct != 100:
        overrides[key] = pct / 100
extra = {"dist_geo": closeness / 200, "dist_econ": closeness / 200} if home and closeness else None
weights, invert = build_weights(profile, have, overrides or None, extra)
exclude = (home,) if home else ()
year = latest_complete_year(panel, weights, exclude, method=method)

ranking = score_year(panel, year, weights, invert, exclude, method=method, gates=gates or None)
if len(ranking) < 3:
    st.warning("Fewer than three countries pass your filters. Relax a hard filter in Assumptions.")
    if not ranking.empty:
        st.dataframe(ranking[["rank", "country", "score"]], hide_index=True)
    st.stop()
dropped = ranking.attrs.get("dropped", [])
gated = ranking.attrs.get("gated", {})
evidence = top_evidence(panel, ranking, weights, invert, year, n=6)
robust = robustness(ranking, weights, sigma=UNCERTAINTY[uncertainty], method=method)
loo = leave_one_out(ranking, weights, method=method)
summary = executive_summary(ranking, robust, loo, year, method, gated, home_name)
summary_md = summary_text(summary, ranking)
conf_by_iso = robust.set_index("iso3")["confidence"].to_dict() if not robust.empty else {}

profile_lines = {
    "Industry": profile.industry_label(),
    "Focus": focuses[focus]["label"],
    "Customers": BUSINESS_MODELS[profile.business_model]["label"],
    "Budget": BUDGET_MULTIPLIERS[profile.budget]["label"],
    "Priority": PRIORITIES[profile.priority]["label"],
    "Home country (benchmark, not ranked)": home_name or "none",
    "Scoring method": "Weighted average" if method == "arithmetic" else "Balanced (weighted geometric mean)",
    "Closeness to home": f"{closeness} % of the weight" if closeness else "not used",
    "Hard filters": "; ".join(f"{GATES[g['key']]['label']} {g['value'] / GATES[g['key']]['scale']:g}"
                              for g in gates) or "none",
    "Manual weight changes": ", ".join(f"{INDICATORS[k]['label']} {v * 100:.0f} %" for k, v in overrides.items()) or "none",
}
analysis = {
    "summary": summary_md.replace("**", "").replace("\n\n", " "),
    "method": f"Scoring method: {profile_lines['Scoring method']}. Weights shaken by '{uncertainty}' uncertainty "
              "in 1,000 simulated scenarios.",
    "closeness": f"Closeness to home counts {closeness} % of the total weight." if closeness else "",
    "gates": ("Hard filters applied: " + profile_lines["Hard filters"] + f". {len(gated)} countries removed.")
    if gates else "",
}

# ------------------------------------------------------------------ tabs
t_over, t_cmp, t_rob, t_score, t_method, t_ai = st.tabs(
    ["Overview", "Compare", "Robustness", "Scorecard and export", "Method and sources", "AI advisor"])

# ================================================================ overview
with t_over:
    st.markdown(memo(summary_md), unsafe_allow_html=True)
    lead_conf = summary.get("confidence", "")
    st.markdown(kpis([
        ("Lead market", summary["leader"], f"{summary['score']:.0f} of 100 points"),
        ("Lead over #2", f"{summary['gap']:.1f}", f"points ahead of {summary['runner_up']}"),
        ("Confidence", lead_conf or "n/a",
         f"#1 in {summary.get('p_first', 0) * 100:.0f} % of scenarios" if lead_conf else ""),
        ("Countries ranked", str(len(ranking)),
         f"{len(gated)} removed by filters" if gated else f"data year {year}"),
        ("Criteria used", str(len(ranking.attrs.get('active', []))), "weights add up to 100 %"),
    ]), unsafe_allow_html=True)
    st.markdown(top_picks(evidence), unsafe_allow_html=True)

    st.subheader("Explore the world")
    st.markdown('<p class="mec-note">Drag the globe to turn it, click a country to open its analysis.</p>',
                unsafe_allow_html=True)
    if "country_pick" not in st.session_state or st.session_state["country_pick"] not in set(ranking["iso3"]):
        st.session_state["country_pick"] = ranking.iloc[0]["iso3"]
    selected = st.session_state["country_pick"]


    def make_globe(ranking: pd.DataFrame, selected: str) -> go.Figure:
        fig = go.Figure(
            go.Choropleth(
                locations=ranking["iso3"], z=ranking["score"], zmin=0, zmax=100,
                text=ranking["country"], customdata=ranking["rank"],
                colorscale=GLOBE_SCALE, marker_line_color=GLOBE_BG, marker_line_width=0.6,
                hovertemplate="<b>%{text}</b><br>Rank %{customdata}<br>Score %{z:.0f} of 100<extra></extra>",
                colorbar=dict(title=dict(text="Score", font=dict(color="#8FA3C4", size=11)),
                              orientation="h", x=0.5, xanchor="center", y=0.02, len=0.4, thickness=8,
                              tickfont=dict(color="#8FA3C4", size=10), outlinewidth=0),
            )
        )
        fig.add_trace(
            go.Choropleth(
                locations=[selected], z=[1], showscale=False, hoverinfo="skip",
                colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                marker_line_color=AMBER, marker_line_width=3,
            )
        )
        lat, lon = CENTROIDS.get(selected, (20, 10))
        fig.update_geos(
            projection_type="orthographic", projection_rotation=dict(lon=lon, lat=lat),
            projection_scale=0.92, showland=True, landcolor=GLOBE_LAND, showocean=True,
            oceancolor=GLOBE_BG, showcountries=True, countrycolor=GLOBE_LINE, showcoastlines=False,
            showframe=False, bgcolor="rgba(0,0,0,0)",
        )
        # A new uirevision (= new selected country) turns the globe to that country;
        # while it stays the same, the user's own dragging is kept.
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=560, uirevision=selected,
                          clickmode="event+select", paper_bgcolor="rgba(0,0,0,0)",
                          hoverlabel=dict(bgcolor="#fff", font_color=INK))
        return fig


    left, right = st.columns([1.5, 1], gap="medium")
    with left:
        with st.container(key="globe_panel"):
            event = st.plotly_chart(make_globe(ranking, selected), key="globe", width="stretch",
                                    on_select="rerun", selection_mode="points")
        clicked = [p.get("location") for p in (event.selection.get("points", []) if event else [])]
        clicked = [c for c in clicked if c in set(ranking["iso3"])]
        if clicked and clicked[0] != st.session_state.get("_last_click"):
            st.session_state["_last_click"] = clicked[0]
            if clicked[0] != selected:
                st.session_state["country_pick"] = clicked[0]
                st.rerun()
    with right:
        with st.container(key="panel_ranking"):
            st.markdown(f"**Ranking, data year {year}**")
            st.markdown(ranking_table(ranking, selected), unsafe_allow_html=True)
            st.caption("The percentage shows how complete the data is for that country."
                       + (f" Left out for too little data: {', '.join(dropped)}." if dropped else ""))

    st.subheader("Country analysis")
    st.selectbox("Country", list(ranking["iso3"]), key="country_pick",
                 format_func=lambda k: f"#{int(ranking.loc[ranking['iso3'] == k, 'rank'].iloc[0])}  {names[k]}")
    selected = st.session_state["country_pick"]
    ev = evidence_for(panel, ranking, selected, weights, invert, year)
    if selected in conf_by_iso:
        st.markdown(f"Confidence for this country: {badge(conf_by_iso[selected])}", unsafe_allow_html=True)

    a, b = st.columns([1, 1])
    with a:
        st.markdown(country_paragraph(ev))
    with b:
        tab_pts, tab_hist = st.tabs(["Points per criterion", "Score over time"])
        with tab_pts:
            pts = pd.DataFrame({"Criterion": [i["label"] for i in ev["indicators"]],
                                "Points": [i["points"] for i in ev["indicators"]],
                                "Pillar": [i["pillar"] for i in ev["indicators"]]})
            bar = px.bar(pts, x="Points", y="Criterion", orientation="h", range_x=(0, 100), color="Pillar",
                         color_discrete_sequence=[BLUE, "#6B8CCE", "#9AA7BD", AMBER])
            bar.update_layout(bargap=0.5, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                              font=dict(color=INK, size=12), height=420, margin=dict(l=0, r=0, t=10, b=0),
                              yaxis_title=None, yaxis=dict(autorange="reversed"),
                              legend=dict(orientation="h", y=-0.12, title=None))
            bar.update_xaxes(gridcolor=LINE, title=None)
            st.plotly_chart(bar, width="stretch")
        with tab_hist:
            history = score_history(panel, weights, invert, exclude, method=method)
            mine = history[history["iso3"] == selected]
            line = px.line(mine, x="year", y="score", markers=True, range_y=(0, 100))
            line.update_traces(line_color=BLUE)
            line.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                               font=dict(color=INK, size=12), height=420, margin=dict(l=0, r=0, t=10, b=0),
                               xaxis_title=None)
            line.update_yaxes(gridcolor=LINE)
            st.plotly_chart(line, width="stretch")
            st.caption("Scores are relative: a country is compared with the other countries for the same year.")

    rows = [{
        "Criterion": i["label"], "Pillar": i["pillar"], "What it tells you": INDICATORS[i["key"]]["question"],
        "Value": i["value_text"], "Score (0-100)": i["points"], "Weight": f"{i['weight'] * 100:.1f} %",
        "Change in 5 years": i["trend"]["text"] if i["trend"] else "no data",
    } for i in ev["indicators"]]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={"Score (0-100)": st.column_config.ProgressColumn(
                     "Score (0-100)", min_value=0, max_value=100, format="%.0f")})

# ================================================================ compare
with t_cmp:
    st.markdown("Put two to four markets side by side. Your home country is shown as a benchmark.")
    by_iso = ranking.set_index("iso3")
    pick = st.multiselect("Markets to compare", list(ranking["iso3"]), default=list(ranking["iso3"][:3]),
                          max_selections=4, format_func=lambda k: f"#{int(by_iso.loc[k, 'rank'])}  {names[k]}",
                          key="cmp_pick")
    benchmark = ranking.attrs.get("excluded", [])
    bench = benchmark[0] if benchmark else None
    if len(pick) < 2:
        st.info("Choose at least two markets.")
    else:
        rows_c = [by_iso.loc[k].to_dict() | {"iso3": k} for k in pick]
        if bench:
            rows_c.append(bench | {"country": f"{bench['country']} (home, benchmark)"})
        pillar_keys = [p for p in PILLARS if f"p_{p}" in ranking]
        pal = [BLUE, "#0F7B63", AMBER, "#8A5CF6", "#6B7A90"]
        radar = go.Figure()
        for i, r in enumerate(rows_c):
            vals = [r.get(f"p_{p}") for p in pillar_keys]
            if any(pd.isna(v) for v in vals):
                continue
            radar.add_trace(go.Scatterpolar(
                r=vals + vals[:1], theta=[PILLARS[p] for p in pillar_keys] + [PILLARS[pillar_keys[0]]],
                name=r["country"], line=dict(color=pal[i % len(pal)], width=2,
                                             dash="dot" if bench and r is rows_c[-1] else "solid"),
                fill="toself", opacity=0.35 if not (bench and r is rows_c[-1]) else 0.1))
        radar.update_layout(polar=dict(radialaxis=dict(range=[0, 100], gridcolor=LINE)), height=430,
                            margin=dict(l=40, r=40, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(color=INK, size=12), legend=dict(orientation="h", y=-0.1))
        c1, c2 = st.columns([1, 1.5], gap="medium")
        c1.plotly_chart(radar, width="stretch")
        crit = [k for k, _ in sorted(weights.items(), key=lambda kv: kv[1], reverse=True)
                if f"pts_{k}" in ranking][:12]
        table = pd.DataFrame({"Criterion": [INDICATORS[k]["label"] for k in crit],
                              "Weight": [f"{weights[k] * 100:.1f} %" for k in crit]})
        for r in rows_c:
            table[r["country"]] = [
                "n/a" if pd.isna(r.get(k)) else f"{fmt_value(k, r[k])}  ({r[f'pts_{k}']:.0f})" for k in crit]
        c2.dataframe(table, hide_index=True, width="stretch", height=430)
        st.caption("Each cell shows the value and, in brackets, the points from 0 to 100. "
                   "The three pillars average the points of their criteria with your weights.")
        gap_rows = []
        for k in pick:
            ev_k = evidence_for(panel, ranking, k, weights, invert, year)
            gap_rows.append({"Market": ev_k["country"], "Rank": ev_k["rank"], "Score": ev_k["score"],
                             "Confidence": conf_by_iso.get(k, ""),
                             "Strongest": "; ".join(s["label"] for s in ev_k["strengths"][:2]) or "none above 60",
                             "Biggest risk": "; ".join(r["label"] for r in ev_k["risks"][:2]) or "none below 40"})
        st.dataframe(pd.DataFrame(gap_rows), hide_index=True, width="stretch")

# ============================================================== robustness
with t_rob:
    st.markdown(
        "A ranking is only useful if you know how far to trust it. Here the weights are shaken "
        f"1,000 times (uncertainty: **{uncertainty}**) and we count how often each market keeps its place.")
    if robust.empty:
        st.info("Not enough data for the robustness test.")
    else:
        top_n = robust.head(15)
        rng = go.Figure()
        rng.add_trace(go.Scatter(
            x=top_n["rank_worst"], y=top_n["country"], mode="markers", name="Worst typical rank (90 %)",
            marker=dict(color=AMBER, size=9)))
        rng.add_trace(go.Scatter(
            x=top_n["rank_best"], y=top_n["country"], mode="markers", name="Best typical rank (10 %)",
            marker=dict(color=BLUE, size=9)))
        for _, r in top_n.iterrows():
            rng.add_shape(type="line", x0=r["rank_best"], x1=r["rank_worst"], y0=r["country"], y1=r["country"],
                          line=dict(color="#B7C3D8", width=3), layer="below")
        rng.add_trace(go.Scatter(x=top_n["rank"], y=top_n["country"], mode="markers", name="Rank now",
                                 marker=dict(color=INK, size=7, symbol="diamond")))
        rng.update_layout(height=520, margin=dict(l=0, r=10, t=10, b=0), plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", font=dict(color=INK, size=12),
                          yaxis=dict(autorange="reversed", title=None), xaxis=dict(title="Rank", gridcolor=LINE, dtick=2),
                          legend=dict(orientation="h", y=-0.12))
        rb1, rb2 = st.columns([1.4, 1], gap="medium")
        rb1.markdown("**How far each market's rank moves** (line = range in 80 % of scenarios)")
        rb1.plotly_chart(rng, width="stretch")
        show = robust.head(10)[["rank", "country", "p_first", "p_top3", "confidence"]].rename(columns={
            "rank": "Rank", "country": "Market", "p_first": "Ranked #1", "p_top3": "In top 3",
            "confidence": "Confidence"})
        rb2.markdown("**How often it comes out on top**")
        rb2.dataframe(show, hide_index=True, width="stretch", height=420, column_config={
            "Ranked #1": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent"),
            "In top 3": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent")})
        rb2.caption("Confidence is High when the data is nearly complete and the rank moves by at most "
                    "4 places, Medium up to 8 places, otherwise Low.")

        st.subheader("Which criterion decides the leader?")
        st.markdown("Each row ignores one criterion and shows who would lead instead.")
        loo_view = loo.copy()
        loo_view["Weight"] = (loo_view["Weight"] * 100).round(1).astype(str) + " %"
        st.dataframe(loo_view, hide_index=True, width="stretch")
        if gated:
            st.subheader("Removed by your hard filters")
            st.dataframe(pd.DataFrame([{"Country": c, "Reason": "; ".join(r)} for c, r in gated.items()]),
                         hide_index=True, width="stretch")

# ============================================================== scorecard
with t_score:
    frames = scorecard_frames(ranking, weights)
    st.markdown("Every number behind the ranking. Sort any column, or download the full workbook.")
    sc = frames["ranking"].copy()
    sc.insert(3, "Confidence", [conf_by_iso.get(i, "") for i in ranking["iso3"]])
    st.dataframe(sc, hide_index=True, width="stretch", column_config={
        "Score (0-100)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
        "Data coverage": st.column_config.NumberColumn(format="percent"),
        **{label: st.column_config.NumberColumn(format="%.0f") for label in PILLARS.values()}})

    st.subheader("Heat map: points per criterion")
    n_show = st.slider("Markets shown", 5, min(25, len(ranking)), min(12, len(ranking)), key="heat_n")
    crit_all = [k for k, _ in sorted(weights.items(), key=lambda kv: kv[1], reverse=True) if f"pts_{k}" in ranking]
    sub = ranking.head(n_show)
    z = sub[[f"pts_{k}" for k in crit_all]].to_numpy(dtype=float)
    heat = go.Figure(go.Heatmap(
        z=z, x=[INDICATORS[k]["label"] for k in crit_all], y=sub["country"],
        colorscale=[[0, "#F6E1DE"], [0.5, "#F5F7FA"], [1, "#2F6FED"]], zmin=0, zmax=100,
        text=[[f"{v:.0f}" if pd.notna(v) else "n/a" for v in row] for row in z], texttemplate="%{text}",
        hovertemplate="%{y}<br>%{x}: %{z:.0f} points<extra></extra>", showscale=False))
    heat.update_layout(height=max(320, 30 * n_show + 160), margin=dict(l=0, r=0, t=10, b=0),
                       yaxis=dict(autorange="reversed"), xaxis=dict(side="top", tickangle=-40),
                       paper_bgcolor="rgba(0,0,0,0)", font=dict(color=INK, size=11))
    st.plotly_chart(heat, width="stretch")
    st.caption("Blue = strong, red = weak, compared with all 42 countries. Columns are ordered by weight.")

    st.subheader("Download and share")
    ai_cached = st.session_state.get("ai_cache", {})
    d1, d2, d3, d4 = st.columns(4)
    d1.download_button(
        "Excel workbook", data=to_excel(ranking, weights, profile_lines, robust, loo, gated, year, retrieved),
        file_name="market-entry-screening.xlsx", width="stretch",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    d2.download_button(
        "One-page brief (.md)", width="stretch", file_name="market-entry-brief.md", mime="text/markdown",
        data=brief_markdown(profile_lines, summary_md, ranking, evidence, year, retrieved,
                            next(iter(ai_cached.values()), "")))
    d3.download_button("Ranking (.csv)", data=sc.to_csv(index=False), file_name="ranking.csv",
                       mime="text/csv", width="stretch")
    d4.download_button(
        "Scenario (.json)", width="stretch", file_name="scenario.json", mime="application/json",
        data=scenario_to_json(ans, {"method": method, "closeness": closeness, "overrides": {
            k: round(v * 100) for k, v in overrides.items()},
            "gates": {g["key"]: g["value"] for g in gates}}))
    st.caption("The scenario file stores all your assumptions. Upload it later to get exactly this view back. "
               "The page address also holds your answers, so you can share it as a link.")
    upload = st.file_uploader("Load a saved scenario", type="json", key="scenario_upload")
    if upload is not None:
        loaded = scenario_from_json(upload.getvalue().decode("utf-8", errors="replace"))
        if loaded is None:
            st.error("This file is not a valid scenario.")
        elif st.button("Apply scenario", type="primary"):
            ss["pending_scenario"] = loaded
            st.rerun()

# ================================================================= method
with t_method:
    m1, m2 = st.columns([1, 1], gap="large")
    with m1:
        st.subheader("How the score works")
        st.markdown(
            f"""
1. **Data.** World Bank open data: World Development Indicators, Worldwide Governance
   Indicators and Global Findex, reference year **{year}**. Missing years are filled with the last
   known value (survey data up to 6 years).
2. **Points.** Each criterion is scaled to 0 to 100 across all {META.get('countries', 42)} countries
   (outliers capped at the 5th and 95th percentile). Inflation and distance are scored by closeness
   to a target or by "lower is better".
3. **Weights.** Industry focus, customers, budget and priority set the weights. A block of
   institutional criteria (political stability, regulation, corruption, government effectiveness,
   external balance, investment, openness) is added for every startup, with more weight if you prefer safety.
4. **Pillars.** Criteria are grouped into market opportunity, operating environment, and
   stability and institutions, so you can see trade-offs.
5. **Combine.** Weighted average, or the balanced method (weighted geometric mean) in which a very
   weak criterion pulls the total down.
6. **Missing data.** A country is scored on the criteria it has (weights renormalised). Countries with
   less than 70 % of the weight covered are left out.
7. **Robustness.** 1,000 random weight scenarios (seeded, so repeatable) show how stable the order is.
8. **Home country.** Scored with the others as a benchmark but not ranked.
"""
        )
    with m2:
        st.subheader("Limits")
        st.markdown(DISCLAIMER)
        st.markdown(
            "- Rich, small, stable countries tend to score high: they do well on most governance and "
            "infrastructure criteria. Use the growth priority, the balanced method and the hard filters to test this.\n"
            "- Only two of the four classic distances (geographic, economic) can be measured with open data. "
            "Cultural and administrative distance are not in the score.\n"
            "- The data is national and annual; it can be one to two years old."
        )
    st.subheader("Weights and sources for your profile")
    wt = sources_table(weights, retrieved)
    wt.insert(1, "Pillar", [PILLARS[pillar_of(k)] for k in sorted(weights, key=lambda k: weights[k], reverse=True)])
    wt.insert(2, "Weight", [f"{weights[k] * 100:.1f} %" for k in sorted(weights, key=lambda k: weights[k], reverse=True)])
    st.dataframe(wt, hide_index=True, width="stretch")

# ===================================================================== AI
with t_ai:
    st.markdown(briefing(profile, evidence, weights, year, dropped).replace("\n# ", "\n### ").replace(
        "\n## ", "\n### ").removeprefix("# ").removeprefix("## "))
    with st.container(key="panel_advice"):
        k1, k2 = st.columns([2, 1])
        api_key = k1.text_input(
            "Your Anthropic API key (for the AI analysis)", type="password", placeholder="sk-ant-...",
            help="Kept only in this browser session. Not saved or logged by this app. "
                 "Get a key at console.anthropic.com.")
        language = k2.selectbox("Language of the AI advice", ["English", "Deutsch"])
    signature = hashlib.sha256(
        repr((profile, year, sorted(weights.items()), language, method, tuple(map(str, gates)))).encode()).hexdigest()
    cache = st.session_state.setdefault("ai_cache", {})
    st.subheader("AI analysis")
    st.caption("Claude reads your profile, the data and the robustness results and writes a memo. "
               "It may only use these numbers. Verify important facts yourself.")
    if st.button("Generate AI analysis", type="primary", disabled=not api_key):
        try:
            with st.spinner("Analysing your markets ..."):
                text = st.write_stream(stream_advice(api_key, profile, evidence, weights, year, language, analysis))
            cache[signature] = text
        except AdvisorError as error:
            st.error(str(error))
    elif signature in cache:
        st.markdown(cache[signature])
    if not api_key:
        st.caption("Enter your Anthropic API key to enable the AI analysis. The briefing above works without it.")

st.markdown(f'<div class="mec-disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
