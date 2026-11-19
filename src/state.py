"""Save and share a scenario: the answers go into the page address, the full
set of assumptions into a small JSON file.

Both are validated against the config, so a broken or hand-edited link can
never crash the app: unknown values are simply ignored.
"""

import json

from src.config import BUDGET_MULTIPLIERS, BUSINESS_MODELS, COUNTRIES, GATES, INDUSTRIES, PRIORITIES

# answer field -> short name in the page address
PARAM = {"industry": "ind", "focus": "foc", "business_model": "bm", "budget": "bud",
         "priority": "pri", "home": "home"}
SCENARIO_VERSION = 1


def answers_to_params(ans: dict) -> dict[str, str]:
    return {PARAM[k]: str(ans[k]) for k in PARAM if ans.get(k)}


def params_to_answers(params) -> dict | None:
    """Valid answers from a page address, or None if it does not describe a profile."""
    industry = params.get(PARAM["industry"])
    if industry not in INDUSTRIES:
        return None
    focus = params.get(PARAM["focus"])
    if focus not in INDUSTRIES[industry]["focuses"]:
        focus = next(iter(INDUSTRIES[industry]["focuses"]))
    out = {"industry": industry, "focus": focus}
    for field, table in (("business_model", BUSINESS_MODELS), ("budget", BUDGET_MULTIPLIERS),
                         ("priority", PRIORITIES)):
        value = params.get(PARAM[field])
        out[field] = value if value in table else next(iter(table))
    home = params.get(PARAM["home"])
    out["home"] = home if home in COUNTRIES or home == "(none)" else "DEU"
    return out


def scenario_to_json(ans: dict, assumptions: dict) -> str:
    return json.dumps({"version": SCENARIO_VERSION, "answers": {k: ans.get(k, "") for k in (
        "industry", "focus", "business_model", "budget", "priority", "home", "description",
        "notes", "industry_name")}, "assumptions": assumptions}, indent=2, ensure_ascii=False)


def scenario_from_json(text: str) -> tuple[dict, dict] | None:
    """(answers, assumptions) from a saved scenario, or None if it is not valid."""
    try:
        data = json.loads(text)
        ans = params_to_answers({PARAM[k]: data["answers"].get(k, "") for k in PARAM})
        if ans is None:
            return None
    except (ValueError, KeyError, AttributeError, TypeError):
        return None
    for field in ("description", "notes", "industry_name"):
        ans[field] = str(data["answers"].get(field, ""))[:2000]
    raw = data.get("assumptions", {}) if isinstance(data.get("assumptions"), dict) else {}
    assumptions = {
        "method": raw.get("method") if raw.get("method") in ("arithmetic", "balanced") else "arithmetic",
        "closeness": _number(raw.get("closeness"), 0, 30, 0),
        "overrides": {k: _number(v, 0, 200, 100) for k, v in (raw.get("overrides") or {}).items()
                      if isinstance(k, str)},
        "gates": {k: _number(v, -1e12, 1e12, GATES[k]["default"]) for k, v in (raw.get("gates") or {}).items()
                  if k in GATES},
    }
    return ans, assumptions


def _number(value, low, high, default):
    try:
        return min(max(float(value), low), high)
    except (TypeError, ValueError):
        return default
