"""Tests for F03, the Manifold read client.

Hermetic. No network. Every test runs against fixture payloads shaped like real
API responses, because a test that needs the internet is a test that fails on a
train and gets deleted.

The refusal on non-binary markets is the one that matters. Manifold returns
MULTIPLE_CHOICE and NUMERIC markets freely from the same endpoints, and those
carry no single `probability` field. A naive client reads None, and None reaches
the journal as a forecast nobody can score.
"""

from __future__ import annotations

import pytest

from venues import manifold
from venues.manifold import (
    CallCeilingExceeded,
    ManifoldError,
    Market,
    _iso,
    _markets_from,
    forecastable,
    thin,
)

# 2026-11-03T05:00:00Z in epoch milliseconds
CLOSE_MS = 1_793_682_000_000
PAST_MS = 1_600_000_000_000  # 2020


def binary_payload(**overrides):
    payload = {
        "id": "abc123",
        "slug": "will-the-incumbent-hold-pa-07",
        "question": "Will the incumbent hold PA-07?",
        "outcomeType": "BINARY",
        "mechanism": "cpmm-1",
        "probability": 0.55,
        "closeTime": CLOSE_MS,
        "isResolved": False,
        "uniqueBettorCount": 12,
        "totalLiquidity": 250,
        "volume": 1400.5,
        "url": "https://manifold.markets/x/will-the-incumbent-hold-pa-07",
        "token": "MANA",
    }
    payload.update(overrides)
    return payload


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def test_parses_a_binary_market():
    market = Market.from_api(binary_payload())
    assert market.id == "abc123"
    assert market.probability == 0.55
    assert market.bettors == 12
    assert market.liquidity == 250.0
    assert market.token == "MANA"
    assert market.is_resolved is False


def test_epoch_milliseconds_convert_to_iso_utc():
    """Manifold sends epoch ms. The journal takes ISO-8601 UTC with a Z."""
    assert _iso(CLOSE_MS) == "2026-11-03T05:00:00Z"
    assert _iso(None) is None


def test_close_time_survives_into_the_market_record():
    assert Market.from_api(binary_payload()).closes_utc == "2026-11-03T05:00:00Z"


def test_refuses_multiple_choice():
    """The silent-poison guard. These come back from the same endpoints."""
    with pytest.raises(ManifoldError, match="not\n?\\s*BINARY|MULTIPLE_CHOICE"):
        Market.from_api(binary_payload(outcomeType="MULTIPLE_CHOICE", probability=None))


def test_refuses_numeric():
    with pytest.raises(ManifoldError):
        Market.from_api(binary_payload(outcomeType="PSEUDO_NUMERIC"))


def test_refuses_binary_with_no_probability():
    with pytest.raises(ManifoldError, match="carries no probability"):
        Market.from_api(binary_payload(probability=None))


def test_batch_parse_skips_non_binary_instead_of_failing():
    """Most of Manifold is not binary. Skipping is correct; raising would make
    every list call fail on the first multiple-choice market it met."""
    payloads = [
        binary_payload(id="a"),
        binary_payload(id="b", outcomeType="MULTIPLE_CHOICE", probability=None),
        binary_payload(id="c"),
        binary_payload(id="d", outcomeType="POLL", probability=None),
    ]
    markets = _markets_from(payloads)
    assert [m.id for m in markets] == ["a", "c"]


# --------------------------------------------------------------------------
# Forecastability
# --------------------------------------------------------------------------


def test_resolved_market_is_not_forecastable():
    market = Market.from_api(binary_payload(isResolved=True, resolution="YES"))
    assert market.forecastable is False


def test_market_closing_in_the_past_is_not_forecastable():
    assert Market.from_api(binary_payload(closeTime=PAST_MS)).forecastable is False


def test_open_future_market_is_forecastable():
    assert Market.from_api(binary_payload()).forecastable is True


def test_market_with_no_close_time_is_not_forecastable():
    """An open-ended market cannot satisfy the journal's close-time invariant."""
    assert Market.from_api(binary_payload(closeTime=None)).forecastable is False


def test_forecastable_filter_keeps_only_open_future_markets():
    markets = [
        Market.from_api(binary_payload(id="open")),
        Market.from_api(binary_payload(id="done", isResolved=True)),
        Market.from_api(binary_payload(id="past", closeTime=PAST_MS)),
    ]
    assert [m.id for m in forecastable(markets)] == ["open"]


# --------------------------------------------------------------------------
# The thinness band, where F05 and resolution risk disagree
# --------------------------------------------------------------------------


def test_thin_band_excludes_both_ends():
    markets = [
        Market.from_api(binary_payload(id="ghost", uniqueBettorCount=2)),
        Market.from_api(binary_payload(id="good", uniqueBettorCount=12)),
        Market.from_api(binary_payload(id="crowded", uniqueBettorCount=400)),
    ]
    assert [m.id for m in thin(markets)] == ["good"]


def test_thin_band_boundaries_are_inclusive():
    markets = [
        Market.from_api(binary_payload(id="floor", uniqueBettorCount=5)),
        Market.from_api(binary_payload(id="ceiling", uniqueBettorCount=30)),
        Market.from_api(binary_payload(id="under", uniqueBettorCount=4)),
        Market.from_api(binary_payload(id="over", uniqueBettorCount=31)),
    ]
    assert [m.id for m in thin(markets)] == ["floor", "ceiling"]


def test_floor_can_be_dropped_deliberately():
    """The floor is a judgement about resolution risk, not a law. It should be
    possible to override it knowingly."""
    markets = [Market.from_api(binary_payload(uniqueBettorCount=1))]
    assert thin(markets) == []
    assert len(thin(markets, min_bettors=0)) == 1


# --------------------------------------------------------------------------
# The call ceiling
# --------------------------------------------------------------------------


def test_call_ceiling_aborts_rather_than_backing_off(monkeypatch):
    """The failure this guards is a retry loop quietly becoming a multi-hour
    stall. The fix is a ceiling that refuses, not smarter backoff."""
    monkeypatch.setattr(manifold, "_calls_this_run", manifold.MAX_CALLS_PER_RUN)
    with pytest.raises(CallCeilingExceeded, match="refusing to exceed"):
        manifold._get("/markets")


def test_reset_budget_clears_the_counter(monkeypatch):
    monkeypatch.setattr(manifold, "_calls_this_run", 99)
    manifold.reset_budget()
    assert manifold._calls_this_run == 0
