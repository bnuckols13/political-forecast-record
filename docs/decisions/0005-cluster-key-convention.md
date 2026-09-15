# 0005 — The cluster key convention

Status: accepted, 2026-09-15

## Context

Every journal record carries a `cluster` field. F05 made that field the unit of
evidence: significance is computed across clusters, never across forecasts. A
mislabelled cluster is therefore not untidiness, it is a wrong answer, and it is a
wrong answer with no symptom. Nothing raises. The number simply comes out wrong.

The convention has to be fixed once and applied mechanically, because deciding it
per forecast is how a denominator gets quietly inflated by the person it benefits.

## Decision

**A cluster is a set of outcomes that share a dominant common error term.**

If being wrong about one outcome makes you wrong about the others in the same
direction and for the same reason, they are one cluster.

Key format: `<iso2>-<year>-<body>`, lowercase and hyphenated. `nz-2026-general`,
`us-2026-midterms`, `fr-2027-presidential`. A key is stable forever once used,
because renaming one silently splits a record that was a single observation.

Applied:

- **Same cluster.** Every race on one national election night in one country.
  Multiple questions about a single race (winner, margin, seat count). Turnout
  and result questions for the same election.
- **Separate.** Different countries, even in the same week. Different election
  nights in one country separated by months. Process questions that do not
  resolve on a vote count.

## The judgement call, pinned

France 2027 holds a presidential election in April and a legislative in June. The
legislative follows the presidential and is heavily conditioned on it, but the
two are two months apart, have different electorates, and have diverged sharply
before.

Recorded as **two clusters**, with the dependence written into the watchlist note.

Treating them as one discards real information. Treating them as fully
independent overstates the denominator by exactly one. Separate is the more
aggressive choice, which is why the note matters and why this ADR exists rather
than the decision living in someone's head.

## Enforcement

`tests/test_clusters.py` checks uniqueness, key format, date sortability, that
every shortlist key resolves to a real watchlist entry, and that the France and
US/NZ decisions above still hold. None of those failures would surface on their
own.

The suite immediately earned this. It caught that `"2027-06"` sorts *before*
`"2027-06-06"` under naive string comparison, because a prefix sorts first, so a
month-only date jumps ahead of every dated election in its own month. France's
legislative election would have outranked Mexico's June 6th vote purely because
we know less about it. Resolved by `Election.sort_key`, which pads a month-only
date to mid-month: when only the month is known, the expected day is the middle
of it.

## Consequences

Cluster assignment is now a lookup rather than a judgement, for anything on the
watchlist. Off-watchlist forecasts still need a human decision, and the rule at
the top of this document is what that decision appeals to.
