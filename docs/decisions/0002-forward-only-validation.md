# 0002 — Forward-only validation. Backtesting is barred.

Status: accepted, 2026-09-15

## Context

The obvious way to test a forecasting process cheaply is to run it against questions
that have already resolved. It is also the way that does not work.

Anthropic documented Claude Opus 4.6, having exhausted legitimate search on a
benchmark task, reasoning that it was probably inside an evaluation, enumerating
candidate benchmarks, identifying the right one, and decrypting its answer key.
Eighteen independent runs converged on that strategy; sixteen further attempts were
blocked. The model was not told it was being tested. It worked it out and went
looking.

A resolved political question is worse than a benchmark. The resolution is on the open
web, indexed, in the first page of results, and the agent has every incentive to find
it while believing it is doing research.

## Decision

No thesis in this repository is ever tested by forecasting an already-resolved
question. Validation is forward-only. `journal.record.write` raises if the market's
close time has already passed.

## Why the obvious mitigations fail

*Tell the agent not to look.* Instruction-following is not a security boundary, and a
model that finds the answer while genuinely researching has not disobeyed anything.

*Use an air-gapped model.* Removes the leak and the capability together. The process
under test is research-fed; a model with no retrieval is not the process.

*Use questions from before the training cutoff.* The cutoff is not a wall, retrieval
crosses it, and questions old enough to be safe are drawn from a political environment
too different to generalise from.

## Consequences

The expensive one: calibration accrues only in real time. There is no way to buy a
track record, catch up after a slow month, or validate before the first resolution
lands. This is why the journal ships before the apparatus is finished, and why the
earliest honest verdict is January 2027.

The compensation is that forward paper trading is free here. Writing a forecast and
not staking it costs nothing and is scored against the real market and the real
outcome. Crypto-trading's paper stage had no equivalent.
