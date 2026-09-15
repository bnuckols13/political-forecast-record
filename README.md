# political-forecast-record

A timestamped, tamper-evident record of political forecasts, published so that the claim "I called this in September" can be checked rather than believed.

**Verify the whole record:**

```bash
python check.py
```

That command needs no credentials, no network, and no data beyond what is in this repository. It recomputes every published digest and walks the commitment chain. If a forecast was edited, dropped, reordered, or added after the fact, it exits non-zero and says which one.

---

## Why this exists

Self-reported forecasting records are close to worthless, for a reason that has nothing to do with honesty. The person keeping the record chooses which calls to mention. Even with no intent to deceive, memory and selection do the work: the confident call that landed is vivid, the hedged one that missed is not. A track record you can edit is a track record that proves nothing.

Three properties fix that, and this repository is built to have all three.

**Timestamped.** Each forecast is committed publicly when it is made, before the outcome is known.

**Sealed while live.** The commitment publishes a digest and a date, not the position. Forecasts are worth money while a market is open, so the content stays private until the market resolves. A reader cannot trade against an open position, and the author cannot revise one.

**Complete.** Commitments are chained: each one commits to the digest of the previous. Removing a forecast that went badly breaks every commitment after it. Selective disclosure is detectable, which is the only reason to give a self-reported record any weight at all.

## How the commit-reveal works

At forecast time, one line goes into [`public/chain.jsonl`](public/chain.jsonl):

```json
{"id":"f_...","created_utc":"2026-09-15T18:22:31Z","hash":"9f3c...","prev":"41ab..."}
```

That is the entire public footprint of a live forecast. The question, the probability, the market price and the reasoning are not in it.

Each record also carries 128 bits of withheld randomness. Without it the scheme would leak: the question and the market price are observable on the venue and the probability is one of about a thousand values, so anyone holding the digest could search the whole space in under a second and read the position. The nonce puts that out of reach and is published at reveal alongside everything else.

After the market resolves, the full record is appended to [`public/revealed.jsonl`](public/revealed.jsonl) with its outcome. `check.py` confirms it hashes to the digest published weeks earlier.

## What this proves, and what it does not

Proves that every revealed forecast is byte-identical to what was committed on the stated date. Proves that the published chain has no gaps. Proves that no revealed forecast resolved before it was recorded.

Does not prove that the private journal holds nothing else. The chain shows that what was published is complete and intact; a forecast never committed at all leaves no trace here. Nothing short of a third-party timestamping service closes that gap, and this record does not claim otherwise.

## Scoring

The benchmark is the market price at the moment of the forecast, recorded inside the forecast itself. Beating it is the definition of an edge, and failing to beat it is the expected outcome: a market price already aggregates the information of everyone trading it, including people who do this full time.

`check.py` prints a running Brier comparison once forecasts resolve. That tally is not evidence. The unit of independence is the correlated-event group rather than the individual forecast, because forty House races loading on one national environment are not forty observations. The pre-registered test in [`docs/preregistration/`](docs/preregistration/) is the only thing that settles whether an edge exists, and it is committed to git before any result is seen so the ordering is checkable.

## Disclosure

I report on campaign finance and political ethics. I take positions in political prediction markets, and I disclose rather than abstain. [`public/disclosure.md`](public/disclosure.md) is the standing record of positions, append-only and current at the moment any related piece publishes. If you find a conflict I have not disclosed, that is a failure worth telling me about.

## Layout

| Path | What it is |
|---|---|
| `check.py` | The verifier. Start here. |
| `public/chain.jsonl` | Commitments, one per forecast, written when the forecast is made |
| `public/revealed.jsonl` | Full records with outcomes, written after resolution |
| `journal/` | The append-only journal and the commit-reveal publisher |
| `scoring/` | Brier score with the calibration and resolution decomposition |
| `inference/` | Event-clustered significance testing and the sufficiency pre-flight |
| `docs/preregistration/` | Metrics pinned before results are seen |
| `docs/decisions/` | Why the structural choices are what they are |
| `AGENTS.md` | The operating constraints this project holds itself to |

The private journal is not in this repository and never will be. Only commitments and reveals are published.

## License

Code under MIT. The forecast record itself is CC BY 4.0: reuse it, check it, argue with it, cite it.

---

Lena Rose Williams (she/her)
