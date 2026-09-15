"""Tests for F05, the sufficiency pre-flight.

Every number this module produces rests on one derivation:

    d = (m - Y)^2 - (p - Y)^2 = (m - p)(m + p - 2Y)
    E[d] = e^2,  sd[d] = 2|e| sqrt(q(1-q))   when q = p

If that derivation is wrong, the kill-gate is wrong, and a wrong kill-gate either
kills a good project or waves a doomed one through. So it is checked three ways:
against hand-computed values, against the closed form, and against Monte Carlo
simulation, which is an independent path to the same quantity.
"""

from __future__ import annotations

import math
import random

import pytest

from inference.sufficiency import (
    SufficiencyError,
    brier_difference,
    design_effect,
    difference_sd,
    expected_improvement,
    independent_n,
    requirement,
)


# --------------------------------------------------------------------------
# Hand-computed values. The oracle.
# --------------------------------------------------------------------------


def test_brier_difference_hand_computed_hit():
    """p=0.70, m=0.50, outcome YES.

    market Brier = (0.50 - 1)^2 = 0.2500
    mine         = (0.70 - 1)^2 = 0.0900
    difference   = 0.1600
    """
    assert brier_difference(p=0.70, m=0.50, y=1) == pytest.approx(0.16)


def test_brier_difference_hand_computed_miss():
    """Same forecast, outcome NO. Being bolder than the market costs more.

    market Brier = (0.50 - 0)^2 = 0.2500
    mine         = (0.70 - 0)^2 = 0.4900
    difference   = -0.2400
    """
    assert brier_difference(p=0.70, m=0.50, y=0) == pytest.approx(-0.24)


def test_agreeing_with_the_market_scores_identically():
    for y in (0, 1):
        assert brier_difference(p=0.42, m=0.42, y=y) == pytest.approx(0.0)


@pytest.mark.parametrize("p,m,y", [(0.7, 0.5, 1), (0.7, 0.5, 0), (0.1, 0.9, 1), (0.33, 0.66, 0)])
def test_long_form_matches_the_closed_form_used_in_the_derivation(p, m, y):
    """The whole module is built on this identity. Check it directly."""
    closed = (m - p) * (m + p - 2 * y)
    assert brier_difference(p, m, y) == pytest.approx(closed)


def test_expected_improvement_is_the_square_of_the_edge():
    """Five points of edge buys 0.0025 of Brier. This is the sobering one."""
    assert expected_improvement(0.05) == pytest.approx(0.0025)
    assert expected_improvement(0.10) == pytest.approx(0.01)
    assert expected_improvement(-0.05) == pytest.approx(0.0025)  # sign-independent


def test_difference_sd_hand_computed():
    """2 * |0.05| * sqrt(0.5 * 0.5) = 0.1 * 0.5 = 0.05"""
    assert difference_sd(0.05, q=0.5) == pytest.approx(0.05)


def test_independent_n_hand_computed():
    """(t * sd / mean)^2 = (2.0 * 0.05 / 0.0025)^2 = 40^2 = 1600"""
    assert independent_n(0.05, t=2.0, q=0.5) == pytest.approx(1600.0)


def test_independent_n_reduces_to_t_squared_over_edge_squared_at_q_half():
    """The e cancels down to N = t^2 / e^2. Verify the simplification holds."""
    for edge in (0.02, 0.05, 0.10, 0.25):
        for t in (1.645, 2.0, 2.576):
            assert independent_n(edge, t=t, q=0.5) == pytest.approx(t**2 / edge**2)


def test_halving_the_edge_quadruples_the_sample():
    """N scales as 1/e^2, so small edges are brutally expensive."""
    assert independent_n(0.05) == pytest.approx(4 * independent_n(0.10))


def test_design_effect_hand_computed():
    """1 + (10 - 1) * 0.5 = 5.5"""
    assert design_effect(10, 0.5) == pytest.approx(5.5)
    assert design_effect(1, 0.9) == pytest.approx(1.0)  # a cluster of one is one
    assert design_effect(20, 0.0) == pytest.approx(1.0)  # no correlation, no penalty


# --------------------------------------------------------------------------
# Clustering: the part that actually decides whether S01 is testable
# --------------------------------------------------------------------------


def test_uncorrelated_clusters_cost_nothing():
    """At ICC 0, k forecasts buy k observations."""
    req = requirement(edge=0.05, cluster_size=20, icc=0.0)
    assert req.clusters == pytest.approx(req.independent / 20)
    assert req.forecasts == pytest.approx(req.independent)


def test_perfectly_correlated_clusters_are_one_observation_each():
    """At ICC 1.0, a cluster is one observation no matter how many forecasts it holds.

    This is the midterms. Every House race resolves on one night under one
    national environment, so 400 forecasts on 400 races buy roughly one
    observation. The required CLUSTER count equals the independent-N outright.
    """
    req = requirement(edge=0.05, cluster_size=400, icc=1.0)
    assert req.clusters == pytest.approx(req.independent)
    assert req.forecasts == pytest.approx(req.independent * 400)


def test_correlation_monotonically_raises_the_cluster_requirement():
    previous = 0.0
    for icc in (0.0, 0.2, 0.5, 0.9, 1.0):
        req = requirement(edge=0.05, cluster_size=20, icc=icc)
        assert req.clusters > previous
        previous = req.clusters


# --------------------------------------------------------------------------
# Monte Carlo. An independent path to the analytic result.
# --------------------------------------------------------------------------


def test_simulation_confirms_the_analytic_mean_and_sd():
    """Simulate the Brier difference directly and compare to the closed forms.

    This is the real check on the derivation. If the algebra above is wrong, the
    simulation and the formula disagree here and nothing else in the module can
    be trusted.
    """
    rng = random.Random(12345)
    m, p = 0.50, 0.55
    edge = p - m
    q = p  # calibrated forecaster: the true probability is what I said
    draws = 200_000

    samples = [brier_difference(p, m, 1 if rng.random() < q else 0) for _ in range(draws)]
    observed_mean = sum(samples) / draws
    observed_sd = math.sqrt(sum((s - observed_mean) ** 2 for s in samples) / (draws - 1))

    assert observed_mean == pytest.approx(expected_improvement(edge), abs=5e-4)
    assert observed_sd == pytest.approx(difference_sd(edge, q), rel=0.02)


def test_simulation_confirms_a_miscalibrated_forecaster_loses():
    """Claiming an edge you do not have makes your Brier worse, not merely flat."""
    rng = random.Random(999)
    m, p = 0.50, 0.70
    q = 0.50  # the market was right; I was overconfident
    draws = 100_000

    samples = [brier_difference(p, m, 1 if rng.random() < q else 0) for _ in range(draws)]
    assert sum(samples) / draws < 0


# --------------------------------------------------------------------------
# Refusals
# --------------------------------------------------------------------------


def test_zero_edge_is_never_detectable():
    with pytest.raises(SufficiencyError, match="never detectable"):
        independent_n(0.0)


@pytest.mark.parametrize("bad", [0.0, 1.0, -0.5, 2.0])
def test_refuses_impossible_true_probability(bad):
    with pytest.raises(SufficiencyError, match="q must lie strictly"):
        difference_sd(0.05, q=bad)


@pytest.mark.parametrize("bad", [-0.1, 1.5])
def test_refuses_impossible_icc(bad):
    with pytest.raises(SufficiencyError, match="icc must lie"):
        design_effect(10, bad)


def test_refuses_empty_cluster():
    with pytest.raises(SufficiencyError, match="at least 1"):
        design_effect(0, 0.5)


@pytest.mark.parametrize("bad", [-1, 2, 0.5, None])
def test_refuses_non_binary_outcome(bad):
    with pytest.raises(SufficiencyError, match="must be 0 or 1"):
        brier_difference(0.6, 0.5, bad)
