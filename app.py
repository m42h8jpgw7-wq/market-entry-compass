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

NAVY, ORANGE, GREY = "#1B2A41", "#E07A1F", "#6B7280"

st.set_page_config(page_title="Market Entry Compass", page_icon="🧭", layout="wide")
st.markdown(
    f"""
    <style>
      .block-container {{ padding-top: 2rem; max-width: 1280px; }}
      h1, h2, h3 {{ color: {NAVY}; font-weight: 600; letter-spacing: -0.01em; }}
      .subtitle {{ color: {GREY}; font-size: 1.05rem; margin-top: -0.7rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_panel() -> pd.DataFrame:
    return build_panel(pd.read_csv(DATA_FILE))


def country_names(panel: pd.DataFrame) -> dict:
    return panel.drop_duplicates("iso3").set_index("iso3")["country"].to_dict()


# ------------------------------------------------------------------- header
st.title("Market Entry Compass")
st.markdown(
    '<p class="subtitle">Which country should your startup enter first? '
    "Tell us about your startup. We rank 42 countries with public World Bank data "
    "and explain the result.</p>",
    unsafe_allow_html=True,
)

if not Path(DATA_FILE).exists():
    st.error("No data found yet. Run this in the terminal first:  python -m src.fetch_data")
    st.stop()

panel = load_panel()
names = country_names(panel)
have = available_indicators(panel)

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("AI advisor (optional)")
    api_key = st.text_input(
        "Your Anthropic API key", type="password", placeholder="sk-ant-...",
        help="Needed only for the AI analysis. Get one at console.anthropic.com.",
    )
    language = st.selectbox("Language of the AI advice", ["English", "Deutsch"])
    st.caption(
        "The key stays in this session's memory only and is not saved or logged by this app. "
        "You can also run the app on your own computer."
    )
    st.divider()
    with st.expander("Advanced"):
        pick_year = st.checkbox("Choose the reference year myself")

# ----------------------------------------------------------- 1. your startup
st.subheader("1. Your startup")
c1, c2, c3 = st.columns(3)
industry = c1.selectbox("Industry", list(INDUSTRIES), format_func=lambda k: INDUSTRIES[k]["label"])
focuses = INDUSTRIES[industry]["focuses"]
focus = c2.selectbox("What exactly do you do?", list(focuses), format_func=lambda k: focuses[k]["label"])
business_model = c3.selectbox("Who are your customers?", list(BUSINESS_MODELS),
                              format_func=lambda k: BUSINESS_MODELS[k]["label"])

c4, c5, c6, c7 = st.columns(4)
stage = c4.selectbox("Stage", STAGES, index=1)
budget = c5.selectbox("Budget for expansion", list(BUDGET_MULTIPLIERS),
                      format_func=lambda k: BUDGET_MULTIPLIERS[k]["label"])
priority = c6.selectbox("What matters more?", list(PRIORITIES),
                        format_func=lambda k: PRIORITIES[k]["label"])
home = c7.selectbox("Home country (left out of the ranking)", ["(none)"] + sorted(names, key=names.get),
                    index=(["(none)"] + sorted(names, key=names.get)).index("DEU")
                    if "DEU" in names else 0,
                    format_func=lambda k: k if k == "(none)" else names[k])

description = st.text_area(
    "Describe your startup in your own words",
    placeholder="e.g. We build invoice financing for small online shops. Customers connect "
                "their shop, we advance payouts within 24 hours ...",
    help="What do you sell, to whom, what makes it hard to expand? The AI advisor reads this.",
)
notes = st.text_input(
    "Constraints or wishes (optional)",
    placeholder="e.g. team speaks English, German and Greek; no licence budget this year",
)

profile = StartupProfile(
    industry=industry, focus=focus, business_model=business_model, priority=priority,
    budget=budget, stage=stage, description=description,
    home_country="" if home == "(none)" else home, extra_notes=notes,
)
st.info(f"**{focuses[focus]['label']}.** {focuses[focus]['text']}")

weights, invert = build_weights(profile, have)
exclude = (profile.home_country,) if profile.home_country else ()
default_year = latest_complete_year(panel, weights, exclude)
year = default_year
if pick_year:
    years = [y for y in sorted(panel["year"].unique()) if y <= default_year]
    year = st.sidebar.select_slider("Reference year", options=years, value=default_year)

ranking = score_year(panel, year, weights, invert, exclude)
if ranking.empty:
    st.warning(f"Not enough data for {year}. Pick another year.")
    st.stop()
dropped = ranking.attrs.get("dropped", [])
evidence = top_evidence(panel, ranking, weights, invert, year, n=6)

# ---------------------------------------------------------- 2. recommendation
st.subheader("2. Where to go first")
cols = st.columns(3)
for col, ev in zip(cols, evidence[:3]):
    with col.container(border=True):
        st.markdown(f"##### #{ev['rank']} {ev['country']}")
        st.markdown(f"**{ev['score']:.0f}** / 100 points")
        for item in ev["strengths"][:2]:
            st.caption(f"**Strong:** {item['label']}, {item['value_text']}")
        for item in ev["risks"][:1]:
            st.caption(f"**Risk:** {item['label']}, {item['value_text']}")

# ----------------------------------------------------------------- 3. globe
st.subheader("3. Explore the world")
st.caption("Drag the globe to turn it. Click a country to open its analysis.")

if "country_pick" not in st.session_state or st.session_state["country_pick"] not in set(ranking["iso3"]):
    st.session_state["country_pick"] = ranking.iloc[0]["iso3"]
selected = st.session_state["country_pick"]


def make_globe(ranking: pd.DataFrame, selected: str) -> go.Figure:
    fig = go.Figure(
        go.Choropleth(
            locations=ranking["iso3"], z=ranking["score"], zmin=0, zmax=100,
            text=ranking["country"], customdata=ranking["rank"],
            colorscale=[[0, "#E3E8F0"], [0.5, "#7F95B8"], [1, NAVY]],
            marker_line_color="#FFFFFF", marker_line_width=0.6,
            hovertemplate="<b>%{text}</b><br>Rank #%{customdata}<br>Score %{z:.0f}/100<extra></extra>",
            colorbar=dict(title="Score", orientation="h", x=0.5, xanchor="center", y=-0.02,
                          len=0.5, thickness=10),
        )
    )
    # Orange outline around the selected country
    fig.add_trace(
        go.Choropleth(
            locations=[selected], z=[1], showscale=False, hoverinfo="skip",
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            marker_line_color=ORANGE, marker_line_width=3,
        )
    )
    lat, lon = CENTROIDS.get(selected, (20, 10))
    fig.update_geos(
        projection_type="orthographic", projection_rotation=dict(lon=lon, lat=lat),
        projection_scale=0.92, showland=True, landcolor="#EEF1F6", showocean=True,
        oceancolor="#FAFBFD", showcountries=True, countrycolor="#FFFFFF", showcoastlines=False,
        showframe=True, framecolor="#D5DBE6", framewidth=1, bgcolor="rgba(0,0,0,0)",
    )
    # A new uirevision (= new selected country) turns the globe to that country;
    # while it stays the same, the user's own dragging is kept.
    fig.update_layout(margin=dict(l=10, r=10, t=0, b=30), height=580, uirevision=selected,
                      clickmode="event+select")
    return fig


left, right = st.columns([1.5, 1])
with left:
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
    st.markdown(f"**Ranking {year}**")
    table = ranking[["rank", "country", "score", "coverage"]].rename(
        columns={"rank": "#", "country": "Country", "score": "Score", "coverage": "Data"})
    table["Data"] = (table["Data"] * 100).round(0).astype(int).astype(str) + " %"
    st.dataframe(
        table, hide_index=True, width="stretch", height=520,
        column_config={"Score": st.column_config.ProgressColumn(
            "Score", min_value=0, max_value=100, format="%.0f")},
    )
    st.caption("'Data' = share of the criteria weights with data for that country. "
               + (f"Left out (too little data): {', '.join(dropped)}." if dropped else ""))

# ------------------------------------------------------------ 4. deep dive
st.subheader("4. Country analysis")
st.selectbox("Country", list(ranking["iso3"]), key="country_pick",
             format_func=lambda k: f"#{int(ranking.loc[ranking['iso3'] == k, 'rank'].iloc[0])}  {names[k]}")
selected = st.session_state["country_pick"]
ev = evidence_for(panel, ranking, selected, weights, invert, year)

a, b = st.columns([1, 1])
with a:
    st.markdown(country_paragraph(ev))
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

with b:
    tab_pts, tab_hist = st.tabs(["Points per criterion", "Score over time"])
    with tab_pts:
        pts = pd.DataFrame({"Criterion": [i["label"] for i in ev["indicators"]],
                            "Points": [i["points"] for i in ev["indicators"]]})
        bar = px.bar(pts, x="Points", y="Criterion", orientation="h", range_x=(0, 100))
        bar.update_traces(marker_color=NAVY)
        bar.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), yaxis_title=None,
                          yaxis=dict(autorange="reversed"))
        st.plotly_chart(bar, width="stretch")
    with tab_hist:
        history = score_history(panel, weights, invert, exclude)
        mine = history[history["iso3"] == selected]
        line = px.line(mine, x="year", y="score", markers=True, range_y=(0, 100))
        line.update_traces(line_color=NAVY)
        line.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), xaxis_title=None)
        st.plotly_chart(line, width="stretch")
        st.caption("Scores are relative: a country is compared with the other countries "
                   "for the same year.")

# --------------------------------------------------------- 5. advice
st.subheader("5. Advice")
st.markdown(briefing(profile, evidence, weights, year, dropped))

signature = hashlib.sha256(
    repr((profile, year, sorted(weights.items()), language)).encode()
).hexdigest()
cache = st.session_state.setdefault("ai_cache", {})

st.markdown("#### AI analysis")
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
    st.caption("Enter your Anthropic API key in the sidebar to enable the AI analysis. "
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
