"""The founder's answers and how they turn into score weights."""

from dataclasses import dataclass, field

from src.config import (
    BUDGET_MULTIPLIERS,
    BUSINESS_MODELS,
    INDICATORS,
    INDUSTRIES,
    PRIORITIES,
)


@dataclass
class StartupProfile:
    """Everything the founder tells us about the startup."""

    industry: str = "fintech"
    focus: str = "payments"
    business_model: str = "b2b"
    priority: str = "balanced"
    budget: str = "low"
    stage: str = "First customers at home"
    description: str = ""          # free text: what the startup does, for whom
    home_country: str = "DEU"      # ISO3; excluded from the ranking
    extra_notes: str = field(default="")  # constraints: languages, regulation, team ...
    industry_name: str = ""        # free text, used when industry == "other"

    def focus_spec(self) -> dict:
        return INDUSTRIES[self.industry]["focuses"][self.focus]

    def industry_label(self) -> str:
        if self.industry == "other" and self.industry_name.strip():
            return f"Other: {self.industry_name.strip()}"
        return INDUSTRIES[self.industry]["label"]

    def is_generic(self) -> bool:
        """True if no industry-specific indicators are used."""
        return self.industry == "other"


def build_weights(profile: StartupProfile, available: set[str] | None = None,
                  overrides: dict[str, float] | None = None):
    """Return (weights, inverted_indicators) for this startup.

    Steps: start from the industry focus, multiply by what the business model,
    the risk priority and the budget say, apply optional manual factors, drop indicators that have no data,
    and normalise so the weights add up to 1.
    """
    focus = profile.focus_spec()
    weights = dict(focus["weights"])
    invert = set(focus.get("invert", []))

    for table, key in (
        (BUSINESS_MODELS, profile.business_model),
        (PRIORITIES, profile.priority),
        (BUDGET_MULTIPLIERS, profile.budget),
    ):
        for indicator, factor in table[key]["multipliers"].items():
            if indicator in weights:
                weights[indicator] *= factor

    if overrides:  # manual fine-tuning: factor per indicator (1.0 = unchanged)
        for indicator, factor in overrides.items():
            if indicator in weights:
                weights[indicator] *= max(float(factor), 0.0)

    weights = {k: v for k, v in weights.items() if k in INDICATORS}
    if available is not None:
        weights = {k: v for k, v in weights.items() if k in available}

    total = sum(weights.values())
    if total <= 0:
        raise ValueError("No usable indicators for this profile. Run: python -m src.fetch_data")
    return {k: v / total for k, v in weights.items()}, invert
