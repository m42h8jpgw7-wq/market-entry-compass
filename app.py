"""Market Entry Compass - dashboard for founders choosing their first foreign market.

Start with:  streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import DATA_FILE, DEFAULT_WEIGHTS, INDICATORS
from src.scoring import build_panel, explain, latest_complete_year, score_history, score_year

NAVY = "#1B2A41"
GREY = "#6B7280"

st.set_page_config(page_title="Market Entry Compass", page_icon="🧭", layout="wide")

st.markdown(
    f"""
    <style>
      .block-container {{ padding-top: 2rem; max-width: 1200px; }}
      h1, h2, h3 {{ color: {NAVY}; font-weight: 600; }}
      .subtitle {{ color: {GREY}; font-size: 1.05rem; margin-top: -0.6rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_panel() -> pd.DataFrame:
    return build_panel(pd.read_csv(DATA_FILE))


st.title("Market Entry Compass")
st.markdown(
    '<p class="subtitle">Which country should your startup enter first? '
    "A transparent, data-driven ranking based on public World Bank data.</p>",
    unsafe_allow_html=True,
)

if not Path(DATA_FILE).exists():
    st.error("No data found yet. Run this in the terminal first:  python -m src.fetch_data")
    st.stop()

panel = load_panel()
default_year = latest_complete_year(panel)
years = sorted(panel["year"].unique())

# ----------------------------- Sidebar -----------------------------------
st.sidebar.header("Settings")
year = st.sidebar.select_slider("Reference year", options=years, value=default_year)

st.sidebar.subheader("How important is each criterion?")
weights = {}
for key, spec in INDICATORS.items():
    weights[key] = st.sidebar.slider(
        spec["label"].split(" (")[0],
        0, 10, int(DEFAULT_WEIGHTS[key] * 20),
        help=spec["question"],
    )
if sum(weights.values()) == 0:
    st.sidebar.warning("Set at least one weight above 0.")
    st.stop()

ranking = score_year(panel, year, weights)
if ranking.empty:
    st.warning(f"Not enough data for {year}. Pick another year.")
    st.stop()

# ----------------------------- Ranking + map ------------------------------
left, right = st.columns([1, 1.4])

with left:
    st.subheader(f"Ranking {year}")
    table = ranking[["rank", "country", "score"]].rename(
        columns={"rank": "#", "country": "Country", "score": "Score"}
    )
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        height=520,
        column_config={"Score": st.column_config.ProgressColumn(
            "Score", min_value=0, max_value=100, format="%.0f")},
    )

with right:
    st.subheader("World map")
    fig = px.choropleth(
        ranking, locations="iso3", color="score", hover_name="country",
        range_color=(0, 100), color_continuous_scale=["#E5EAF1", NAVY],
        labels={"score": "Score"},
    )
    fig.update_geos(showframe=False, showcoastlines=False, projection_type="natural earth")
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=520,
                      coloraxis_colorbar=dict(title="Score"))
    st.plotly_chart(fig, width="stretch")

# ----------------------------- Country detail -----------------------------
st.divider()
st.subheader("Country analysis")
country = st.selectbox("Choose a country", ranking["country"].tolist())
row = ranking[ranking["country"] == country].iloc[0]

st.info(explain(row, weights))

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("**Points per criterion (0-100)**")
    points = pd.DataFrame(
        {
            "Criterion": [INDICATORS[k]["label"].split(" (")[0] for k in INDICATORS],
            "Points": [row[f"pts_{k}"] for k in INDICATORS],
        }
    )
    bar = px.bar(points, x="Points", y="Criterion", orientation="h", range_x=(0, 100))
    bar.update_traces(marker_color=NAVY)
    bar.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), yaxis_title=None)
    st.plotly_chart(bar, width="stretch")

with col_b:
    st.markdown("**Score over time**")
    history = score_history(panel, weights)
    history = history[history["country"] == country]
    line = px.line(history, x="year", y="score", markers=True, range_y=(0, 100))
    line.update_traces(line_color=NAVY)
    line.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), xaxis_title=None)
    st.plotly_chart(line, width="stretch")
    st.caption("Scores are relative: a country is compared with the other countries "
               "in the data set for the same year.")

with st.expander("Method and limits"):
    st.markdown(
        """
        - **Data:** World Bank (World Development Indicators, Worldwide Governance
          Indicators). Missing years are filled with the last known value (max. 3 years).
        - **Score:** each indicator is scaled to 0-100 across all countries (outliers
          capped at the 5th/95th percentile), then combined with your weights.
        - **Inflation** is scored by distance from 2 %, because both very high
          inflation and deflation are bad for planning.
        - **Limits:** this is a first screening tool, not a forecast and not a
          replacement for local research. Industry and target-group specifics are
          not included yet.
        """
    )
