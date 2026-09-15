# 0004 — The midterms are one observation

Status: accepted, 2026-09-15
Supersedes: the sprint framing in the original plan

## Context

The plan this repository was built from treated 2026-11-03 as the catalyst: 49 days
to the midterms, forecast hard, get a first real calibration reading in November. F05
was supposed to confirm that was reachable.

It does not.

## What F05 found

Per forecast, the Brier difference against the market price is

    d = (m - Y)^2 - (p - Y)^2 = (m - p)(m + p - 2Y)

and with edge e = p - m, assuming you are perfectly calibrated and the market carries
the error, E[d] = e^2 with sd[d] = 2|e| sqrt(q(1-q)). Substituting into
N = (t sd / mean)^2 and taking q = 0.5 as the conservative case:

    N = t^2 / e^2

Independent observations required, at t = 2.0:

| edge | independent observations |
|---|---|
| 3%  | 4,444 |
| 5%  | 1,600 |
| 10% | 400 |
| 15% | 178 |

Those are INDEPENDENT observations. Applying the design effect
DEFF = 1 + (k-1)*rho, a cluster of correlated forecasts contributes far fewer.

Every House race on election night resolves at once, under one national polling
environment, decided substantially by one shared error term. That is intra-cluster
correlation close to 1.0. At rho = 1.0, a cluster contributes exactly one observation
regardless of how many forecasts it holds.

**Four hundred forecasts on four hundred House races buy approximately one
observation, not four hundred.**

At a 5% edge and rho = 0.9, S01 needs on the order of 1,450 clusters. There is one
midterm election.

## Decision

Three changes.

**1. The midterms are not the evidence.** They are calibration practice, the first
substantial batch in the public record, and the place money would be made if an edge
exists. They are not, and cannot be, the test of whether it exists.

**2. Breadth is the mechanism, not a nicety.** The denominator grows only through
unrelated questions resolving on different dates for different reasons. Twenty
forecasts across twenty unconnected topics are worth more evidentially than four
hundred forecasts on one election night. Wide scope on Manifold was justified in the
plan as calibration training; it is in fact the only route to a testable thesis.

**3. S01 narrows to markets where a large edge is plausible.** A 3% edge needs ~890
clusters and is unmeasurable in any realistic timeframe. A 10% edge needs ~80. So the
thesis is only ever testable where a 10-point disagreement with the price is
plausible, which means genuinely thin markets priced by few traders. On liquid
headline markets, any edge that exists is small enough to be permanently invisible.

## Consequences

The verdict date is no longer a date. It is a count: roughly 80 independent clusters
at a 10% edge, roughly 320 at 5%. When that count is reached depends on forecasting
breadth, not on the election calendar. January 2027 was a guess anchored to the wrong
event.

The plan's timeline section is wrong and should be read as superseded by this ADR.
