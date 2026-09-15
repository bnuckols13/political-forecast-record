# Kalshi API — reference for F13 (blocked)

Verified against the live API 2026-09-15. Docs: https://docs.kalshi.com
F13 is blocked by design until F12's gate passes; this exists so that when it
unblocks, nobody rebuilds it from stale tutorials.

**Read that sentence literally. Nearly every Kalshi tutorial online is wrong about
the price fields**, because the schema broke in March 2026 and the guides did not.

## Base

`https://external-api.kalshi.com/trade-api/v2` (recommended, dedicated external
host). `https://api.elections.kalshi.com/trade-api/v2` also works and, despite the
name, serves all markets. `trading-api.kalshi.com` returns 401 with a move notice:
dead. There is no v3 — `/trade-api/v3/markets` 404s. Kalshi versions individual
operations instead of the path.

The OpenAPI document self-reports `version: 3.30.0`, which is the *spec* version,
not the URL's v2. Spec: https://docs.kalshi.com/openapi.yaml (349 KB, complete).
Changelog RSS: https://docs.kalshi.com/changelog/rss.xml — subscribe to it.

## Auth

**Read is fully open.** No key, no headers. Everything under `/portfolio`,
`/account`, `/api_keys` requires auth. Legacy email/password login is removed (both
`/login` and `/log_in` 404).

RSA-PSS signing, three headers per request:

| Header | Value |
|---|---|
| `KALSHI-ACCESS-KEY` | API Key ID (UUID) |
| `KALSHI-ACCESS-TIMESTAMP` | current time in **milliseconds** |
| `KALSHI-ACCESS-SIGNATURE` | base64 RSA-PSS signature |

String to sign is `timestamp + METHOD + path`, concatenated with no separators.
The path **includes** `/trade-api/v2` and **excludes** the query string. PSS with
SHA-256 for digest and MGF1, salt length = digest length.

Keys are generated in Account & security → API Keys. The private key downloads once
and cannot be retrieved afterwards.

## The five things that break a client

1. **Prices are fixed-point dollar STRINGS, not cent integers.** As of 2026-03-12
   the integer fields (`yes_bid`, `no_ask`, `last_price`, `volume`, `open_interest`)
   were removed from all REST and WebSocket responses. You now read
   `yes_bid_dollars: "0.0100"` and `volume_fp: "794.09"`. **Parse with `Decimal`,
   never float** — ticks go down to $0.0001 and responses emit up to six decimals.
2. **`GET /markets` without `mve_filter=exclude` returns almost entirely
   auto-generated combo markets.** A live sample was 100/100 multivariate parlay
   markets; with the filter, 0/100. Always pass it.
3. **The `status` query filter and the `status` response field use different
   vocabularies.** Filter `open` → response `active`. Filter `closed` → response
   `determined`. Filter `settled` → response `finalized`. Passing `status=active`
   returns HTTP 400.
4. **The official Python package was renamed.** `kalshi-python` is deprecated and
   over a year stale; it parses current responses into `yes_bid=None` on every
   field without raising, so you would be trading off nulls. It is now
   `kalshi_python_sync` / `kalshi_python_async` — which **require Python >= 3.13**,
   and this box is on 3.12.10, so pip silently resolves to a broken December 2025
   build. See "Client" below.
5. **The orderbook returns bids only, on both sides, ascending.** Best bid is the
   **last** element. Best YES ask is derived as `1.00 − best NO bid`.

## Other schema facts

- Times in responses are **RFC3339 strings** (`"2026-09-17T05:00:00Z"`), while query
  params like `min_close_ts` are **unix seconds**. Do not mix them.
- Identity is **Series → Event → Market**; the market `ticker` is the stable unique
  id. Kalshi's own warning: do not parse ticker strings to infer relationships.
- `result` is `""` unresolved, then `"yes"` / `"no"` / `"scalar"`.
- Multi-outcome is modelled as several binary markets under one event with
  `mutually_exclusive: true`. Every one of 1,719 live markets sampled was
  `market_type: "binary"`.
- `GET /portfolio/balance` is the one exception that still returns integer cents
  alongside `balance_dollars`. Use the dollars field; the integer truncates.
- Market orders no longer exist. Use a crossing limit with `immediate_or_cancel`
  or `fill_or_kill`.

## Rate limits

Token bucket, not requests-per-second. Most requests cost 10 tokens. Two independent
buckets, Read and Write. Basic tier is 200 read tokens/s (20 GETs/s) and 100 write
(10 orders/s), which is ample here.

On limit: **HTTP 429 with no `Retry-After` and no `X-RateLimit-*` headers** — Kalshi
says so explicitly. Back off exponentially. Note responses carry
`Cache-Control: max-age=15`, so polling faster than ~15s just serves cached edge data.

Batching saves nothing: 25 creates cost 25 × 10 tokens, and the whole batch must fit
in the bucket at once or the entire batch is rejected.

## Fees

```
taker: fees = round_up( M × 0.07   × C × P × (1−P) )
maker: fees = round_up( M × 0.0175 × C × P × (1−P) )
```

`P` in dollars, `C` contracts, `M` a per-series multiplier (default 1 taker,
0 maker). Rounding is to a **centicent on `fee + positionCost`**, not a naive
ceil-to-the-cent — a naive implementation is off by a cent at P=0.70 and P=0.80.

**Do not hardcode 0.07.** Read `fee_type` and `fee_multiplier` off
`GET /series/{ticker}`. Live: politics is 100% `quadratic` with multiplier 1 for
2,314 of 2,319 series and 0 (fee-free) for 5. Maker fees switched on 2026-08-20.
Better still, read `average_fee_paid` back off the order response.

No settlement fee, no membership fee, no ACH fee.

## Demo

`https://external-api.demo.kalshi.co/trade-api/v2`, UI at https://demo.kalshi.co.
**Demo keys are entirely separate from production keys** and do not cross over.
Mock funds. Kalshi warns demo prices may not reflect real markets.

## Client

**Hit REST directly with `requests`, per Kalshi's own recommendation:** "For
production, we recommend generating your own client from those specs — or
integrating directly — for full control."

The surface we need is four unauthenticated GETs. Auth is about twenty lines. Every
library in this space is either a year behind the March 2026 break or four months old
with fourteen major versions. And the official SDK's Python >= 3.13 floor rules it
out on this box entirely.

Whatever is used, **write one smoke test asserting a known ticker returns a non-null
price.** That single assertion is what catches a stale client returning `None` for
every field without raising.

## Legal status, as of 2026-09-15

Live and legal for election markets after a district court vacated the CFTC's
prohibition, but actively contested: the CFTC filed an emergency stay motion
2026-09-06, and Arizona and Connecticut enforcement actions are in progress with the
CFTC suing the states. In April the CFTC brought its first insider-trading
enforcement on event contracts. This is a position-sizing consideration, and it is
why F13 stays blocked behind a human decision rather than a passing test.

## Not verified

Current KYC and state-by-state eligibility (kalshi.com 429s non-browser clients).
A formal market-maker program with published rebate terms. Any live
`market_type: "scalar"` market.
