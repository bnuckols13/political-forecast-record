"""F03 - Manifold read client.

Stdlib only. The read path is what the daily record depends on, and no
dependency gets to break it.

Three things this module is opinionated about, each for a reason:

  1. **Binary markets only.** The journal records one probability against one
     outcome. A MULTIPLE_CHOICE or NUMERIC market has no single `probability`
     field, and the live API returns such markets freely. Asking for a
     probability that is not there returns None in a naive client and poisons
     the journal silently, so `Market.from_api` refuses instead.

  2. **Thinness is surfaced, not buried.** F05 established that S01 is only ever
     testable where a ten-point disagreement with the price is plausible, which
     means markets priced by few traders. `uniqueBettorCount` and
     `totalLiquidity` therefore come back on every record and `thin()` is a
     first-class filter rather than something to eyeball in a browser.

  3. **A hard call ceiling that aborts.** The documented limit is 500 requests
     per minute per IP. The failure this guards against is not slowness, it is a
     retry storm quietly turning into a multi-hour stall. The ceiling refuses
     rather than backing off forever.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

BASE = "https://api.manifold.markets/v0"
USER_AGENT = "political-forecast-record/0.1 (+https://github.com/bnuckols13/political-forecast-record)"

# Documented limit is 500/min per IP. We stay far under it: this client is
# driven by a human recording a handful of forecasts, not by a scraper.
MIN_INTERVAL_S = 0.15
MAX_ATTEMPTS = 4
MAX_CALLS_PER_RUN = 120

_last_call = 0.0
_calls_this_run = 0


class ManifoldError(RuntimeError):
    """Raised on an API failure, or on a market that cannot be forecast honestly."""


class CallCeilingExceeded(ManifoldError):
    """Raised when a run would exceed its request budget. Abort, do not back off."""


def reset_budget() -> None:
    """Reset the per-run call counter. Tests and long sessions use this."""
    global _calls_this_run
    _calls_this_run = 0


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    """One GET with polite pacing, bounded retries, and a hard ceiling."""
    global _last_call, _calls_this_run

    if _calls_this_run >= MAX_CALLS_PER_RUN:
        raise CallCeilingExceeded(
            f"refusing to exceed {MAX_CALLS_PER_RUN} requests in one run. "
            "Raise the ceiling deliberately if the work genuinely needs it; do not "
            "let a loop discover this on its own."
        )

    url = f"{BASE}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        elapsed = time.monotonic() - _last_call
        if elapsed < MIN_INTERVAL_S:
            time.sleep(MIN_INTERVAL_S - elapsed)

        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            _calls_this_run += 1
            with urllib.request.urlopen(request, timeout=20) as response:
                _last_call = time.monotonic()
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            _last_call = time.monotonic()
            last_error = exc
            if exc.code == 429 or 500 <= exc.code < 600:
                if attempt < MAX_ATTEMPTS:
                    time.sleep(2**attempt)
                    continue
            raise ManifoldError(f"GET {url} failed: HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            _last_call = time.monotonic()
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(2**attempt)
                continue

    raise ManifoldError(f"GET {url} failed after {MAX_ATTEMPTS} attempts: {last_error}")


def _iso(epoch_ms: int | None) -> str | None:
    """Manifold returns epoch milliseconds. The journal wants ISO-8601 UTC."""
    if epoch_ms is None:
        return None
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


@dataclass(frozen=True)
class Market:
    id: str
    slug: str
    question: str
    probability: float
    closes_utc: str | None
    is_resolved: bool
    resolution: str | None
    bettors: int
    liquidity: float
    volume: float
    url: str
    # "MANA" on every market since sweepcash was discontinued in March 2025.
    # Carried anyway so that a silent currency change is visible in the record
    # rather than inferred later.
    token: str

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "Market":
        outcome_type = payload.get("outcomeType")
        if outcome_type != "BINARY":
            raise ManifoldError(
                f"{payload.get('slug', payload.get('id', '?'))} is {outcome_type}, not "
                "BINARY. The journal records one probability against one outcome; a "
                "market with no single `probability` field cannot be forecast honestly."
            )

        probability = payload.get("probability")
        if probability is None:
            raise ManifoldError(
                f"{payload.get('slug', '?')} reports BINARY but carries no probability"
            )

        return cls(
            id=payload["id"],
            slug=payload.get("slug", ""),
            question=payload.get("question", ""),
            probability=float(probability),
            closes_utc=_iso(payload.get("closeTime")),
            is_resolved=bool(payload.get("isResolved", False)),
            resolution=payload.get("resolution"),
            bettors=int(payload.get("uniqueBettorCount", 0)),
            liquidity=float(payload.get("totalLiquidity", 0) or 0),
            volume=float(payload.get("volume", 0) or 0),
            url=payload.get("url", ""),
            token=payload.get("token", "MANA"),
        )

    @property
    def forecastable(self) -> bool:
        """Open, unresolved, and closing in the future. The journal enforces this
        too, but catching it here saves a pointless refusal later."""
        if self.is_resolved or self.closes_utc is None:
            return False
        return self.closes_utc > datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _markets_from(payloads: list[dict[str, Any]]) -> list[Market]:
    """Parse what we can and drop what we cannot forecast. Non-binary markets are
    the common case on Manifold, so they are skipped rather than fatal."""
    out: list[Market] = []
    for payload in payloads:
        try:
            out.append(Market.from_api(payload))
        except ManifoldError:
            continue
    return out


def list_markets(limit: int = 100) -> list[Market]:
    return _markets_from(_get("/markets", {"limit": min(limit, 1000)}))


def search_markets(term: str, limit: int = 50, **params: Any) -> list[Market]:
    query = {"term": term, "limit": min(limit, 1000), **params}
    return _markets_from(_get("/search-markets", query))


def get_market(market_id: str) -> Market:
    return Market.from_api(_get(f"/market/{market_id}"))


def get_by_slug(slug: str) -> Market:
    return Market.from_api(_get(f"/slug/{slug}"))


def thin(
    markets: list[Market], max_bettors: int = 30, min_bettors: int = 5
) -> list[Market]:
    """The band where a large edge is plausible and resolution is still policed.

    Two forces pull in opposite directions here, and the band is where they cross.

    Pulling toward FEWER bettors: F05. A 3% edge needs ~890 independent clusters
    and is unmeasurable; a 10% edge needs ~80. Only markets where a ten-point
    disagreement with the price is credible can ever test S01, and a market with
    four hundred traders is not one of them.

    Pulling toward MORE bettors: resolution risk. On Manifold the market creator
    resolves their own market. A creator who resolves against the plain reading
    of their criteria usually stands if it technically complies, and an N/A
    resolution cancels the market and claws back profits already taken. Markets
    with more traders draw moderator attention when that happens; a market with
    two bettors does not.

    So the floor is not arbitrary caution. A forecast that resolves wrongly is
    worse than no forecast, because it enters the scored record as a loss you did
    not earn and cannot appeal.
    """
    return [m for m in markets if min_bettors <= m.bettors <= max_bettors]


def forecastable(markets: list[Market]) -> list[Market]:
    return [m for m in markets if m.forecastable]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="venues.manifold", description="F03 Manifold read client."
    )
    parser.add_argument("--check", action="store_true", help="verify the API and shape")
    parser.add_argument("--search", help="search markets by term")
    parser.add_argument("--max-bettors", type=int, default=30, help="thin enough for a large edge")
    parser.add_argument("--min-bettors", type=int, default=5, help="thick enough that resolution is policed")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args(argv)

    try:
        if args.check:
            raw = _get("/markets", {"limit": 50})
            if not isinstance(raw, list) or not raw:
                print("FAIL: /markets did not return a non-empty list")
                return 1
            binary = _markets_from(raw)
            open_binary = forecastable(binary)
            print(f"ok: /markets returned {len(raw)} markets")
            print(f"    {len(binary)} binary, {len(open_binary)} open and forecastable")
            if open_binary:
                sample = open_binary[0]
                print(f"    sample: {sample.slug[:48]}")
                print(f"            p={sample.probability:.3f} bettors={sample.bettors} closes={sample.closes_utc}")
            missing = [f for f in ("id", "question", "outcomeType") if f not in raw[0]]
            if missing:
                print(f"FAIL: response shape changed, missing {missing}")
                return 1
            return 0

        if args.search:
            found = thin(forecastable(search_markets(args.search, limit=args.limit)),
                         max_bettors=args.max_bettors, min_bettors=args.min_bettors)
            if not found:
                print(
                    f"no open binary markets with {args.min_bettors}-{args.max_bettors} "
                    f"bettors for {args.search!r}"
                )
                return 0
            print(
                f"{len(found)} market(s) for {args.search!r} in the "
                f"{args.min_bettors}-{args.max_bettors} bettor band:\n"
            )
            for market in sorted(found, key=lambda m: m.bettors):
                print(f"  {market.probability:>6.1%}  {market.bettors:>4} bettors  {market.question[:64]}")
                print(f"          closes {market.closes_utc}  id={market.id}")
            return 0

        parser.error("pass --check or --search TERM")
    except ManifoldError as exc:
        print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
