"""F01 - the append-only, hash-chained forecast journal.

Stdlib only, on purpose. This is the one thing that must run every day, and no
dependency gets to break it.

Why a hash chain rather than a plain log: the whole project rests on the claim
that a forecast was recorded *before* the outcome was known. A file you can
quietly edit proves nothing. Each record commits to the previous record's hash,
so altering any earlier forecast invalidates every record after it, and
`verify()` says so.

Two invariants carry most of the weight:

  1. A forecast may not be written for a market whose close time has passed.
     Forward-only validation is the project's central discipline; an agent asked
     to forecast a resolved question will find the resolution.

  2. The market price at forecast time is recorded *with* the forecast. That
     price is the benchmark S01 is scored against, and embedding it here is what
     stops a later price from silently reaching a scoring path. The closing
     price is the most predictive number available and does not exist yet.

A revision is a new append, never an edit. Updating often on small evidence is
good forecasting practice; mutating the record is not.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

GENESIS_PREV = "0" * 64
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "forecasts"

# Fields that make up a record's identity, in canonical order. "hash" is excluded
# because it is the digest of everything else.
#
# "nonce" is what makes the public commitment actually hiding. Without it the
# scheme leaks: the question and the market price are observable on the venue,
# and p is one of about 999 values, so anyone holding the published hash could
# brute-force the whole space in well under a second and read a live position.
# 128 bits of withheld randomness puts that out of reach. It is published only
# at reveal, when hiding no longer matters and verification does.
_SIGNED_FIELDS = (
    "id",
    "created_utc",
    "venue",
    "market_id",
    "question",
    "p",
    "market_p",
    "closes_utc",
    "cluster",
    "rationale",
    "nonce",
    "prev",
)

# The only fields that go public at forecast time. Everything else waits for
# resolution. This tuple is the privacy boundary; widening it leaks edge.
_COMMITMENT_FIELDS = ("id", "created_utc", "hash", "prev")


class JournalError(Exception):
    """Raised when a write would violate an invariant, or the chain is broken."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(value: str, field: str) -> datetime:
    """Parse an ISO-8601 UTC stamp, accepting a trailing Z."""
    if not isinstance(value, str) or not value:
        raise JournalError(f"{field} must be a non-empty ISO-8601 UTC string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise JournalError(f"{field} is not valid ISO-8601: {value!r}") from exc
    if parsed.tzinfo is None:
        raise JournalError(f"{field} must carry a timezone (use ...Z): {value!r}")
    return parsed.astimezone(timezone.utc)


def _fmt_utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical(record: dict[str, Any]) -> str:
    """The exact byte-string a record's hash is taken over.

    Sorted keys and tight separators so the digest does not depend on how the
    dict happened to be built. `ensure_ascii=False` with an explicit UTF-8
    encode at write time: this box has produced cp1252 corruption before, and a
    mangled byte breaks the chain rather than merely looking wrong.
    """
    subset = {k: record[k] for k in _SIGNED_FIELDS}
    return json.dumps(subset, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(record: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(record).encode("utf-8")).hexdigest()


def _month_files(data_dir: Path) -> list[Path]:
    """Journal files in chronological order. Names are YYYY-MM so sort is date order."""
    if not data_dir.exists():
        return []
    return sorted(data_dir.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].jsonl"))


def read_all(data_dir: Path | None = None) -> Iterator[dict[str, Any]]:
    """Yield every record in write order, across month files."""
    directory = data_dir or DATA_DIR
    for path in _month_files(directory):
        with path.open("r", encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise JournalError(f"{path.name}:{lineno} is not valid JSON") from exc


def tip(data_dir: Path | None = None) -> str:
    """Hash of the most recent record, or the genesis sentinel if empty."""
    last = GENESIS_PREV
    for record in read_all(data_dir):
        last = record.get("hash", GENESIS_PREV)
    return last


def _validate_probability(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise JournalError(f"{field} must be a number, got {type(value).__name__}")
    probability = float(value)
    # Strict inequality on both ends. A stated 0 or 1 is a claim of certainty,
    # carries infinite log score when wrong, and is never honest about an
    # unresolved political question.
    if not 0.0 < probability < 1.0:
        raise JournalError(
            f"{field} must lie strictly between 0 and 1, got {probability}. "
            "Certainty is not a forecast."
        )
    return probability


def write(
    *,
    venue: str,
    market_id: str,
    question: str,
    p: float,
    market_p: float,
    closes_utc: str,
    cluster: str,
    rationale: str = "",
    data_dir: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Append one forecast to the journal and return the stored record.

    Raises JournalError rather than writing anything when an invariant fails.
    """
    directory = data_dir or DATA_DIR
    created = (now or _utcnow()).astimezone(timezone.utc)

    for field, value in (
        ("venue", venue),
        ("market_id", market_id),
        ("question", question),
        ("cluster", cluster),
    ):
        if not isinstance(value, str) or not value.strip():
            raise JournalError(f"{field} is required and must be a non-empty string")

    probability = _validate_probability(p, "p")
    market_probability = _validate_probability(market_p, "market_p")

    closes = _parse_utc(closes_utc, "closes_utc")
    if closes <= created:
        raise JournalError(
            f"closes_utc ({_fmt_utc(closes)}) is not after created_utc "
            f"({_fmt_utc(created)}). A forecast recorded at or after close is not a "
            "forecast; forward-only validation is the whole discipline here."
        )

    record: dict[str, Any] = {
        "id": f"f_{uuid.uuid4().hex[:12]}",
        "created_utc": _fmt_utc(created),
        "venue": venue.strip(),
        "market_id": market_id.strip(),
        "question": question.strip(),
        "p": probability,
        "market_p": market_probability,
        "closes_utc": _fmt_utc(closes),
        "cluster": cluster.strip(),
        "rationale": rationale.strip(),
        "nonce": secrets.token_hex(16),
        "prev": tip(directory),
    }
    record["hash"] = digest(record)

    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{created.strftime('%Y-%m')}.jsonl"
    line = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")

    return record


def commitment(record: dict[str, Any]) -> dict[str, Any]:
    """The public half of a forecast: proof it existed, without its content.

    Published at forecast time. Carries the timestamp and the digest, so the
    claim "this forecast was made on this date and has not changed since" is
    checkable by anyone, while the question, the probability and the reasoning
    stay private until the market resolves.
    """
    missing = [f for f in _COMMITMENT_FIELDS if f not in record]
    if missing:
        raise JournalError(f"cannot build commitment, missing {', '.join(missing)}")
    return {field: record[field] for field in _COMMITMENT_FIELDS}


def verify(data_dir: Path | None = None) -> list[str]:
    """Walk the chain. Return a list of problems; empty means intact."""
    problems: list[str] = []
    expected_prev = GENESIS_PREV
    count = 0

    for record in read_all(data_dir):
        count += 1
        where = record.get("id", f"record #{count}")

        missing = [f for f in (*_SIGNED_FIELDS, "hash") if f not in record]
        if missing:
            problems.append(f"{where}: missing field(s) {', '.join(missing)}")
            return problems  # chain position is no longer meaningful

        if record["prev"] != expected_prev:
            problems.append(
                f"{where}: prev is {record['prev'][:12]}... but the preceding "
                f"record hashes to {expected_prev[:12]}.... A record was inserted, "
                "removed, or reordered."
            )

        recomputed = digest(record)
        if recomputed != record["hash"]:
            problems.append(
                f"{where}: stored hash {record['hash'][:12]}... does not match "
                f"recomputed {recomputed[:12]}.... This record was edited after writing."
            )

        expected_prev = record["hash"]

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="journal.record",
        description="Append-only hash-chained forecast journal (F01).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify chain integrity; exit non-zero if any record was altered",
    )
    parser.add_argument("--venue", default="manifold")
    parser.add_argument("--market-id")
    parser.add_argument("--question")
    parser.add_argument("--p", type=float, help="your probability, strictly 0 to 1")
    parser.add_argument("--market-p", type=float, help="market price at forecast time")
    parser.add_argument("--closes", help="market close, ISO-8601 UTC, e.g. 2026-11-03T05:00:00Z")
    parser.add_argument("--cluster", help="correlated-event group, e.g. us-house-2026")
    parser.add_argument("--rationale", default="")
    args = parser.parse_args(argv)

    if args.check:
        problems = verify()
        total = sum(1 for _ in read_all())
        if problems:
            print(f"FAIL: journal chain broken ({len(problems)} problem(s)):")
            for problem in problems:
                print(f"  - {problem}")
            return 1
        print(f"ok: {total} forecast(s), chain intact, tip {tip()[:12]}...")
        return 0

    required = (args.market_id, args.question, args.p, args.market_p, args.closes, args.cluster)
    if any(value is None for value in required):
        parser.error(
            "recording a forecast needs --market-id --question --p --market-p "
            "--closes --cluster (or pass --check)"
        )

    try:
        record = write(
            venue=args.venue,
            market_id=args.market_id,
            question=args.question,
            p=args.p,
            market_p=args.market_p,
            closes_utc=args.closes,
            cluster=args.cluster,
            rationale=args.rationale,
        )
    except JournalError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1

    edge = record["p"] - record["market_p"]
    print(f"recorded {record['id']}  p={record['p']:.3f}  market={record['market_p']:.3f}  edge={edge:+.3f}")
    print(f"  cluster={record['cluster']}  closes={record['closes_utc']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
