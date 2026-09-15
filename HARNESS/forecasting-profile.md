# The `trading` profile, second-project edition

Harness engineering ships three profiles: code, investigation, prose. None fits a
system whose unit of work is a falsifiable claim about a market. `crypto-trading`
proved a fourth inline; this project is the second deployment, which is the condition
`~/harness/orchestration/registry.md` set for extracting `templates/trading/`.

| | |
|---|---|
| Unit of work | a build unit, and separately a thesis |
| Ledger file | `forecast_ledger.json` |
| Build unit states | `not_started` → `active` → `blocked` → `passing` |
| Thesis states | `hypothesis` → `measured` → `paper` → `live` → `retired` |
| The verification gate | a build unit passes when its command exits 0; a thesis moves out of `measured` only on an independent evaluator's verdict against a metric pre-registered before the result was seen |
| Evidence recorded | commit SHA, test output, or evaluator verdict in `docs/evals/` |
| Generator vs evaluator | a fresh-context subagent, preferably a different model, prompted to refute |
| Clean state adds | journal chain verifies, public commitments synced, disclosure log current |

## Why this profile is different from the other three

The other three cannot lose money. This one can, and the loss is silent: a forecasting
model that is wrong does not crash, it returns a plausible number you then stake.

## The verification traps, ranked

Two are inherited from `crypto-trading`.

**Overfitting reads as alpha.** The backtest is the strategy grading its own homework
on the data it was fit to. Defence: pre-register the metric, commit it before the run,
let git ordering prove it, and have someone else score it.

**Lookahead reads as skill.** Here the form is the closing price, which is the most
predictive number available and does not exist when you forecast. Defence: the price
is recorded inside the forecast, and any scoring path touching a later price raises.

Three are specific to this domain.

**Answer-key leakage.** An agent asked about a resolved question finds the resolution.
This bars backtesting outright. See `docs/decisions/0002`.

**Correlated events read as independent.** The same error inflates apparent sample
size, position size, and model confidence at once, in the same direction. Forty House
races on one national environment are one observation, not forty.

**Resulting bias.** A forecast that resolved correctly was not necessarily a good
forecast. Defence: no verdict is ever issued on a single question.

## What this profile owes `templates/trading/`

Carried forward from crypto-trading: clustered/independent-N named in the
pre-registration, a metric-contract check (returns-series not equity-levels), and
batch-endpoint/incremental-cache guidance for large fetches.

Added here: forward-only validation where an agent can reach the answer key, and the
decomposed-metric gate — proving an edge through low-variance intermediates when the
terminal metric is undetectable at any achievable sample size.
