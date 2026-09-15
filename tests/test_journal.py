"""Tests for F01, the forecast journal.

The refusal tests matter more than the happy path. Every one of them encodes a
constraint from AGENTS.md, and each exists because the corresponding mistake is
invisible once made: a forecast backdated past a close, a stated certainty, or a
quietly edited record all look exactly like good data afterwards.

Hermetic. Every test writes to tmp_path and never touches data/forecasts/.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from journal.record import (
    GENESIS_PREV,
    JournalError,
    canonical,
    digest,
    read_all,
    tip,
    verify,
    write,
)

NOW = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)
LATER = "2026-11-03T05:00:00Z"


def _write(tmp_path, **overrides):
    kwargs = dict(
        venue="manifold",
        market_id="mkt-1",
        question="Will the incumbent hold PA-07?",
        p=0.62,
        market_p=0.55,
        closes_utc=LATER,
        cluster="us-house-2026",
        rationale="district-level fundamentals",
        data_dir=tmp_path,
        now=NOW,
    )
    kwargs.update(overrides)
    return write(**kwargs)


# --------------------------------------------------------------------------
# Refusals. These are the discipline.
# --------------------------------------------------------------------------


def test_refuses_forecast_on_already_closed_market(tmp_path):
    """Forward-only validation. A forecast at or after close is not a forecast."""
    with pytest.raises(JournalError, match="not after created_utc"):
        _write(tmp_path, closes_utc="2026-09-15T11:59:59Z")


def test_refuses_forecast_exactly_at_close(tmp_path):
    """Boundary: equal timestamps are a refusal, not a pass."""
    with pytest.raises(JournalError, match="not after created_utc"):
        _write(tmp_path, closes_utc="2026-09-15T12:00:00Z")


@pytest.mark.parametrize("bad", [0.0, 1.0, -0.1, 1.5])
def test_refuses_certainty_and_out_of_range(tmp_path, bad):
    with pytest.raises(JournalError, match="strictly between 0 and 1"):
        _write(tmp_path, p=bad)


@pytest.mark.parametrize("bad", [0.0, 1.0, 2.0])
def test_refuses_bad_market_price(tmp_path, bad):
    with pytest.raises(JournalError, match="strictly between 0 and 1"):
        _write(tmp_path, market_p=bad)


def test_refuses_boolean_probability(tmp_path):
    """bool is an int subclass in Python; True must not slip through as 1.0."""
    with pytest.raises(JournalError, match="must be a number"):
        _write(tmp_path, p=True)


@pytest.mark.parametrize("field", ["venue", "market_id", "question", "cluster"])
def test_refuses_missing_required_field(tmp_path, field):
    with pytest.raises(JournalError, match=f"{field} is required"):
        _write(tmp_path, **{field: "   "})


def test_refuses_naive_timestamp(tmp_path):
    with pytest.raises(JournalError, match="must carry a timezone"):
        _write(tmp_path, closes_utc="2026-11-03T05:00:00")


def test_nothing_is_written_when_a_write_is_refused(tmp_path):
    """A refusal must leave no trace. A partial write would corrupt the chain."""
    with pytest.raises(JournalError):
        _write(tmp_path, p=1.0)
    assert list(read_all(tmp_path)) == []
    assert tip(tmp_path) == GENESIS_PREV


# --------------------------------------------------------------------------
# Chain integrity
# --------------------------------------------------------------------------


def test_empty_journal_has_genesis_tip(tmp_path):
    assert tip(tmp_path) == GENESIS_PREV
    assert verify(tmp_path) == []


def test_first_record_points_at_genesis(tmp_path):
    record = _write(tmp_path)
    assert record["prev"] == GENESIS_PREV
    assert verify(tmp_path) == []


def test_records_chain_in_write_order(tmp_path):
    first = _write(tmp_path, market_id="mkt-1")
    second = _write(tmp_path, market_id="mkt-2")
    third = _write(tmp_path, market_id="mkt-3")

    assert second["prev"] == first["hash"]
    assert third["prev"] == second["hash"]
    assert tip(tmp_path) == third["hash"]
    assert verify(tmp_path) == []


def test_revision_is_an_append_not_an_edit(tmp_path):
    """Updating on new evidence is good practice; mutating the record is not."""
    first = _write(tmp_path, p=0.62)
    second = _write(tmp_path, p=0.71)

    stored = list(read_all(tmp_path))
    assert len(stored) == 2
    assert stored[0]["p"] == 0.62  # the original estimate survives untouched
    assert stored[1]["p"] == 0.71
    assert second["prev"] == first["hash"]
    assert verify(tmp_path) == []


def test_digest_matches_an_independently_computed_sha256(tmp_path):
    """Golden test: hash the canonical string by a separate path.

    This is the oracle. If digest() ever changes what it commits to, this fails
    even though the implementation remains self-consistent.
    """
    record = _write(tmp_path)
    expected = hashlib.sha256(canonical(record).encode("utf-8")).hexdigest()
    assert record["hash"] == expected
    assert len(record["hash"]) == 64


def test_canonical_form_ignores_key_insertion_order(tmp_path):
    record = _write(tmp_path)
    shuffled = {k: record[k] for k in reversed(list(record.keys()))}
    assert canonical(shuffled) == canonical(record)
    assert digest(shuffled) == digest(record)


# --------------------------------------------------------------------------
# Tamper detection. The reason the chain exists.
# --------------------------------------------------------------------------


def _rewrite_lines(tmp_path, transform):
    path = next(tmp_path.glob("*.jsonl"))
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    lines = transform(lines)
    path.write_text(
        "".join(
            json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
            for r in lines
        ),
        encoding="utf-8",
        newline="\n",
    )


def test_editing_an_earlier_forecast_is_caught(tmp_path):
    """The attack this whole design exists to stop: improving a past estimate."""
    _write(tmp_path, market_id="mkt-1", p=0.62)
    _write(tmp_path, market_id="mkt-2", p=0.40)

    def nudge_first(records):
        records[0]["p"] = 0.95  # with hindsight, claim a better call
        return records

    _rewrite_lines(tmp_path, nudge_first)

    problems = verify(tmp_path)
    assert problems, "an edited forecast must not verify"
    assert any("edited after writing" in p for p in problems)


def test_deleting_a_record_is_caught(tmp_path):
    """Quietly dropping a forecast that went badly."""
    _write(tmp_path, market_id="mkt-1")
    _write(tmp_path, market_id="mkt-2")
    _write(tmp_path, market_id="mkt-3")

    _rewrite_lines(tmp_path, lambda records: [records[0], records[2]])

    problems = verify(tmp_path)
    assert problems
    assert any("inserted, removed, or reordered" in p for p in problems)


def test_reordering_records_is_caught(tmp_path):
    _write(tmp_path, market_id="mkt-1")
    _write(tmp_path, market_id="mkt-2")

    _rewrite_lines(tmp_path, lambda records: [records[1], records[0]])

    problems = verify(tmp_path)
    assert problems
    assert any("inserted, removed, or reordered" in p for p in problems)


def test_forging_a_hash_to_match_an_edit_still_breaks_the_chain(tmp_path):
    """Recomputing the tampered record's own hash is not enough: the next
    record still commits to the old one."""
    _write(tmp_path, market_id="mkt-1", p=0.62)
    _write(tmp_path, market_id="mkt-2", p=0.40)

    def nudge_and_reseal(records):
        records[0]["p"] = 0.95
        records[0]["hash"] = digest(records[0])
        return records

    _rewrite_lines(tmp_path, nudge_and_reseal)

    problems = verify(tmp_path)
    assert problems
    assert any("inserted, removed, or reordered" in p for p in problems)


def test_missing_field_is_reported_not_crashed(tmp_path):
    _write(tmp_path)

    def strip_cluster(records):
        del records[0]["cluster"]
        return records

    _rewrite_lines(tmp_path, strip_cluster)

    problems = verify(tmp_path)
    assert problems
    assert any("missing field" in p for p in problems)


def test_chain_spans_month_boundaries(tmp_path):
    """Journal files roll monthly; the chain does not restart."""
    september = _write(tmp_path, market_id="sep", now=NOW)
    october = _write(tmp_path, market_id="oct", now=NOW + timedelta(days=20))

    names = sorted(p.name for p in tmp_path.glob("*.jsonl"))
    assert names == ["2026-09.jsonl", "2026-10.jsonl"]
    assert october["prev"] == september["hash"]
    assert verify(tmp_path) == []
