"""F05 - the sufficiency pre-flight. A kill-gate.

One question: how many resolved, cluster-independent forecasts does it take to
detect a real Brier edge over the market price? If the honest answer exceeds
what a cycle can produce, S01 is not a thesis, it is a wish, and the correct
output of this project is a refusal ADR rather than fourteen more build units.

Needs no data, no network, no venue. Run it before building anything downstream.

-------------------------------------------------------------------------------
The arithmetic

For a binary outcome Y, your probability p, the market's m, the per-forecast
difference in Brier score collapses to a closed form:

    d = (m - Y)^2 - (p - Y)^2 = (m - p)(m + p - 2Y)

Write e = p - m for your edge in probability units. Assume you are perfectly
calibrated (true probability q = p) and the market is the one that is wrong.
That assumption is maximally generous to you, which is the point: what comes out
is a LOWER bound on the sample you need.

    E[d]   = e^2
    Var[d] = 4 e^2 q(1-q)
    sd[d]  = 2|e| sqrt(q(1-q))

Two consequences worth sitting with.

First, your Brier improvement is the SQUARE of your probability edge. Being five
points better than the market on every question buys 0.0025 of Brier. The
quantity you can feel is e; the quantity you get scored on is e^2.

Second, substituting into N = (t sd / mean)^2, the e cancels almost entirely:

    N = (t * 2|e| sqrt(q(1-q)) / e^2)^2 = 4 t^2 q(1-q) / e^2

and at q = 0.5, which maximises the variance and is therefore the conservative
choice, this is simply

    N = t^2 / e^2

-------------------------------------------------------------------------------
Clustering, which is where the real damage is

N above counts INDEPENDENT observations. Forty House races resolving on one
night under one national environment are not forty. With intra-cluster
correlation rho and clusters of size k, the design effect is

    DEFF = 1 + (k - 1) rho

Effective sample is total/DEFF, so the clusters you need are

    clusters = N * (1 + (k-1) rho) / k

At rho = 0 clustering is free and k forecasts buy k observations. At rho = 1 a
cluster is one observation no matter how many forecasts it contains, and the
required number of CLUSTERS equals N outright.

The midterms are close to the rho = 1 case. That is the finding this module
exists to surface.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


class SufficiencyError(ValueError):
    """Raised on an input that would produce a meaningless answer."""


def brier_difference(p: float, m: float, y: int) -> float:
    """Market Brier minus mine. Positive means I did better.

    Computed the long way on purpose. `test_sufficiency` checks it against the
    closed form used in the derivation above; if the two ever disagree, the
    derivation is wrong and every number in this module is wrong with it.
    """
    if y not in (0, 1):
        raise SufficiencyError(f"outcome must be 0 or 1, got {y!r}")
    return (m - y) ** 2 - (p - y) ** 2


def expected_improvement(edge: float) -> float:
    """Mean Brier gain per forecast, assuming you are calibrated and the market is not."""
    return edge**2


def difference_sd(edge: float, q: float = 0.5) -> float:
    """Standard deviation of the per-forecast Brier difference."""
    if not 0.0 < q < 1.0:
        raise SufficiencyError(f"q must lie strictly between 0 and 1, got {q}")
    return 2 * abs(edge) * math.sqrt(q * (1 - q))


def independent_n(edge: float, t: float = 2.0, q: float = 0.5) -> float:
    """Independent observations needed to clear a t-threshold.

    q defaults to 0.5, which maximises the variance and so maximises N. That is
    the conservative direction.
    """
    if edge == 0:
        raise SufficiencyError("a zero edge is never detectable; N is unbounded")
    mean = expected_improvement(edge)
    sd = difference_sd(edge, q)
    return (t * sd / mean) ** 2


def design_effect(cluster_size: int, icc: float) -> float:
    """How much correlation inside a cluster inflates the sample you need."""
    if cluster_size < 1:
        raise SufficiencyError("cluster_size must be at least 1")
    if not 0.0 <= icc <= 1.0:
        raise SufficiencyError(f"icc must lie in [0, 1], got {icc}")
    return 1 + (cluster_size - 1) * icc


@dataclass(frozen=True)
class Requirement:
    edge: float
    cluster_size: int
    icc: float
    independent: float
    clusters: float
    forecasts: float


def requirement(
    edge: float, cluster_size: int, icc: float, t: float = 2.0, q: float = 0.5
) -> Requirement:
    n = independent_n(edge, t, q)
    deff = design_effect(cluster_size, icc)
    clusters = n * deff / cluster_size
    return Requirement(
        edge=edge,
        cluster_size=cluster_size,
        icc=icc,
        independent=n,
        clusters=clusters,
        forecasts=clusters * cluster_size,
    )


def preflight(
    edges: tuple[float, ...] = (0.03, 0.05, 0.10, 0.15),
    cluster_size: int = 20,
    iccs: tuple[float, ...] = (0.0, 0.2, 0.5, 0.9),
    t: float = 2.0,
    clusters_available: int = 30,
) -> int:
    """Print the table and a verdict. Returns 0 if any scenario is reachable."""
    print("F05 - sufficiency pre-flight")
    print("=" * 74)
    print(
        f"\nAssumptions: one-sided t >= {t}, true probability q = 0.5 (worst case for\n"
        f"variance), you are perfectly calibrated and the market carries the error.\n"
        f"Every number below is therefore a LOWER bound on what you actually need.\n"
        f"Clusters of {cluster_size} forecasts each.\n"
    )
    print(f"{'edge':>6} {'ICC':>6} {'indep. obs':>12} {'clusters':>12} {'forecasts':>12}")
    print("-" * 74)

    reachable: list[Requirement] = []
    for edge in edges:
        for icc in iccs:
            req = requirement(edge, cluster_size, icc, t)
            flag = ""
            if req.clusters <= clusters_available:
                reachable.append(req)
                flag = "  <- reachable"
            print(
                f"{edge:>6.2f} {icc:>6.2f} {req.independent:>12,.0f} "
                f"{req.clusters:>12,.0f} {req.forecasts:>12,.0f}{flag}"
            )

    print("-" * 74)
    print(f"\nAgainst a budget of {clusters_available} independent event clusters:\n")

    if reachable:
        best = min(reachable, key=lambda r: r.edge)
        print(
            f"  REACHABLE. The smallest detectable edge is {best.edge:.0%} at ICC "
            f"{best.icc:.1f},\n  needing {best.clusters:,.0f} clusters "
            f"({best.forecasts:,.0f} forecasts)."
        )
    else:
        print("  NOT REACHABLE at any tested edge. S01 is undetectable on this budget.")

    print(
        "\nThe finding that matters more than the table:\n"
        "\n"
        "  A whole midterm night is close to ICC 1.0. Every House race resolves at once\n"
        "  under one national polling environment, so 400 forecasts on 400 races buy\n"
        "  roughly ONE observation, not 400. Read the ICC 0.9 rows as the midterms.\n"
        "\n"
        "  The route to a verdict is therefore many UNRELATED clusters resolving on\n"
        "  different dates for different reasons, not many forecasts inside one event.\n"
        "  Wide scope on Manifold is not a calibration nicety. It is the only way the\n"
        "  denominator ever grows.\n"
    )
    return 0 if reachable else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="inference.sufficiency",
        description="F05 sufficiency pre-flight (kill-gate).",
    )
    parser.add_argument("--preflight", action="store_true", help="print the table and verdict")
    parser.add_argument("--cluster-size", type=int, default=20)
    parser.add_argument("--t", type=float, default=2.0)
    parser.add_argument("--clusters-available", type=int, default=30)
    args = parser.parse_args(argv)

    if not args.preflight:
        parser.error("pass --preflight")

    return preflight(
        cluster_size=args.cluster_size,
        t=args.t,
        clusters_available=args.clusters_available,
    )


if __name__ == "__main__":
    raise SystemExit(main())
