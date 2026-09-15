"""Tests for the cluster convention and the election watchlist.

These are integrity tests rather than logic tests, and they earn their place for
one reason: a typo in a cluster key does not raise. It silently splits one
observation into two, or merges two into one, and every significance test
downstream inherits the error with no symptom. The convention is only worth
having if something enforces it.
"""

from __future__ import annotations

import re

import pytest

from model.clusters import (
    SHORTLIST,
    WATCHLIST,
    by_cluster,
    shortlist,
    tractable,
    upcoming,
)

KEY = re.compile(r"^[a-z]{2}-\d{4}-[a-z]+$")
DATE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


def test_cluster_keys_are_unique():
    """Two elections sharing a key would merge two independent observations into
    one, which understates the denominator and is the safer direction to fail in
    but still wrong."""
    keys = [e.cluster for e in WATCHLIST]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize("election", WATCHLIST, ids=lambda e: e.cluster)
def test_cluster_key_follows_the_convention(election):
    assert KEY.match(election.cluster), f"{election.cluster} is not <iso2>-<year>-<body>"


@pytest.mark.parametrize("election", WATCHLIST, ids=lambda e: e.cluster)
def test_dates_are_iso_and_sortable(election):
    assert DATE.match(election.date), f"{election.cluster} has unsortable date {election.date}"


@pytest.mark.parametrize("election", WATCHLIST, ids=lambda e: e.cluster)
def test_every_election_carries_a_note_and_search_terms(election):
    """A watchlist entry with no search terms cannot be looked up, and one with
    no note is a date nobody can act on."""
    assert election.note.strip()
    assert election.search_terms


def test_watchlist_is_in_date_order():
    dates = [e.sort_key for e in WATCHLIST]
    assert dates == sorted(dates)


def test_shortlist_keys_all_exist():
    """A typo here silently drops a target from the shortlist with no error."""
    known = {e.cluster for e in WATCHLIST}
    missing = set(SHORTLIST) - known
    assert not missing, f"shortlist names clusters not in the watchlist: {missing}"
    assert len(shortlist()) == len(SHORTLIST)


def test_high_slip_risk_is_excluded_from_tractable():
    """An election that does not happen is not a resolution. Haiti, South Sudan
    and Guinea-Bissau are warnings on the list, not targets."""
    risky = {e.cluster for e in WATCHLIST if e.slip_risk == "high"}
    assert risky, "the watchlist should carry some warnings"
    assert risky.isdisjoint({e.cluster for e in tractable()})


def test_tractable_keeps_moderate_risk():
    """Moderate means the date may move, not that the election may not happen."""
    moderate = [e for e in WATCHLIST if e.slip_risk == "moderate"]
    assert moderate
    assert all(e in tractable() for e in moderate)


def test_us_midterms_are_one_cluster():
    """The finding F05 exists to enforce. Every federal and state race on that
    night shares one national error term."""
    us = by_cluster("us-2026-midterms")
    assert us is not None
    same_night = [e for e in WATCHLIST if e.date == "2026-11-03"]
    assert same_night == [us]


def test_new_zealand_is_separate_from_the_midterms():
    """Four days apart, and completely independent. Two observations, not one."""
    nz = by_cluster("nz-2026-general")
    us = by_cluster("us-2026-midterms")
    assert nz is not None and us is not None
    assert nz.cluster != us.cluster
    assert (nz.date > us.date) and (nz.date < "2026-11-30")


def test_france_presidential_and_legislative_are_separate_clusters():
    """The judgement call, pinned so it cannot drift. Two months apart, different
    electorates, capable of diverging sharply."""
    pres = by_cluster("fr-2027-presidential")
    leg = by_cluster("fr-2027-legislative")
    assert pres is not None and leg is not None
    assert pres.cluster != leg.cluster
    assert "conditional" in leg.note.lower() or "dependence" in leg.note.lower()


def test_upcoming_filters_by_date():
    near = upcoming("2026-12-31")
    assert by_cluster("us-2026-midterms") in near
    assert by_cluster("nz-2026-general") in near
    assert by_cluster("ke-2027-general") not in near


def test_unknown_cluster_returns_none():
    assert by_cluster("xx-1999-nonsense") is None


def test_month_only_dates_sort_mid_month_not_as_a_prefix():
    """The defect this caught: "2027-06" is a prefix of "2027-06-06", so naive
    string ordering puts the vaguer date first. France's legislative election,
    known only to be in June, would jump ahead of Mexico's on June 6 purely
    because we know less about it."""
    fr = by_cluster("fr-2027-legislative")
    mx = by_cluster("mx-2027-deputies")
    assert fr.date < mx.date          # the naive comparison, wrong
    assert fr.sort_key > mx.sort_key  # the corrected one
    assert fr.sort_key == "2027-06-15"
    assert mx.sort_key == "2027-06-06"
