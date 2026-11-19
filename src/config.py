"""Central settings for Market Entry Compass.

Everything a founder might want to change later (countries, indicators,
default weights) lives here, so the rest of the code stays simple.
"""

# ---------------------------------------------------------------------------
# Indicators (all from the World Bank, free and public)
# ---------------------------------------------------------------------------
# key            -> short name used everywhere in the code
# code           -> World Bank indicator code
# label          -> text shown in the dashboard
# higher_is_better -> True: bigger value = more attractive market
#                     "target": best value is close to `target` (e.g. inflation)
# source         -> World Bank "source" id (only needed for governance data)
INDICATORS = {
    "growth": {
        "code": "NY.GDP.MKTP.KD.ZG",
        "label": "GDP growth (% per year)",
        "question": "Is the economy growing?",
        "higher_is_better": True,
    },
    "purchasing_power": {
        "code": "NY.GDP.PCAP.PP.CD",
        "label": "GDP per capita, PPP (current int. $)",
        "question": "Can customers afford your product?",
        "higher_is_better": True,
    },
    "stability": {
        "code": "FP.CPI.TOTL.ZG",
        "label": "Inflation (% per year)",
        "question": "Are prices and costs predictable?",
        "higher_is_better": "target",
        "target": 2.0,  # central banks in rich countries aim for about 2 %
    },
    "digital": {
        "code": "IT.NET.USER.ZS",
        "label": "Internet users (% of population)",
        "question": "Can you reach customers online?",
        "higher_is_better": True,
    },
    "rule_of_law": {
        "code": "GOV_WGI_RL.EST",  # Worldwide Governance Indicators, via the WDI database
        "fallback": {"code": "RL.EST", "source": 3},  # older code, tried if the first fails
        "label": "Rule of law (WGI estimate, -2.5 to +2.5)",
        "question": "Are contracts and property protected?",
        "higher_is_better": True,
    },
}

# Default importance of each criterion (must add up to 1.0).
DEFAULT_WEIGHTS = {
    "growth": 0.30,
    "purchasing_power": 0.20,
    "stability": 0.15,
    "digital": 0.15,
    "rule_of_law": 0.20,
}

# ---------------------------------------------------------------------------
# Countries (ISO3 codes) - Version 1 starts with 42 countries.
# ---------------------------------------------------------------------------
COUNTRIES = [
    # Europe
    "DEU", "FRA", "GBR", "ESP", "ITA", "NLD", "SWE", "POL", "CHE", "NOR",
    "IRL", "PRT", "AUT", "DNK", "TUR",
    # Americas
    "USA", "CAN", "MEX", "BRA", "ARG", "CHL", "COL",
    # Asia-Pacific
    "JPN", "KOR", "CHN", "IND", "IDN", "VNM", "THA", "MYS", "SGP", "PHL",
    "AUS", "NZL",
    # Middle East & Africa
    "ARE", "SAU", "EGY", "ZAF", "NGA", "KEN", "MAR", "ISR",
]

START_YEAR = 2005
END_YEAR = 2024

# Where the downloaded data is stored
DATA_FILE = "data/processed/indicators.csv"
