# Adding an industry

1. **Indicators.** In `src/config.py`, add the World Bank indicators you need to `INDICATORS`: `group`, `code`, `label`, `unit`, `higher_is_better`, optional `log` (skewed data) and `carry` (how many years an old value may be reused). Mark new ones `"optional": True`.
2. **Industry.** Add an entry to `INDUSTRIES` with one or more `focuses`. Each focus has a label, a short text, base `weights` (any positive numbers) and optionally `invert`: indicators where a LOW value is the opportunity.
3. **Formatting.** Add a branch to `fmt_value` in `src/evidence.py` so values show with units.
4. **Data.** Run `python -m src.fetch_data`. Indicators that the World Bank no longer serves are skipped and the weights are renormalised.
5. **Check.** Run `python -m pytest` (every focus must only use known indicators) and look at the ranking: does the top and bottom make sense for the industry? Write down your reasoning for each weight.
6. **Pillar.** If the new indicator is not an operating-environment criterion, add it to `PILLAR_OF` in `src/config.py` (opportunity, operating, stability). Unlisted indicators count as operating environment.
7. **Institutional block.** Every profile already gets the institutional block (`INSTITUTIONAL_BLOCK`); do not repeat those indicators in an industry's weights.
