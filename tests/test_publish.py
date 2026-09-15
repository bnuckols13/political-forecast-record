"""Tests for commit-reveal publication.

The privacy tests are the ones that matter. A commitment scheme that leaks is
worse than no commitment at all, because it looks like discipline while handing
a reader the live position.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pytest

from check import check_chain, check_reveals
from journal.publish import read_chain, read_revealed, reveal, sync_commitments
from journal.record import JournalError, canonical, digest, write

NOW = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)
CLOSES = "2026-11-03T05:00:00Z"
RESOLVED = "2026-11-04T12:00:00Z"


@pytest.fixture
def dirs(tmp_path):
    private = tmp_path / "private"
    public = tmp_path / "public"
    private.mkdir()
    public.mkdir()
    return private, public


def _forecast(private, **overrides):
    kwargs = dict(
        venue="manifold",
        market_id="mkt-1",
        question="Will the incumbent hold PA-07?",
        p=0.62,
        market_p=0.55,
        closes_utc=CLOSES,
        cluster="us-house-2026",
        rationale="district fundamentals",
        data_dir=private,
        now=NOW,
    )
    kwargs.update(overrides)
    return write(**kwargs)


# --------------------------------------------------------------------------
# The commitment must hide the position
# --------------------------------------------------------------------------


def test_commitment_publishes_only_timestamp_and_digest(dirs):
    private, public = dirs
    record = _forecast(private)
    sync_commitments(private, public)

    entry = read_chain(public)[0]
    assert set(entry) == {"id", "created_utc", "hash", "prev"}

    # The whole point: nothing about the position is recoverable from the file.
    published = json.dumps(entry)
    assert "0.62" not in published
    assert "0.55" not in published
    assert "PA-07" not in published
    assert record["nonce"] not in published


def test_identical_forecasts_produce_different_commitments(dirs):
    """The nonce is what makes the commitment hiding rather than decorative.

    Without it, a reader who knows the question and the market price (both public
    on the venue) could brute-force ~999 values of p in under a second and read a
    live position. Identical content hashing differently is the observable
    consequence of that randomness existing.
    """
    private, public = dirs
    first = _forecast(private, market_id="mkt-a")
    second = _forecast(private, market_id="mkt-a")

    assert first["nonce"] != second["nonce"]
    assert len(first["nonce"]) == 32  # 128 bits
    assert first["hash"] != second["hash"]


def test_guessing_every_probability_does_not_recover_the_hash(dirs):
    """Simulate the attacker: known question, known market price, unknown nonce."""
    private, public = dirs
    record = _forecast(private)

    guess = {k: v for k, v in record.items() if k != "hash"}
    guess["nonce"] = "0" * 32  # the attacker does not have it

    for step in range(1, 1000):
        guess["p"] = step / 1000
        assert digest(guess) != record["hash"]


# --------------------------------------------------------------------------
# Sync and reveal
# --------------------------------------------------------------------------


def test_sync_is_idempotent(dirs):
    private, public = dirs
    _forecast(private, market_id="mkt-1")
    _forecast(private, market_id="mkt-2")

    assert len(sync_commitments(private, public)) == 2
    assert sync_commitments(private, public) == []
    assert len(read_chain(public)) == 2


def test_commitments_preserve_the_chain(dirs):
    private, public = dirs
    _forecast(private, market_id="mkt-1")
    _forecast(private, market_id="mkt-2")
    _forecast(private, market_id="mkt-3")
    sync_commitments(private, public)

    assert check_chain(read_chain(public)) == []


def test_revealed_record_verifies_against_its_commitment(dirs):
    private, public = dirs
    record = _forecast(private)
    sync_commitments(private, public)

    entry = reveal(record["id"], outcome=1, resolved_utc=RESOLVED,
                   data_dir=private, public_dir=public)

    assert entry["outcome"] == 1
    assert entry["p"] == 0.62
    assert check_reveals(read_chain(public), read_revealed(public)) == []


def test_reveal_refuses_unknown_forecast(dirs):
    private, public = dirs
    _forecast(private)
    with pytest.raises(JournalError, match="no forecast with id"):
        reveal("f_doesnotexist", outcome=1, resolved_utc=RESOLVED,
               data_dir=private, public_dir=public)


def test_reveal_refuses_twice(dirs):
    private, public = dirs
    record = _forecast(private)
    sync_commitments(private, public)
    reveal(record["id"], outcome=1, resolved_utc=RESOLVED,
           data_dir=private, public_dir=public)

    with pytest.raises(JournalError, match="already revealed"):
        reveal(record["id"], outcome=0, resolved_utc=RESOLVED,
               data_dir=private, public_dir=public)


@pytest.mark.parametrize("bad", [-1, 2, None, "yes"])
def test_reveal_refuses_bad_outcome(dirs, bad):
    private, public = dirs
    record = _forecast(private)
    with pytest.raises(JournalError, match="outcome must be 0 or 1"):
        reveal(record["id"], outcome=bad, resolved_utc=RESOLVED,
               data_dir=private, public_dir=public)


def test_reveal_refuses_outcome_preceding_the_forecast(dirs):
    private, public = dirs
    record = _forecast(private)
    with pytest.raises(JournalError, match="cannot precede the prediction"):
        reveal(record["id"], outcome=1, resolved_utc="2026-09-15T11:00:00Z",
               data_dir=private, public_dir=public)


# --------------------------------------------------------------------------
# What check.py catches
# --------------------------------------------------------------------------


def test_check_catches_a_forecast_improved_before_reveal(dirs):
    """The attack: commit an honest forecast, reveal a better one."""
    private, public = dirs
    record = _forecast(private, p=0.62)
    sync_commitments(private, public)
    reveal(record["id"], outcome=1, resolved_utc=RESOLVED,
           data_dir=private, public_dir=public)

    path = public / "revealed.jsonl"
    entry = json.loads(path.read_text(encoding="utf-8").strip())
    entry["p"] = 0.97  # claim a far better call than was actually made
    path.write_text(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n",
                    encoding="utf-8", newline="\n")

    problems = check_reveals(read_chain(public), read_revealed(public))
    assert problems
    assert any("changed between recording and reveal" in p for p in problems)


def test_check_catches_a_forecast_revealed_but_never_committed(dirs):
    """The attack: add a winning forecast to the record afterwards."""
    private, public = dirs
    record = _forecast(private)
    sync_commitments(private, public)

    smuggled = dict(record)
    smuggled["id"] = "f_smuggled0001"
    smuggled["outcome"] = 1
    smuggled["resolved_utc"] = RESOLVED
    (public / "revealed.jsonl").write_text(
        json.dumps(smuggled, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8", newline="\n",
    )

    problems = check_reveals(read_chain(public), read_revealed(public))
    assert any("revealed but never committed" in p for p in problems)


def test_check_catches_a_dropped_commitment(dirs):
    """The attack: delete the forecast that went badly."""
    private, public = dirs
    _forecast(private, market_id="mkt-1")
    _forecast(private, market_id="mkt-2")
    _forecast(private, market_id="mkt-3")
    sync_commitments(private, public)

    path = public / "chain.jsonl"
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    path.write_text(lines[0] + "\n" + lines[2] + "\n", encoding="utf-8", newline="\n")

    problems = check_chain(read_chain(public))
    assert problems
    assert any("inserted, removed or reordered" in p for p in problems)
