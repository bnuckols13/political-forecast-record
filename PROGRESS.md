# PROGRESS

Repo: `~/forecast-edge` (published as `bnuckols13/political-forecast-record`)

## The three commands
- `./init.sh install` — `python -m pip install -r requirements.txt`
- `./init.sh verify` — `python -m journal.record --check && python -m pytest -q`
- `./init.sh start` — record a forecast
- `python check.py` — the public verifier, runs from published files alone

## Current priority (WIP=1)

**F03 — Manifold API client.** F01 is `passing`. Nothing can be forecast until there is a live market and a live price to record beside it.

## The clock

Election day is Tuesday 2026-11-03. As of 2026-09-15 that is 49 days. Calibration data is a decaying asset: a day without a recorded probability is a day of calibration permanently lost, and forward-only validation means there is no way to make it up later. Forecasting starts before the apparatus is finished, on purpose.

The earliest an honest verdict can exist is January 2027. Anything faster is the bar moving.

## Blockers

- **F05 has not run.** It is a kill-gate and needs no data. If a detectable Brier edge requires more clustered observations than a cycle can produce, the correct output is a refusal ADR, not an apparatus. Run it before building anything downstream of F02.
- **The private journal has no backup.** `data/forecasts/` is gitignored and local-only. Losing it does not invalidate published commitments, but it makes every sealed forecast permanently unrevealable, which would destroy the record's value while leaving its skeleton intact. Needs a private mirror or encrypted backup before real volume accrues.
- **Venue research is incomplete.** Two research threads died on a session rate limit: Manifold's current mana/sweepcash status and whether real money is reachable there, Kalshi's fees and API and Pennsylvania availability, cross-venue spreads, and capital-efficiency math on long-dated contracts. F03 can be built against the public Manifold API regardless; F13 stays blocked.
- **Kalshi's legal status is live litigation.** A district court vacated the CFTC order barring political event contracts; the CFTC filed an emergency stay motion 2026-09-06. Arizona and Connecticut enforcement actions are in progress with the CFTC suing the states. This is a position-sizing consideration for later, not a blocker now.

## Running log

**2026-09-15** — Repo genesis. Harness primitives installed: `AGENTS.md` (15 constraints), `forecast_ledger.json` (15 build units, 1 thesis), `init.sh`, `HARNESS/`, `docs/decisions/`.

F01 built and `passing`. Append-only hash-chained forecast journal, stdlib only. 28 tests. Mutation-tested three ways before accepting the green: weakening the close-time guard, relaxing the certainty check, and severing the chain link each fail a specific test.

Commit-reveal publication added on top of F01 after the decision to publish. The naive version leaked: question and market price are observable on the venue and the probability is one of ~999 values, so a published digest could be brute-forced in under a second. Fixed with 128 bits of withheld per-record randomness, published at reveal. `tests/test_publish.py` includes the attacker simulation.

`check.py` written as the public verifier. Reads `public/` only, needs no credentials or network.

44 tests passing. Nothing has been forecast yet: F03 does not exist, and fabricating a forecast to have something in the journal would poison the record it is designed to protect.
