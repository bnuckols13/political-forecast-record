#!/usr/bin/env python3
"""Verify the published forecast record. Run: python check.py

This reads only what is in `public/`. It needs no private data, no network and
no credentials, so anyone can run it against a fresh clone and reach the same
verdict I do.

What it proves, and what it does not.

  PROVES  Each revealed forecast recomputes to the digest that was published at
          forecast time, so no revealed forecast was edited after the fact.

  PROVES  The commitments form an unbroken chain, so no forecast was inserted,
          removed or reordered. This is the part that matters: a self-reported
          track record is worthless if the author can drop the bad calls, and a
          chain makes selective disclosure detectable.

  PROVES  Every revealed forecast was committed before it resolved.

  DOES NOT PROVE  that the private journal contains nothing else. It proves the
          published chain is complete and intact; a forecast never committed at
          all leaves no trace here. Nothing short of a trusted timestamping
          service fixes that, and I am not claiming otherwise.

Exit status is 0 when the record verifies and 1 when it does not.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from journal.record import GENESIS_PREV, digest  # noqa: E402
from journal.publish import read_chain, read_revealed  # noqa: E402


def check_chain(chain: list[dict]) -> list[str]:
    """Every commitment must point at the one before it."""
    problems: list[str] = []
    expected_prev = GENESIS_PREV
    for position, entry in enumerate(chain, start=1):
        missing = [f for f in ("id", "created_utc", "hash", "prev") if f not in entry]
        if missing:
            problems.append(f"commitment #{position}: missing {', '.join(missing)}")
            return problems
        if entry["prev"] != expected_prev:
            problems.append(
                f"{entry['id']}: breaks the chain. It commits to "
                f"{entry['prev'][:12]}... but the preceding commitment is "
                f"{expected_prev[:12]}.... A forecast was inserted, removed or reordered."
            )
        expected_prev = entry["hash"]
    return problems


def check_reveals(chain: list[dict], revealed: list[dict]) -> list[str]:
    """Every revealed record must recompute to its published commitment."""
    problems: list[str] = []
    committed = {entry["id"]: entry for entry in chain}

    for record in revealed:
        forecast_id = record.get("id", "<no id>")
        entry = committed.get(forecast_id)
        if entry is None:
            problems.append(
                f"{forecast_id}: revealed but never committed. A forecast cannot be "
                "added to the record after the fact."
            )
            continue

        try:
            recomputed = digest(record)
        except KeyError as exc:
            problems.append(f"{forecast_id}: revealed record is missing field {exc}")
            continue

        if recomputed != entry["hash"]:
            problems.append(
                f"{forecast_id}: revealed content hashes to {recomputed[:12]}... but "
                f"{entry['hash'][:12]}... was published on {entry['created_utc']}. "
                "This forecast was changed between recording and reveal."
            )

        if record.get("resolved_utc", "") <= entry["created_utc"]:
            problems.append(
                f"{forecast_id}: resolved_utc {record.get('resolved_utc')} is not after "
                f"created_utc {entry['created_utc']}."
            )

        if record.get("outcome") not in (0, 1):
            problems.append(f"{forecast_id}: outcome must be 0 or 1")

    return problems


def scoreboard(revealed: list[dict]) -> None:
    """Brier against the market price, on revealed forecasts only."""
    scored = [r for r in revealed if r.get("outcome") in (0, 1)]
    if not scored:
        print("\nNo resolved forecasts yet. Nothing to score.")
        return

    mine = sum((r["p"] - r["outcome"]) ** 2 for r in scored) / len(scored)
    market = sum((r["market_p"] - r["outcome"]) ** 2 for r in scored) / len(scored)
    clusters = {r.get("cluster", "?") for r in scored}

    print(f"\nResolved forecasts: {len(scored)} across {len(clusters)} event cluster(s)")
    print(f"  Brier, mine   {mine:.4f}")
    print(f"  Brier, market {market:.4f}   (lower is better)")
    print(f"  Difference    {market - mine:+.4f}")
    print(
        "\n  Read this as a running tally, not as evidence of an edge. The unit of\n"
        "  independence is the event cluster, not the forecast, and a handful of\n"
        "  clusters cannot separate skill from variance. The pre-registered test in\n"
        "  docs/preregistration/ is the only thing that settles it."
    )


def main() -> int:
    chain = read_chain(REPO / "public")
    revealed = read_revealed(REPO / "public")

    print(f"Commitments published: {len(chain)}")
    print(f"Forecasts revealed:    {len(revealed)}")
    print(f"Still sealed:          {len(chain) - len(revealed)}")

    problems = check_chain(chain) + check_reveals(chain, revealed)

    if problems:
        print(f"\nFAIL: {len(problems)} problem(s) with the published record:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    if chain:
        print(f"\nOK: chain intact, tip {chain[-1]['hash'][:12]}...")
    else:
        print("\nOK: no forecasts published yet.")
    scoreboard(revealed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
