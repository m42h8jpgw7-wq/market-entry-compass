# Market Entry Compass

**Which country should your startup enter first?**

Most founders pick their first foreign market by gut feeling or by whom they happen to know. Large companies have strategy teams for this decision; early-stage startups do not. Market Entry Compass is a free, transparent screening tool for startups in any industry: you describe your startup, it ranks 42 countries with public data, shows them on a globe you can turn and click, and explains the result. An optional AI advisor (Claude) writes a detailed recommendation, restricted to the numbers the tool provides.

> Status: Version 3 (work in progress). A first screening tool, not a forecast and not legal or financial advice.

![Startup profile and top recommendations](docs/img/startup-profile.png)

![Globe and ranking](docs/img/globe-and-ranking.png)

![Country analysis](docs/img/country-analysis.png)

*Screenshots with real World Bank data (fintech, payments focus, home country Germany).*

## What it does

- **Startup profile:** industry and focus, customers (B2B / B2C), stage, budget, risk priority, home country, free-text description.
- **Six industries, ten focuses:** Fintech, SaaS/B2B software, HealthTech, CleanTech/energy, E-commerce/consumer, and "Other industry" for everything else (general criteria plus your own description). A payments fintech and a financial-inclusion fintech want opposite things from "account ownership"; an off-grid energy startup wants LOW electricity access. Each focus has its own weights (see [`src/config.py`](src/config.py)).
- **Fine-tune:** make any criterion more or less important with a slider and watch the ranking change.
- **3D globe:** drag to rotate, click a country to open its analysis.
- **Country analysis:** score, strengths, risks, five-year trends, points per criterion, score history since 2005.
- **Data briefing:** a rule-based written explanation, built only from the numbers.
- **AI advisor (optional):** Claude reads your profile and the evidence tables and writes a structured recommendation: why #1, why not the others, risks, first 90 days, what the data cannot tell you. It must justify every country with concrete data points and say what to verify. You bring your own Anthropic API key; the app does not store it.

## How the score works

1. Every indicator is scaled to 0-100 points across all countries (outliers capped at the 5th/95th percentile).
2. Weights come from the industry focus and are adjusted by your answers (customers, budget, risk priority).
3. The weighted points add up to the country score.

Indicators (World Bank open data): *core:* GDP growth, purchasing power, population, inflation (best near 2 %), internet users, rule of law. *Fintech:* account ownership, mobile subscriptions, private credit, secure servers. *SaaS:* broadband, R&D spending, researchers, ICT service exports, tertiary enrolment. *Health:* health spending, population 65+, physicians, hospital beds. *Energy:* renewable shares, electricity access, CO2 per person. *Consumer:* urban and working-age population, logistics performance, household spending.

Details and limits: [docs/methodology.md](docs/methodology.md).

## Run it yourself

```bash
git clone https://github.com/m42h8jpgw7-wq/market-entry-compass.git
cd market-entry-compass
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m src.fetch_data     # downloads the data from the World Bank
streamlit run app.py         # opens the dashboard in your browser
python -m pytest             # runs the tests
```

For the AI advisor, paste your Anthropic API key into the Advice section (console.anthropic.com). Without a key everything else works.

## Project structure

```
app.py               Streamlit dashboard (profile form, globe, analysis, advice)
src/ui.py            stylesheet and small HTML helpers (design)
src/config.py        countries, indicators, industry profiles, weights
src/profile.py       startup profile -> score weights
src/scoring.py       data panel and 0-100 scoring
src/evidence.py      numbers, trends, strengths, risks, data briefing
src/advisor.py       prompt and streaming call to Claude
src/fetch_data.py    World Bank download
tests/               tests for scoring, profiles, evidence, prompt
docs/methodology.md  how it works and where it falls short
```

## Roadmap

- [ ] More industries with their own indicators (see [docs/adding-an-industry.md](docs/adding-an-industry.md))
- [ ] Forecasts from published projections (IMF, UN), clearly labelled as estimates
- [ ] Regional data below country level, taxes, funding landscape
- [ ] Automatic check that every number in the AI text appears in the evidence
- [ ] Case study with real founders

## Data sources

World Bank open data: World Development Indicators, Worldwide Governance Indicators, Global Findex (CC BY 4.0).

## License

MIT
