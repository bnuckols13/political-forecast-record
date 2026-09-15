# 0003 — Commit-reveal publication

Status: accepted, 2026-09-15

## Context

The record is worth publishing: a self-reported forecasting track record proves
nothing, because the person keeping it chooses what to mention. Publishing it live is
worth money to other people: a reader who sees an open position and a stated edge can
take it before the author does, and the better the record gets the more people watch.

Both are true at once. Publishing everything sacrifices the edge; publishing nothing
sacrifices the only thing that would make the record citable.

## Decision

Commit-reveal. At forecast time the public repository receives a digest and a
timestamp. After the market resolves it receives the full record and the outcome.
`check.py` confirms the revealed content hashes to the digest published earlier.

## The detail that nearly broke it

A hash commits to content. It only *hides* content that is hard to guess.

The question and the market price are both publicly observable on the venue. The
probability is one of roughly 999 values. An attacker holding the published digest
could therefore enumerate the entire space in well under a second and read the live
position. The commitment would have looked like discipline while providing none.

Every record now carries 128 bits of randomness withheld until reveal.
`tests/test_publish.py::test_guessing_every_probability_does_not_recover_the_hash`
runs the attack and asserts it fails.

## What the chain buys beyond timestamps

Completeness. Commitments are linked, so a forecast that resolved badly cannot be
dropped without breaking every commitment after it. Selective disclosure becomes
detectable, which is the only property that makes a self-reported record worth
anything.

## What is not claimed

The chain proves the published record is intact and complete. It cannot prove the
private journal holds nothing else, because a forecast never committed leaves no
trace. Closing that gap needs a third-party timestamping service. The README says so
rather than implying otherwise.
