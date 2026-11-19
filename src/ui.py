"""Look and feel: one stylesheet and a few small HTML helpers.

Design idea: a calm, light page (cool grey paper, white panels, one blue accent)
and one dark panel, the globe, as the visual centre.
"""

import html

INK, MUTED, LINE = "#0E1B2E", "#5B6779", "#E1E5EC"
BLUE, GOOD, BAD, AMBER = "#1F5EFF", "#0F7B63", "#B03A2E", "#FFB547"
GLOBE_BG, GLOBE_LAND, GLOBE_LINE = "#0A1730", "#14284A", "#0A1730"
GLOBE_SCALE = [[0, "#1D3358"], [0.5, "#2F6FED"], [1, "#7DF0DC"]]

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');
html, body, .stApp, .stMarkdown, input, textarea, button {{ font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; }}
.stApp {{ background: #F5F7FA; color: {INK}; }}
header[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stToolbar"], [data-testid="stDecoration"] {{ display: none; }}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {{ display: none; }}
.block-container {{ max-width: 1180px; padding: 2.2rem 1.5rem 4rem; }}
h1, h2, h3, h4 {{ font-family: 'Inter Tight', 'Inter', system-ui, sans-serif; color: {INK};
  letter-spacing: -0.02em; font-weight: 600; }}
div[data-testid="stHeading"] h2 {{ font-size: 1.45rem; margin-top: 1.6rem; }}
div[data-testid="stHeading"] {{ margin-top: 1.4rem; }}

.stApp .stMarkdown h3, .stApp div[data-testid="stHeading"] h3 {{ font-size: 1.15rem !important; margin-top: 1.2rem; }}
.mec-hero {{ padding: .4rem 0 .6rem; }}
.mec-hero .brand {{ font-family: 'Inter Tight', 'Inter', system-ui, sans-serif; font-weight: 700; font-size: 1rem;
  color: {BLUE}; letter-spacing: -0.01em; }}
.mec-hero h1 {{ font-size: 2.7rem; line-height: 1.08; margin: .5rem 0 .7rem; max-width: 15em;
  font-weight: 700; letter-spacing: -0.03em; }}
.mec-hero p {{ color: {MUTED}; font-size: 1.08rem; max-width: 42em; line-height: 1.55; margin: 0; }}

.mec-note {{ color: {MUTED}; font-size: .92rem; line-height: 1.5; }}
.mec-hint {{ border-left: 3px solid {BLUE}; padding: .15rem 0 .15rem .8rem; color: {INK};
  font-size: .95rem; line-height: 1.5; margin: .6rem 0 .2rem; }}


/* guided questions */
.st-key-wizard {{ max-width: 1000px; }}
.mec-q {{ font-family: 'Inter Tight', 'Inter', system-ui, sans-serif; font-size: 2rem; font-weight: 700;
  letter-spacing: -0.03em; line-height: 1.15; margin: .9rem 0 .3rem; color: {INK}; }}
.mec-qhelp {{ color: {MUTED}; font-size: 1.02rem; margin: 0 0 1.3rem; line-height: 1.5; }}
.mec-step {{ color: {MUTED}; font-size: .86rem; margin-top: .3rem; }}
[class*="st-key-tile_"] {{ background: #fff; border: 1px solid {LINE}; border-radius: 12px;
  padding: 1.05rem 1.15rem 1rem; min-height: 13.4rem; transition: border-color .15s, box-shadow .15s; }}
[class*="st-key-tile_"]:hover {{ border-color: {BLUE}; box-shadow: 0 2px 14px rgba(31,94,255,.10); }}
.mec-tile-t {{ font-family: 'Inter Tight', 'Inter', system-ui, sans-serif; font-weight: 600;
  font-size: 1.12rem; letter-spacing: -0.01em; color: {INK}; margin-bottom: .25rem; }}
.mec-tile-d {{ color: {MUTED}; font-size: .92rem; line-height: 1.45; margin-bottom: .7rem; }}
[class*="st-key-tile_"] > div:last-child {{ margin-top: auto; }}
[class*="st-key-tile_"] .stButton > button {{ border-radius: 8px; font-weight: 600; }}
.stProgress > div > div > div > div {{ background-color: {BLUE}; }}

/* answers summary on the results page */
.mec-chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin: .6rem 0 .3rem; }}
.mec-chip {{ background: #fff; border: 1px solid {LINE}; border-radius: 999px; padding: .28rem .8rem;
  font-size: .86rem; color: {INK}; }}
.mec-lead {{ font-size: 1.15rem; line-height: 1.5; color: {INK}; max-width: 46em; }}

/* white panels */
[class*="st-key-panel"] {{ background: #fff; border: 1px solid {LINE}; border-radius: 12px;
  padding: 1.3rem 1.4rem; }}

/* top recommendations: the winner is large, the others quiet */
.mec-top {{ display: grid; grid-template-columns: 1.35fr 1fr 1fr; gap: 14px; }}
.mec-pick {{ background: #fff; border: 1px solid {LINE}; border-radius: 12px; padding: 1.15rem 1.3rem; }}
.mec-pick.first {{ background: {INK}; color: #fff; border-color: {INK}; }}
.mec-pick .rk {{ font-size: .82rem; color: {MUTED}; }}
.mec-pick.first .rk {{ color: #9FB2D0; }}
.mec-pick .nm {{ font-family: 'Inter Tight', 'Inter', system-ui, sans-serif; font-weight: 600; font-size: 1.5rem;
  letter-spacing: -0.02em; margin: .15rem 0 .1rem; }}
.mec-pick.first .nm {{ font-size: 2rem; }}
.mec-pick .sc {{ font-size: .95rem; color: {MUTED}; margin-bottom: .6rem; }}
.mec-pick.first .sc {{ color: #9FB2D0; }}
.mec-pick .sc b {{ font-size: 1.15rem; color: {INK}; }}
.mec-pick.first .sc b {{ color: #fff; }}
.mec-pick ul {{ list-style: none; padding: 0; margin: 0; font-size: .9rem; line-height: 1.45; }}
.mec-pick li {{ padding-left: 1.1rem; position: relative; margin-bottom: .25rem; }}
.mec-pick li::before {{ content: ''; position: absolute; left: 0; top: .55em; width: 7px; height: 7px;
  border-radius: 50%; background: {GOOD}; }}
.mec-pick li.risk::before {{ background: {BAD}; }}
.mec-pick.first li::before {{ background: #7DF0DC; }}
.mec-pick.first li.risk::before {{ background: {AMBER}; }}
@media (max-width: 800px) {{ .mec-top {{ grid-template-columns: 1fr; }}
  .mec-hero h1 {{ font-size: 2rem; }} }}

/* the globe: the one dark, memorable element */
.st-key-globe_panel {{ background: {GLOBE_BG}; border-radius: 16px; padding: .4rem .4rem 0; }}
.st-key-globe_panel .js-plotly-plot, .st-key-globe_panel .stPlotlyChart {{ border-radius: 12px; }}
.mec-globe-cap {{ color: #8FA3C4; font-size: .85rem; padding: .7rem 1rem 0; }}

/* ranking list */
.mec-rank {{ width: 100%; border-collapse: collapse; font-size: .92rem; }}
.mec-rank td {{ padding: .42rem .3rem; border-bottom: 1px solid {LINE}; vertical-align: middle; }}
.mec-rank tr.sel td {{ background: #EEF3FF; font-weight: 600; }}
.mec-rank .n {{ color: {MUTED}; width: 2rem; text-align: right; padding-right: .7rem; }}
.mec-rank .bar {{ width: 38%; }}
.mec-rank .bar span {{ display: block; height: 6px; border-radius: 3px; background: {BLUE}; }}
.mec-rank .v {{ white-space: nowrap; width: 2.6rem; text-align: right; font-variant-numeric: tabular-nums; }}
.mec-rank .cov {{ white-space: nowrap; color: {MUTED}; width: 3rem; text-align: right; font-size: .82rem; }}
.mec-scroll {{ max-height: 520px; overflow-y: auto; }}

/* controls */
div[data-baseweb="select"] > div, .stTextInput input, .stTextArea textarea {{
  border-radius: 8px !important; border-color: {LINE} !important; background: #fff; }}
.stButton > button[kind="primary"] {{ background: {BLUE}; border: 0; border-radius: 8px;
  font-weight: 600; padding: .55rem 1.2rem; }}
.stButton > button[kind="primary"]:hover {{ background: #1649D6; }}
.stButton > button:focus-visible, input:focus-visible {{ outline: 2px solid {BLUE}; outline-offset: 2px; }}
label p {{ font-size: .86rem !important; color: {MUTED}; font-weight: 500; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 500; }}

/* workbench */
.mec-topbar {{ display: flex; align-items: baseline; justify-content: space-between; gap: 1rem;
  border-bottom: 1px solid {LINE}; padding: 0 0 .7rem; margin-bottom: .9rem; }}
.mec-topbar .brand {{ font-family: 'Inter Tight', 'Inter', system-ui, sans-serif; font-weight: 700; font-size: 1.05rem;
  color: {INK}; letter-spacing: -0.01em; }}
.mec-topbar .brand i {{ font-style: normal; color: {BLUE}; }}
.mec-topbar .stamp {{ color: {MUTED}; font-size: .82rem; text-align: right; }}
.mec-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0;
  background: #fff; border: 1px solid {LINE}; border-radius: 12px; margin: .8rem 0 1rem; overflow: hidden; }}
.mec-kpi {{ padding: .85rem 1.1rem; border-right: 1px solid {LINE}; }}
.mec-kpi:last-child {{ border-right: 0; }}
.mec-kpi .l {{ color: {MUTED}; font-size: .8rem; }}
.mec-kpi .v {{ font-family: 'Inter Tight', 'Inter', system-ui, sans-serif; font-size: 1.45rem; font-weight: 600;
  letter-spacing: -0.02em; font-variant-numeric: tabular-nums; margin-top: .1rem; }}
.mec-kpi .s {{ color: {MUTED}; font-size: .78rem; }}
.mec-badge {{ display: inline-block; border-radius: 999px; padding: .08rem .6rem; font-size: .78rem; font-weight: 600; }}
.mec-badge.High {{ background: #E3F4EE; color: {GOOD}; }}
.mec-badge.Medium {{ background: #FFF1D9; color: #8A5A00; }}
.mec-badge.Low {{ background: #F9E3E0; color: {BAD}; }}
.mec-memo {{ background: #fff; border: 1px solid {LINE}; border-left: 4px solid {BLUE}; border-radius: 8px;
  padding: 1rem 1.3rem; line-height: 1.6; }}
.mec-memo p {{ margin: 0 0 .55rem; }}
.mec-memo p:last-child {{ margin-bottom: 0; }}
.mec-disclaimer {{ color: {MUTED}; font-size: .8rem; line-height: 1.5; border-top: 1px solid {LINE};
  margin-top: 2.2rem; padding-top: .9rem; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 1.4rem; border-bottom: 1px solid {LINE}; }}
.stTabs [data-baseweb="tab"] {{ padding: .5rem 0; font-weight: 500; color: {MUTED}; }}
.stTabs [aria-selected="true"] {{ color: {INK}; font-weight: 600; }}
[data-testid="stDataFrame"], .mec-rank, .mec-kpi {{ font-variant-numeric: tabular-nums; }}
[data-testid="stExpander"] {{ background: #fff; border: 1px solid {LINE}; border-radius: 10px; }}
</style>
"""


def esc(text) -> str:
    return html.escape(str(text))


def hero() -> str:
    return (
        '<div class="mec-hero"><div class="brand">Market Entry Compass</div>'
        "<h1>Which country should your startup enter first?</h1>"
        "<p>Answer a few simple questions. We compare 42 countries with open World Bank data "
        "and explain the result in plain language. No experience needed.</p></div>"
    )


def top_picks(evidence: list[dict]) -> str:
    cards = []
    for i, ev in enumerate(evidence[:3]):
        items = "".join(f"<li>{esc(s['label'])}: {esc(s['value_text'])}</li>" for s in ev["strengths"][:2])
        items += "".join(f'<li class="risk">{esc(r["label"])}: {esc(r["value_text"])}</li>'
                         for r in ev["risks"][:1])
        cards.append(
            f'<div class="mec-pick{" first" if i == 0 else ""}">'
            f'<div class="rk">Rank {ev["rank"]}</div><div class="nm">{esc(ev["country"])}</div>'
            f'<div class="sc"><b>{ev["score"]:.0f}</b> of 100 points</div><ul>{items}</ul></div>'
        )
    return f'<div class="mec-top">{"".join(cards)}</div>'


def ranking_table(ranking, selected: str) -> str:
    rows = []
    for r in ranking.itertuples():
        cls = ' class="sel"' if r.iso3 == selected else ""
        rows.append(
            f"<tr{cls}><td class='n'>{int(r.rank)}</td><td>{esc(r.country)}</td>"
            f"<td class='bar'><span style='width:{r.score:.0f}%'></span></td>"
            f"<td class='v'>{r.score:.0f}</td><td class='cov'>{r.coverage * 100:.0f} %</td></tr>"
        )
    return f'<div class="mec-scroll"><table class="mec-rank">{"".join(rows)}</table></div>'


def question(title: str, help_text: str = "") -> str:
    helper = f'<p class="mec-qhelp">{esc(help_text)}</p>' if help_text else ""
    return f'<div class="mec-q">{esc(title)}</div>{helper}'


def tile(title: str, description: str) -> str:
    return f'<div class="mec-tile-t">{esc(title)}</div><div class="mec-tile-d">{esc(description)}</div>'


def chips(items: list[str]) -> str:
    return '<div class="mec-chips">' + "".join(f'<span class="mec-chip">{esc(i)}</span>' for i in items) + "</div>"


def topbar(stamp: str) -> str:
    return (f'<div class="mec-topbar"><div class="brand">Market Entry <i>Compass</i></div>'
            f'<div class="stamp">{esc(stamp)}</div></div>')


def kpis(items: list[tuple[str, str, str]]) -> str:
    """items = [(label, value, small text)]; values are plain text (escaped)."""
    cells = "".join(
        f'<div class="mec-kpi"><div class="l">{esc(l)}</div><div class="v">{esc(v)}</div>'
        f'<div class="s">{esc(sub)}</div></div>' for l, v, sub in items)
    return f'<div class="mec-kpis">{cells}</div>'


def badge(level: str) -> str:
    return f'<span class="mec-badge {esc(level)}">{esc(level)}</span>'


def memo(markdown_text: str) -> str:
    """Summary text (markdown **bold** only) as paragraphs in a memo box."""
    paragraphs = []
    for para in markdown_text.split("\n\n"):
        safe = esc(para)
        while "**" in safe:
            safe = safe.replace("**", "<b>", 1).replace("**", "</b>", 1)
        paragraphs.append(f"<p>{safe}</p>")
    return f'<div class="mec-memo">{"".join(paragraphs)}</div>'
