"""Commit-reveal publication for the forecast journal.

The private journal (`data/forecasts/`) holds full records and never leaves this
machine. Two public artifacts are derived from it:

  public/chain.jsonl     one commitment per forecast, written at forecast time.
                         {id, created_utc, hash, prev} and nothing else.

  public/revealed.jsonl  the full record plus its outcome, written after the
                         market resolves.

The point of the split is that a live forecast is worth money and a resolved one
is worth credibility. Publishing the hash immediately makes the timestamp
checkable by anyone; withholding the content until resolution stops a reader
from trading against a position while it is still open.

What a skeptic gets from this that plain publishing cannot give them: proof of
*completeness*. Because the commitments are chained, a forecast that went badly
cannot be dropped from the record without breaking every commitment after it.
Selective disclosure is detectable, which is the only reason a self-reported
track record deserves any weight at all.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from journal.record import (
    JournalError,
    _parse_utc,
    commitment,
    digest,
    read_all,
)

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
CHAIN_FILE = "chain.jsonl"
REVEALED_FILE = "revealed.jsonl"


def _dump(record: dict[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise JournalError(f"{path.name}:{lineno} is not valid JSON") from exc


def read_chain(public_dir: Path | None = None) -> list[dict[str, Any]]:
    return list(_read_jsonl((public_dir or PUBLIC_DIR) / CHAIN_FILE))


def read_revealed(public_dir: Path | None = None) -> list[dict[str, Any]]:
    return list(_read_jsonl((public_dir or PUBLIC_DIR) / REVEALED_FILE))


def sync_commitments(
    data_dir: Path | None = None, public_dir: Path | None = None
) -> list[dict[str, Any]]:
    """Append commitments for any private forecasts not yet committed publicly.

    Idempotent and append-only. Existing lines are never rewritten, so a
    published commitment cannot be quietly changed once it is out.
    """
    destination = public_dir or PUBLIC_DIR
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / CHAIN_FILE

    already = {entry["id"] for entry in _read_jsonl(path)}
    added: list[dict[str, Any]] = []

    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for record in read_all(data_dir):
            if record["id"] in already:
                continue
            entry = commitment(record)
            handle.write(_dump(entry) + "\n")
            added.append(entry)

    return added


def reveal(
    forecast_id: str,
    *,
    outcome: int,
    resolved_utc: str,
    data_dir: Path | None = None,
    public_dir: Path | None = None,
) -> dict[str, Any]:
    """Publish the full record for one resolved forecast.

    Refuses to reveal a forecast with no recorded outcome. Revealing early would
    hand a reader the live position, which is the exact thing the commitment
    exists to prevent.
    """
    if outcome not in (0, 1):
        raise JournalError(f"outcome must be 0 or 1, got {outcome!r}")

    destination = public_dir or PUBLIC_DIR
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / REVEALED_FILE

    if any(entry["id"] == forecast_id for entry in _read_jsonl(path)):
        raise JournalError(f"{forecast_id} is already revealed; reveals are append-only")

    record = next(
        (r for r in read_all(data_dir) if r["id"] == forecast_id),
        None,
    )
    if record is None:
        raise JournalError(f"no forecast with id {forecast_id} in the private journal")

    resolved = _parse_utc(resolved_utc, "resolved_utc")
    created = _parse_utc(record["created_utc"], "created_utc")
    if resolved <= created:
        raise JournalError(
            f"resolved_utc ({resolved_utc}) is not after the forecast was recorded "
            f"({record['created_utc']}). An outcome cannot precede the prediction."
        )

    entry = dict(record)
    entry["outcome"] = outcome
    entry["resolved_utc"] = resolved.strftime("%Y-%m-%dT%H:%M:%SZ")

    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(_dump(entry) + "\n")

    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="journal.publish",
        description="Commit-reveal publication for the forecast journal.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("sync", help="publish commitments for any new private forecasts")

    reveal_parser = sub.add_parser("reveal", help="publish a resolved forecast in full")
    reveal_parser.add_argument("forecast_id")
    reveal_parser.add_argument("--outcome", type=int, required=True, choices=[0, 1])
    reveal_parser.add_argument("--resolved", required=True, help="ISO-8601 UTC")

    args = parser.parse_args(argv)

    try:
        if args.command == "sync":
            added = sync_commitments()
            total = len(read_chain())
            if added:
                print(f"published {len(added)} new commitment(s); chain now {total}")
                for entry in added:
                    print(f"  {entry['id']}  {entry['created_utc']}  {entry['hash'][:12]}...")
            else:
                print(f"nothing new; chain holds {total} commitment(s)")
            return 0

        entry = reveal(
            args.forecast_id, outcome=args.outcome, resolved_utc=args.resolved
        )
        hit = "YES" if entry["outcome"] == 1 else "NO"
        print(f"revealed {entry['id']}  p={entry['p']:.3f}  market={entry['market_p']:.3f}  outcome={hit}")
        return 0
    except JournalError as exc:
        print(f"REFUSED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
