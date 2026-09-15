# forecast-edge

A calibration-first political forecasting system feeding prediction markets. The claim under test is narrow and falsifiable: that a well-informed individual can beat the market price's own Brier score on thin political markets, often enough and reliably enough to survive fees, capital lock-up, and the multiple-testing correction his own search procedure demands. Manifold is the unpaid laboratory. Kalshi is where capital goes only after the record justifies it.

This project is not "beat prediction markets." It is "build the apparatus that can tell whether this edge exists, and probably find out it doesn't, cheaply, before capital." That sentence is here so optimism cannot relabel it in November.

## Run
- Install: `./init.sh install`
- Verify: `./init.sh verify`
- Start:  `./init.sh start`  (records a forecast to the append-only journal)

## Where state lives
- `PROGRESS.md` — session state, current priority, blockers. Read this first.
- `forecast_ledger.json` — the work ledger. A build unit reaches `passing` only when its verification command exits 0; a thesis reaches a terminal state only when an independent evaluator says so.
- `HARNESS/forecasting-profile.md` — the inline `trading` profile, second-project edition.
- `HARNESS/verification-traps.md` — the ten named ways this domain lies to you.
- `HARNESS/clean-state-checklist.md` — run before ending any session.
- `docs/decisions/` — the ADRs. Read before changing a structural choice.
- `docs/preregistration/` — pinned metrics, committed before results are seen. Git ordering is the proof.

## Hard constraints (MUST / MUST NOT — non-negotiable)

1. **MUST NOT place a real-money order from code.** No function in this repo submits to Kalshi or any paid venue. The `paper` to `live` transition is a human decision with recorded evidence, never an agent's.
2. **MUST NOT size a position on an unmeasured edge.** `sizing.kelly` raises unless handed a passed-gate flag. With an unmeasured edge the Kelly fraction is zero; this is arithmetic, not caution.
3. **MUST validate forward only.** No thesis is ever tested by having an agent forecast an already-resolved question. Resolutions are on the web and agents find them; this is documented behavior, not a hypothetical. A backtested forecast is contaminated by default.
4. **MUST record the market price at forecast time, and never let a later price touch a scoring path.** The closing price is the most predictive number available and does not exist when you forecast. If it reaches a model input or a comparison, the validation is decorative.
5. **MUST treat the journal as append-only.** Forecasts are chained by hash. A revision is a new record, never an edit. There is no `--force`.
6. **MUST cluster by correlated-event group, never by forecast.** Forty House races loading on one national environment are not forty observations. This same error inflates apparent sample size, position size, and model confidence simultaneously, in the same direction.
7. **MUST compare against the market price using a nested-model test.** Your forecast is the market plus an adjustment; a standard test on nested models almost never rejects even when the edge is real. Clark-West, one-sided.
8. **MUST NOT let a generator grade its own work.** An independent evaluator with a fresh context audits against the pre-registered metric. A model reviewing its own output with no new information is a second sample, not a check.
9. **MUST verify research claims against re-retrieved source text, not against links resolving.** Links resolve far more often than the claims they are cited for are supported.
10. **MUST log every configuration evaluated, including abandoned ones**, and report effective N for correlated trials. An unreported trial count makes overfitting risk unassessable.
11. **MUST record a new best only on an improvement exceeding the ladder threshold**, and round reported scores to that threshold. Repeated holdout checks manufacture signal at a rate proportional to the square root of check count over sample size.
12. **MUST maintain the disclosure log as a publishable artifact**, current at the moment any related piece goes out. A disclosure log that can be quietly revised is not a disclosure log.
13. MUST work one build unit at a time (WIP=1). Only one unit is `active`.
14. MUST record evidence (commit SHA, test output, or evaluator verdict) when a unit reaches its terminal state.
15. MUST run the clean-state checklist before ending a session, and update `PROGRESS.md`.

## The base rate, kept in view

The market price already aggregates everyone else's information, including people who do this full time with more capital and better data. Most people who believe they beat it are measuring variance. A positive result is the thing to disbelieve until it survives forward-only scoring, event-clustered inference, and a trial count you actually wrote down.

## Deeper docs (load on demand)
- `docs/decisions/0001-trading-profile-second-project.md` — why this repo triggers extraction of `templates/trading/`.
- `docs/decisions/0002-forward-only-validation.md` — the answer-key leakage argument, and why backtesting is barred.
- `journal/record.py` — F01, the append-only hash-chained forecast journal. The thing that makes every later claim honest.
