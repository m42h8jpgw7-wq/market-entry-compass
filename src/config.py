"""Central settings for Market Entry Compass.

Everything a founder-facing change needs lives here: which countries, which
indicators, and how every industry weights them. The rest of the code just
reads this file.
"""

# ---------------------------------------------------------------------------
# Indicators (all from the World Bank, free and public)
# ---------------------------------------------------------------------------
# group            "core" = used for every startup, otherwise an industry key
# code             World Bank indicator code
# higher_is_better True, False, or "target" (best value is close to `target`)
# log              True = compare on a log scale (for very skewed values)
# carry            how many years an old value may be carried forward when the
#                  newest year is missing (survey data is published rarely)
# optional         True = if the download fails, skip it instead of stopping
INDICATORS = {
    # ----- core: relevant for every startup --------------------------------
    "growth": {
        "group": "core", "code": "NY.GDP.MKTP.KD.ZG",
        "label": "GDP growth", "unit": "% per year",
        "question": "Is the economy growing?",
        "higher_is_better": True, "carry": 3,
    },
    "purchasing_power": {
        "group": "core", "code": "NY.GDP.PCAP.PP.CD",
        "label": "Purchasing power", "unit": "GDP per capita, PPP, int. $",
        "question": "Can customers afford your product?",
        "higher_is_better": True, "carry": 3,
    },
    "market_size": {
        "group": "core", "code": "SP.POP.TOTL",
        "label": "Market size", "unit": "population",
        "question": "How many potential customers are there?",
        "higher_is_better": True, "log": True, "carry": 3,
    },
    "stability": {
        "group": "core", "code": "FP.CPI.TOTL.ZG",
        "label": "Price stability", "unit": "inflation, % per year",
        "question": "Are prices and costs predictable?",
        "higher_is_better": "target", "target": 2.0, "carry": 3,
    },
    "digital": {
        "group": "core", "code": "IT.NET.USER.ZS",
        "label": "Internet users", "unit": "% of population",
        "question": "Can you reach customers online?",
        "higher_is_better": True, "carry": 3,
    },
    "rule_of_law": {
        "group": "core", "code": "GOV_WGI_RL.EST",
        "fallback": {"code": "RL.EST", "source": 3},
        "label": "Rule of law", "unit": "WGI estimate, -2.5 to +2.5",
        "question": "Are contracts and property protected?",
        "higher_is_better": True, "carry": 3,
    },
    # ----- fintech ---------------------------------------------------------
    "account_ownership": {
        "group": "fintech", "code": "FX.OWN.TOTL.ZS",
        "label": "Account ownership", "unit": "% of adults (Global Findex)",
        "question": "How many adults already have a bank or mobile-money account?",
        "higher_is_better": True, "carry": 6, "optional": True,
    },
    "mobile_subs": {
        "group": "fintech", "code": "IT.CEL.SETS.P2",
        "label": "Mobile subscriptions", "unit": "per 100 people",
        "question": "Do people carry a phone you can build on?",
        "higher_is_better": True, "carry": 3, "optional": True,
    },
    "private_credit": {
        "group": "fintech", "code": "FS.AST.PRVT.GD.ZS",
        "label": "Private credit", "unit": "% of GDP",
        "question": "How deep is the financial system?",
        "higher_is_better": True, "carry": 3, "optional": True,
    },
    "secure_servers": {
        "group": "fintech", "code": "IT.NET.SECR.P6",
        "label": "Secure internet servers", "unit": "per million people",
        "question": "Is the infrastructure for secure online payments there?",
        "higher_is_better": True, "log": True, "carry": 3, "optional": True,
    },
    # ----- SaaS / B2B software --------------------------------------------
    "broadband": {
        "group": "saas", "code": "IT.NET.BBND.P2",
        "label": "Fixed broadband", "unit": "subscriptions per 100 people",
        "question": "Do companies have fast, reliable internet?",
        "higher_is_better": True, "carry": 3, "optional": True,
    },
    "rnd": {
        "group": "saas", "code": "GB.XPD.RSDV.GD.ZS",
        "label": "R&D spending", "unit": "% of GDP",
        "question": "Is the economy innovation-driven?",
        "higher_is_better": True, "carry": 4, "optional": True,
    },
    "researchers": {
        "group": "saas", "code": "SP.POP.SCIE.RD.P6",
        "label": "Researchers", "unit": "per million people",
        "question": "Is there a pool of technical talent?",
        "higher_is_better": True, "log": True, "carry": 5, "optional": True,
    },
    "ict_exports": {
        "group": "saas", "code": "BX.GSR.CCIS.ZS",
        "label": "ICT service exports", "unit": "% of service exports",
        "question": "Is the country a proven software and IT-services economy?",
        "higher_is_better": True, "carry": 3, "optional": True,
    },
    "tertiary": {
        "group": "saas", "code": "SE.TER.ENRR",
        "label": "Tertiary enrolment", "unit": "% gross",
        "question": "Is there an educated workforce coming through?",
        "higher_is_better": True, "carry": 5, "optional": True,
    },
}

# ---------------------------------------------------------------------------
# Industry profiles
# ---------------------------------------------------------------------------
# For each industry: a short description and one or more "focus" variants.
# A focus holds the weights (they are normalised later, so they do not have
# to add up to 1) and optionally `invert`: indicators where LOW is the
# opportunity (e.g. few bank accounts = room for financial inclusion).
INDUSTRIES = {
    "fintech": {
        "label": "Fintech",
        "description": "Payments, banking, lending, insurance and other financial products.",
        "focuses": {
            "payments": {
                "label": "Payments, neobanking, B2B finance",
                "text": "Needs customers who are already banked and digital, "
                        "and a legal system that protects contracts.",
                "weights": {
                    "rule_of_law": 0.18, "account_ownership": 0.14, "digital": 0.10,
                    "stability": 0.10, "growth": 0.10, "purchasing_power": 0.09,
                    "market_size": 0.08, "mobile_subs": 0.06, "private_credit": 0.07,
                    "secure_servers": 0.04,
                },
            },
            "inclusion": {
                "label": "Financial inclusion (serving the unbanked)",
                "text": "Looks for large populations without accounts but with "
                        "mobile phones, so LOW account ownership counts as an opportunity.",
                "weights": {
                    "account_ownership": 0.30, "mobile_subs": 0.14, "market_size": 0.14,
                    "growth": 0.12, "rule_of_law": 0.10, "digital": 0.08,
                    "stability": 0.06, "purchasing_power": 0.06,
                },
                "invert": ["account_ownership"],
            },
        },
    },
    "saas": {
        "label": "SaaS / B2B software",
        "description": "Software sold to companies, usually by subscription.",
        "focuses": {
            "b2b_saas": {
                "label": "B2B software and developer tools",
                "text": "Needs digital companies with budget, good connectivity, "
                        "a tech talent pool and reliable contract law.",
                "weights": {
                    "purchasing_power": 0.14, "rule_of_law": 0.14, "broadband": 0.12,
                    "digital": 0.08, "ict_exports": 0.10, "rnd": 0.09,
                    "researchers": 0.07, "tertiary": 0.04, "market_size": 0.08,
                    "growth": 0.08, "stability": 0.10,
                },
            },
        },
    },
}

# How the founder's answers shift the weights (multipliers on the profile).
PRIORITIES = {
    "balanced": {"label": "Balanced", "multipliers": {}},
    "growth": {
        "label": "Growth first (accept more risk)",
        "multipliers": {"growth": 2.0, "market_size": 1.4, "rule_of_law": 0.7, "stability": 0.7},
    },
    "safety": {
        "label": "Safety first (predictable markets)",
        "multipliers": {"rule_of_law": 1.8, "stability": 1.6, "growth": 0.7},
    },
}

BUSINESS_MODELS = {
    "b2b": {"label": "B2B (companies are the customers)",
            "multipliers": {"purchasing_power": 1.2, "rule_of_law": 1.2, "market_size": 0.8}},
    "b2c": {"label": "B2C (consumers are the customers)",
            "multipliers": {"market_size": 1.5, "digital": 1.3, "purchasing_power": 1.3}},
    "both": {"label": "Both / marketplace", "multipliers": {}},
}

# A small budget cannot absorb surprises, so predictability counts more.
BUDGET_MULTIPLIERS = {
    "low": {"label": "Low (bootstrapped / pre-seed)",
            "multipliers": {"stability": 1.4, "rule_of_law": 1.2}},
    "medium": {"label": "Medium (seed)", "multipliers": {}},
    "high": {"label": "High (Series A or later)", "multipliers": {}},
}

STAGES = ["Idea / prototype", "First customers at home", "Growing at home",
          "Already selling abroad"]

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

# Claude model used by the AI advisor (any current Claude model name works)
ADVISOR_MODEL = "claude-sonnet-5-5"
