# Methodology

## Goal
Give early-stage founders a fast, transparent first screening of possible foreign markets. The score answers "Where should I look first?", not "Where will I succeed?".

## Data
All indicators come from the World Bank API (World Development Indicators, Worldwide Governance Indicators, Global Findex), years 2005-2024, 42 countries. The dashboard uses the newest year in which at least 20 countries can be scored for the chosen profile.

If a country has no value for a year, the last known value of the same country is carried forward. The allowed number of years differs per indicator (3 years for annual statistics, up to 6 for survey data such as account ownership, which is published every few years).

If a country still lacks an indicator, its score is computed from the criteria it has (weights renormalised) and the dashboard shows the share of weights that had data. Countries with less than 70 % coverage are left out of that ranking and listed.

Indicators marked optional in `src/config.py` are skipped if the World Bank does not deliver them. The profile weights are then renormalised over the remaining indicators.

## Scoring steps
1. **Cap outliers.** Values below the 5th or above the 95th percentile (across all countries, same year) are set to those limits.
2. **Scale to 0-100.** The lowest capped value gets 0 points, the highest 100. Skewed indicators (population, researchers, secure servers) are compared on a log scale. Every country, including the home country, is scaled together, so the home country is a fair benchmark.
3. **Direction.** Most indicators are "higher is better". Inflation is scored by its distance from 2 %. Distance to home is "lower is better". For a *financial inclusion* fintech, a low account ownership is the opportunity, so that indicator is inverted for this focus.
4. **Industry weights.** Each industry focus has base weights (`INDUSTRIES` in `src/config.py`). They are multiplied by factors for the business model (B2B/B2C), the risk priority (balanced, growth, safety) and the budget, then normalised.
5. **Institutional block.** Every profile also receives a block of institutional criteria: political stability, regulatory quality, corruption control, government effectiveness (World Bank governance estimates), current account balance, foreign direct investment and trade openness. The block takes 25 % of the total weight for a balanced profile, 20 % for growth and 37.5 % for safety. This follows how country-risk and market-entry frameworks treat the operating environment as a core part of every decision, not an add-on.
6. **Manual factors (optional).** The user can scale any weight between 0 % and 200 % before normalising; 0 % removes the criterion.
7. **Closeness to home (optional).** Adds up to 30 % weight for two measurable distances from the home country (geographic distance between country centres, and the gap in income per person). Two of the four distances in the CAGE framework (Ghemawat, 2001) can be measured with open data; cultural and administrative distance are not scored.
8. **Combine.** *Weighted average*: score = sum of points x weight. *Balanced*: weighted geometric mean, in which a very weak criterion pulls the score down (points are floored at 1). Use it to test whether a market only looks good because strengths offset a serious weakness.
9. **Pillars.** Each criterion belongs to one of three pillars (market opportunity, operating environment, stability and governance). Pillar scores are the weighted averages of their criteria and are shown for diagnosis; the total score does not add them a second time.
10. **Hard filters (optional).** A country that fails a filter (minimum political stability, rule of law, population, income per person, maximum inflation) is removed from the ranking and listed with the reason. Missing data does not fail a filter.

## Robustness
A ranking is shown with its uncertainty.
- **Weight shaking.** Every weight is multiplied by exp(sigma x z) with z from a standard normal, 1,000 times (seeded, so results are repeatable). sigma is 0.3, 0.6 or 1.0 (low, medium, high). For every country the app reports the 10th and 90th percentile rank, the share of scenarios in which it is first, and in the top three.
- **Confidence.** High: data coverage of at least 90 % and a rank range of at most 4 places. Medium: at least 80 % and at most 8 places. Otherwise Low.
- **Pivotal criteria.** Each criterion is set to zero in turn; if another country then leads, the criterion is listed as decisive.

## Export and sharing
The Excel workbook contains the assumptions, ranking, points, raw values, weights, robustness results, pivotal criteria, hard-filter exclusions and, for every criterion, its source indicator code, direction and retrieval date, so a ranking can be audited and reproduced. A scenario file (JSON) stores all assumptions; the answers also live in the page address so a result can be shared as a link. Both are validated, and invalid values are ignored.

## Explanations
The data briefing is generated by fixed rules from the numbers: strengths are criteria with at least 60 points (largest weighted contribution first), risks are criteria below 40 points (largest weighted shortfall first), and trends compare the current value with the value five years earlier.

## AI advisor
The advisor receives the startup profile, the weights, pillar scores, the robustness summary (confidence, pivotal criteria, filters) and an evidence table for the top six countries (values, points, weights, trends). Its instructions require it to use only these numbers, to justify each recommendation with at least three data points, to name the main risk, to compare the top countries, and to say what the data cannot show. Text from the founder is passed in marked blocks and treated as data, not as instructions. The model can still make mistakes; important facts must be verified. An automatic check of every number in the output is on the roadmap.

## Known limits
- Scores are **relative** to the other countries in the data set, not absolute.
- National averages hide regional differences (cities vs. countryside).
- The score does not see competitors, taxes, licences, language, culture or the product itself. Only geographic and economic distance can be measured with open data.
- World Bank data is published with delay; some indicators lag by one to two years.
- Weights are a judgement call, informed by what each industry needs. They are visible in the app and in `src/config.py` and can be challenged.
- Six industries have their own indicators (Fintech, software, health, energy, consumer, education); "Something else" uses the core and institutional criteria only and says so to the AI adviser. 42 countries so far.
- Rich, small countries rank high in most profiles because most indicators reward wealth and institutions. Use the growth priority, the balanced method, hard filters and the weight sliders to challenge this.
