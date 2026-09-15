# 0001 — The `trading` profile, second project

Status: accepted, 2026-09-15

## Context

`~/harness` ships three templates: code, investigation, prose. None fits a project
whose unit of work is a falsifiable claim about a market. `~/crypto-trading` proved a
fourth profile inline (ADR 0001 there), and `~/harness/orchestration/registry.md`
records the extraction condition verbatim: extract into `templates/trading/` once
proven against a second trading project.

This is that second project.

## Decision

Run the `trading` profile inline here as well, and treat extraction to
`~/harness/templates/trading/` as now owed rather than hypothetical.

The mapping from crypto-trading is close to one-to-one:

| crypto-trading | here |
|---|---|
| bar | forecast |
| trade | market position |
| cluster by token | cluster by correlated-event group |
| fees + borrow | fees + capital lock-up to resolution |
| beat BTC buy-and-hold net of costs | beat the market price's Brier score |

## What this project contributes that crypto-trading structurally cannot

Three things, and they are the reason extraction should wait for this repo rather
than happening from crypto-trading alone.

1. **Forward-only validation under answer-key leakage.** Crypto backtests on price
   history, which is fixed and public and carries no answer to find. A forecasting
   agent asked about a resolved question will search for and find the resolution.
   That is a documented behaviour, not a hypothetical. It bars backtesting entirely
   and forces a discipline crypto never needed.

2. **An environment that verifies itself.** Crypto-trading had to construct an
   independent evaluator to approximate an external check. Here the market resolves
   on a schedule and publishes the answer. The verifier is free, automatic, and
   cannot be argued with.

3. **Claim-level research verification.** Forecasts are fed by research, and research
   agents produce working links far more often than supported claims. The defence
   generalises to every investigation in `~/journalism-master`.

## Consequences

The three items already owed to `templates/trading/` by crypto-trading still stand:
clustered/independent-N named in the pre-registration, a metric-contract check
(returns-series not equity-levels), and batch-endpoint/incremental-cache guidance for
large fetches. This project adds a fourth: forward-only validation where an agent can
reach the answer key.
