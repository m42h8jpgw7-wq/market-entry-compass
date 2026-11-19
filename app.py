"""Market Entry Compass - find the best first foreign market for your startup.

Start with:  streamlit run app.py
"""

import hashlib
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.advisor import AdvisorError, stream_advice
from src.config import (
    BUDGET_MULTIPLIERS, BUSINESS_MODELS, DATA_FILE, INDICATORS, INDUSTRIES, PRIORITIES, STAGES,
)
from src.evidence import briefing, country_paragraph, evidence_for, top_evidence
from src.geo import CENTROIDS
from src.profile import StartupProfile, build_weights
from src.scoring import (
    available_indicators, build_panel, latest_complete_year, score_history, score_year,
)

from src.ui import (
    AMBER, BLUE, GLOBE_BG, GLOBE_LAND, GLOBE_LINE, GLOBE_SCALE, INK, MUTED, CSS, hero,
    ranking_table, top_picks,
)

st.set_page_config(page_title="Market Entry Compass", page_icon="🧭", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data
def load_panel() -> pd.DataFrame:
    return build_panel(pd.read_csv(DATA_FILE))


def country_names(panel: pd.DataFrame) -> dict:
    return panel.drop_duplicates("iso3").set_index("iso3")["country"].to_dict()


# ------------------------------------------------------------------- header
st.markdown(hero(), unsafe_allow_html=True)

if not Path(DATA_FILE).exists():
    st.error("No data found yet. Run this in the terminal first:  python -m src.fetch_data")
    st.stop()

panel = load_panel()
names = country_names(panel)
have = available_indicators(panel)

# ----------------------------------------------------------- your startup
st.header("Your startup")
with st.container(key="panel_profile"):
    c1, c2, c3 = st.columns(3)
    industry = c1.selectbox("Industry", list(INDUSTRIES), format_func=lambda k: INDUSTRIES[k]["label"])
    focuses = INDUSTRIES[industry]["focuses"]
    focus = c2.selectbox("What exactly do you do?", list(focuses),
                         format_func=lambda k: focuses[k]["label"])
    business_model = c3.selectbox("Who are your customers?", list(BUSINESS_MODELS),
                                  format_func=lambda k: BUSINESS_MODELS[k]["label"])
    industry_name = ""
    if industry == "other":
        industry_name = st.text_input("Name your industry",
                                      placeholder="e.g. Agriculture technology, legal services, gaming")

    c4, c5, c6, c7 = st.columns(4)
    stage = c4.selectbox("Stage", STAGES, index=1)
    budget = c5.selectbox("Budget for expansion", list(BUDGET_MULTIPLIERS),
                          format_func=lambda k: BUDGET_MULTIPLIERS[k]["label"])
    priority = c6.selectbox("What matters more?", list(PRIORITIES),
                            format_func=lambda k: PRIORITIES[k]["label"])
    home_options = ["(none)"] + sorted(names, key=names.get)
    home = c7.selectbox("Home country (left out)", home_options,
                        index=home_options.index("DEU") if "DEU" in names else 0,
                        format_func=lambda k: k if k == "(none)" else names[k])

    description = st.text_area(
        "Describe your startup in your own words",
        placeholder="e.g. We build invoice financing for small online shops. Customers connect "
                    "their shop and we advance payouts within 24 hours.",
        help="What do you sell, to whom, and what makes expansion hard? The AI adviser reads this.",
    )
    notes = st.text_input(
        "Constraints or wishes (optional)",
        placeholder="e.g. team speaks English, German and Greek; no licence budget this year",
    )

profile = StartupProfile(
    industry=industry, focus=focus, business_model=business_model, priority=priority,
    budget=budget, stage=stage, description=description,
    home_country="" if home == "(none)" else home, extra_notes=notes, industry_name=industry_name,
)
st.markdown(f'<div class="mec-hint"><b>{focuses[focus]["label"]}.</b> {focuses[focus]["text"]}</div>',
            unsafe_allow_html=True)

base_weights, _ = build_weights(profile, have)
with st.expander("Fine-tune the criteria (optional)"):
    st.caption("Make a criterion more or less important than the default for your profile. "
               "100 % keeps it as is, 0 % removes it.")
    overrides = {}
    cols = st.columns(3)
    for i, (key, w) in enumerate(sorted(base_weights.items(), key=lambda kv: kv[1], reverse=True)):
        pct = cols[i % 3].slider(f"{INDICATORS[key]['label']} (default {w * 100:.0f} % weight)",
                                 0, 200, 100, step=10, format="%d %%", key=f"w_{industry}_{focus}_{key}")
        if pct != 100:
            overrides[key] = pct / 100

weights, invert = build_weights(profile, have, overrides or None)
exclude = (profile.home_country,) if profile.home_country else ()
year = latest_complete_year(panel, weights, exclude)

ranking = score_year(panel, year, weights, invert, exclude)
if ranking.empty:
    st.warning(f"Not enough data for {year}. Pick another year.")
    st.stop()
dropped = ranking.attrs.get("dropped", [])
evidence = top_evidence(panel, ranking, weights, invert, year, n=6)

# ---------------------------------------------------------- recommendation
st.header("Where to go first")
st.markdown(top_picks(evidence), unsafe_allow_html=True)

# ----------------------------------------------------------------- globe
st.header("Explore the world")
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
        st.caption("The last column shows how much of the criteria weight has data for that country."
                   + (f" Left out for too little data: {', '.join(dropped)}." if dropped else ""))

# ------------------------------------------------------------ 4. deep dive
st.header("Country analysis")
st.selectbox("Country", list(ranking["iso3"]), key="country_pick",
             format_func=lambda k: f"#{int(ranking.loc[ranking['iso3'] == k, 'rank'].iloc[0])}  {names[k]}")
selected = st.session_state["country_pick"]
ev = evidence_for(panel, ranking, selected, weights, invert, year)

a, b = st.columns([1, 1])
with a:
    st.markdown(country_paragraph(ev))

with b:
    tab_pts, tab_hist = st.tabs(["Points per criterion", "Score over time"])
    with tab_pts:
        pts = pd.DataFrame({"Criterion": [i["label"] for i in ev["indicators"]],
                            "Points": [i["points"] for i in ev["indicators"]]})
        bar = px.bar(pts, x="Points", y="Criterion", orientation="h", range_x=(0, 100))
        bar.update_layout(bargap=0.55, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          font=dict(color=INK, size=12))
        bar.update_xaxes(gridcolor="#E1E5EC", title=None)
        bar.update_traces(marker_color=BLUE)
        bar.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), yaxis_title=None,
                          yaxis=dict(autorange="reversed"))
        st.plotly_chart(bar, width="stretch")
    with tab_hist:
        history = score_history(panel, weights, invert, exclude)
        mine = history[history["iso3"] == selected]
        line = px.line(mine, x="year", y="score", markers=True, range_y=(0, 100))
        line.update_traces(line_color=BLUE)
        line.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           font=dict(color=INK, size=12), height=380, margin=dict(l=0, r=0, t=10, b=0), xaxis_title=None)
        st.plotly_chart(line, width="stretch")
        st.caption("Scores are relative: a country is compared with the other countries "
                   "for the same year.")

# --------------------------------------------------------- 5. advice
rows = []
for item in ev["indicators"]:
    rows.append({
        "Criterion": item["label"], "Value": item["value_text"],
        "Points": item["points"], "Weight": f"{item['weight'] * 100:.0f} %",
        "Trend": item["trend"]["text"] if item["trend"] else "n/a",
    })
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
             column_config={"Points": st.column_config.ProgressColumn(
                 "Points", min_value=0, max_value=100, format="%.0f")})

st.header("Advice")
st.markdown(briefing(profile, evidence, weights, year, dropped).replace("\n# ", "\n### ").replace("\n## ", "\n### ").removeprefix("# ").removeprefix("## "))

with st.container(key="panel_advice"):
    k1, k2 = st.columns([2, 1])
    api_key = k1.text_input(
        "Your Anthropic API key (for the AI analysis)", type="password", placeholder="sk-ant-...",
        help="Kept only in this browser session. Not saved or logged by this app. "
             "Get a key at console.anthropic.com.",
    )
    language = k2.selectbox("Language of the AI advice", ["English", "Deutsch"])

signature = hashlib.sha256(
    repr((profile, year, sorted(weights.items()), language)).encode()
).hexdigest()
cache = st.session_state.setdefault("ai_cache", {})

st.subheader("AI analysis")
st.caption(
    "Claude reads your profile and the data above and writes a detailed recommendation. "
    "It may only use these numbers. Verify important facts yourself."
)
if st.button("Generate AI analysis", type="primary", disabled=not api_key):
    try:
        with st.spinner("Analysing your markets ..."):
            text = st.write_stream(stream_advice(api_key, profile, evidence, weights, year, language))
        cache[signature] = text
    except AdvisorError as error:
        st.error(str(error))
elif signature in cache:
    st.markdown(cache[signature])
if not api_key:
    st.caption("Enter your Anthropic API key above to enable the AI analysis. "
               "The data briefing above works without it.")

# ------------------------------------------------------------- method
with st.expander("Method, data and limits"):
    rows = [{"Criterion": INDICATORS[k]["label"], "What it measures": INDICATORS[k]["unit"],
             "Weight for your profile": f"{w * 100:.0f} %"}
            for k, w in sorted(weights.items(), key=lambda kv: kv[1], reverse=True)]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.markdown(
        """
        - **Data:** World Bank open data (World Development Indicators, Worldwide Governance
          Indicators, Global Findex). Missing years are filled with the last known value
          (survey data for up to 6 years).
        - **Score:** every criterion is scaled to 0-100 across all countries (outliers capped
          at the 5th/95th percentile), then combined with weights that depend on your
          industry focus, customers, budget and priority.
        - **Inflation** is scored by distance from 2 %. If a country lacks a criterion, the
          score uses the remaining criteria (weights renormalised); countries with less than
          70 % of the weight covered are left out.
        - **Limits:** national averages hide regional differences. The tool cannot see
          competitors, taxes, licences, language, culture or your product. It is a first
          screening, not a forecast and not legal or financial advice.
        """
    )
