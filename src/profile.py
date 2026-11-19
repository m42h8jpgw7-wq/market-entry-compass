"""The founder's answers and how they turn into score weights."""

from dataclasses import dataclass, field

from src.config import (
    BLOCK_FACTOR,
    BUDGET_MULTIPLIERS,
    BUSINESS_MODELS,
    INDICATORS,
    INDUSTRIES,
    INSTITUTIONAL_BLOCK,
    INSTITUTIONAL_SHARE,
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


def _normalise(weights: dict) -> dict:
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()} if total > 0 else {}


def build_weights(profile: StartupProfile, available: set[str] | None = None,
                  overrides: dict[str, float] | None = None,
                  extra: dict[str, float] | None = None):
    """Return (weights, inverted_indicators) for this startup.

    1. Start from the industry focus and multiply by what the business model,
       the risk priority and the budget say.
    2. Add the institutional block (political stability, regulation, ...) that
       applies to every profile; its share depends on the risk priority.
    3. Apply optional manual factors (`overrides`, 1.0 = unchanged) and drop
       indicators that have no data.
    4. `extra` adds absolute shares of the final total (e.g. closeness to home).
    The result is normalised so the weights add up to 1.
    """
    focus = profile.focus_spec()
    industry = {k: v for k, v in focus["weights"].items() if k in INDICATORS}
    invert = set(focus.get("invert", []))

    for table, key in (
        (BUSINESS_MODELS, profile.business_model),
        (PRIORITIES, profile.priority),
        (BUDGET_MULTIPLIERS, profile.budget),
    ):
        for indicator, factor in table[key]["multipliers"].items():
            if indicator in industry:
                industry[indicator] *= factor

    block = {k: v for k, v in INSTITUTIONAL_BLOCK.items() if k in INDICATORS}

    def usable(weights: dict) -> dict:
        if overrides:
            weights = {k: v * max(float(overrides.get(k, 1.0)), 0.0) for k, v in weights.items()}
        if available is not None:
            weights = {k: v for k, v in weights.items() if k in available}
        return {k: v for k, v in weights.items() if v > 0}

    industry, block = _normalise(usable(industry)), _normalise(usable(block))
    if not industry and not block:
        raise ValueError("No usable indicators for this profile. Run: python -m src.fetch_data")

    share = min(INSTITUTIONAL_SHARE * BLOCK_FACTOR.get(profile.priority, 1.0), 0.6) if block else 0.0
    if not industry:
        share = 1.0
    weights: dict[str, float] = {}
    for k, v in industry.items():
        weights[k] = weights.get(k, 0.0) + v * (1 - share)
    for k, v in block.items():
        weights[k] = weights.get(k, 0.0) + v * share

    extra = {k: v for k, v in (extra or {}).items()
             if v > 0 and (available is None or k in available) and k in INDICATORS}
    if extra:
        room = 1 - min(sum(extra.values()), 0.5)
        weights = {k: v * room for k, v in weights.items()}
        for k, v in extra.items():
            weights[k] = weights.get(k, 0.0) + v
    return _normalise(weights), invert
