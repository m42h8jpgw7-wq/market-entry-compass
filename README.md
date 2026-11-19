# Market Entry Compass

**Which country should your startup enter first?**

Most founders choose their first foreign market by gut feeling or by who they happen to know. Large companies have strategy teams for this decision, early-stage startups do not. Market Entry Compass is a free, transparent screening tool that ranks countries for international expansion, using public data only.

> Status: Version 1 (work in progress). First screening tool, not a forecast.

## What it does

- **Ranking** of 42 countries by a 0-100 attractiveness score
- **World map** coloured by score
- **Country analysis** with a plain-language explanation of the score
- **Time line** showing how a country's score developed since 2005
- **Adjustable weights**: a fintech founder and a hardware founder care about different things

## The score

| Criterion | Question for the founder | World Bank indicator |
|---|---|---|
| Growth | Is the economy growing? | GDP growth (`NY.GDP.MKTP.KD.ZG`) |
| Purchasing power | Can customers afford the product? | GDP per capita, PPP (`NY.GDP.PCAP.PP.CD`) |
| Stability | Are prices predictable? | Inflation (`FP.CPI.TOTL.ZG`), best near 2 % |
| Digital reach | Can you reach customers online? | Internet users (`IT.NET.USER.ZS`) |
| Rule of law | Are contracts and property protected? | WGI Rule of Law (`RL.EST`) |

Each indicator is scaled to 0-100 across all countries (outliers capped at the 5th/95th percentile) and combined with the weights you choose. Full details: [docs/methodology.md](docs/methodology.md).

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

## Project structure

```
app.py               Streamlit dashboard
src/config.py        countries, indicators, default weights
src/fetch_data.py    World Bank download
src/scoring.py       score calculation and explanations
tests/               tests for the scoring logic
docs/methodology.md  how the score works and where it falls short
```

## Roadmap

- [ ] Target group and industry layer (e.g. B2B software vs. consumer fintech)
- [ ] Forecasts from published projections (IMF, UN), clearly labelled as estimates
- [ ] Startup-specific criteria (cost and time to start a business, funding, talent)
- [ ] Case study with real founders

## Data sources

World Bank: World Development Indicators and Worldwide Governance Indicators (open data, CC BY 4.0).

## License

MIT
