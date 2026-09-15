# Manifold API — implementation reference for F03

Verified against the live API on 2026-09-15. Docs: https://docs.manifold.markets/api

Written so whoever builds F03 does not have to re-derive any of it. The section
that matters most is "Traps", because every entry there is something that returns
a plausible wrong answer rather than an error.

## Base

`https://api.manifold.markets`, all paths under `/v0`. The legacy
`manifold.markets/api/v0/...` host still answers but 308-redirects, costing a round
trip. No v1 exists; the changelog shows no breaking change since 2023-12-18.

Responses carry `cache-control: max-age=5` behind Cloudflare, so list reads can be
up to ~5s stale. `/prob` documents a 1s cache.

## Auth

**Read is fully open.** No key, no account, no headers.

Write takes one static header: `Authorization: Key <api_key>`. No signing, no nonce,
no key/secret pair. The key is generated in the profile editor; one per account, and
refreshing invalidates the previous one.

## Endpoints we need

| Purpose | Call |
|---|---|
| Find markets | `GET /v0/search-markets?term=&filter=open&contractType=BINARY&sort=liquidity&limit=` |
| One market | `GET /v0/market/{id}` or `GET /v0/slug/{slug}` |
| One price | `GET /v0/market/{id}/prob` → `{"prob": 0.2954}` |
| **Many prices** | `GET /v0/market-probs?ids=A&ids=B` → `{"A":{"prob":...},...}` |
| Bets (for price history) | `GET /v0/bets?contractId={id}&limit=1000&order=asc` |
| Place a bet | `POST /v0/bet` with `{amount, contractId, outcome, limitProb?, dryRun?}` |
| Cancel | `POST /v0/bet/cancel/{betId}` (POST, not DELETE) |
| Portfolio | `GET /v0/get-user-portfolio?userId=` (no auth) |

`search-markets` params worth knowing: `filter` takes `open|closed|resolved|closing-day|closing-week|closing-month|closing-90-days`; `sort` takes `liquidity|close-date|newest|24-hour-vol|prob-ascending|prob-descending` among others; `topicSlug`, `creatorId`, and `liquidity` (a minimum) all filter server-side.

## Fields

- **`probability`** is the price, a float 0 to 1. Not cents, not a bid/ask pair.
- **`p` is NOT the price.** It is the CPMM centering constant. Observed live on one
  market: `probability` 0.2954 while `p` is 0.3955. Never display it.
- Times are **unix milliseconds as integers** everywhere. No ISO strings.
- `closeTime` is **optional**. Handle `None`.
- **`id` is the stable key.** `slug` is user-editable and `url` embeds a username that
  need not be correct. Ids vary in length (`28dSLslzOz`, `A319ydGB1B7f4PMOROL3`), so
  do not validate on length.
- Resolution fields are **absent entirely** on unresolved markets, not null. Use
  `.get()`. When resolved: `resolution` (`YES`/`NO`/`MKT`/`CANCEL`),
  `resolutionProbability`, `resolutionTime`, `resolverId`.
- `token` is `MANA` in practice. See "Money" below.

## Traps

Each of these returns something that looks fine.

1. **Auth failure returns HTTP 200.** A bad key gives a 200 with
   `{"message":"No private user exists with the provided API key."}`. A missing header
   gives 401. So you cannot branch on status alone; check the body.
2. **`isRedemption: true` bets do not move price.** Reconstructing a price series from
   `/v0/bets` without filtering them produces duplicate-price spikes. On one sampled
   market, 1000 bets yielded 898 usable rows.
3. **An invalid `topicSlug` returns an error body, not an empty list.** The political
   slug is `us-politics`, not `politics`. Validate against `GET /v0/groups`.
4. **`offset` caps at 1000.** Deeper paging needs `sort=newest` plus a `beforeTime`
   cursor set to the last row's `createdTime`.
5. **There is no close-time range filter.** Only the coarse `closing-*` buckets. Filter
   arbitrary windows client-side on `closeTime`.
6. **There is no time-series endpoint.** Price history only exists as a reduction over
   `/v0/bets` using `probBefore` / `probAfter`. Cache it; cost scales with trade count.
7. **`contractType` is trustworthy for BINARY and not for the numeric types.** A live
   500-row sample of `contractType=BINARY` was 500/500 correct, but
   `contractType=PSEUDO_NUMERIC` returned mostly `MULTI_NUMERIC`. Assert
   `outcomeType == "BINARY" and mechanism == "cpmm-1" and probability is not None`
   before using any row.
8. **Three different pagination schemes** across endpoints: id cursors on `/markets`
   and `/bets`, offset-or-`beforeTime` on `/search-markets`. Limit caps at 1000
   everywhere.

## Rate limit

**500 requests per minute, per IP** — not per key. That is the whole documented policy.

No 429 status, `Retry-After`, or `X-RateLimit-*` headers are documented, and normal
responses carry none. Build exponential backoff that reads `Retry-After` if present
but does not depend on it. Use `/v0/market-probs` for batch polling rather than N
single calls.

## Money

**Manifold is play-money. Sweepcash is dead.** It ran September 2024 to March 2025;
issuance stopped, markets were resolved at their then-current probability, cash-out
closed March 28th, and unredeemed balances converted to mana at 100:1. Live check:
`search-markets?token=CASH` returns `[]`, and a 200-market sample was 100% `MANA`.
The FAQ states mana "cannot be converted to cash."

This confirms the two-venue design in `docs/decisions/0003`: Manifold is the free
calibration gym, and no real capital is reachable here.

**Trading fees are zero.** Live `Bet` objects return
`fees: {creatorFee: 0, platformFee: 0, liquidityFee: 0}`. Older resolved markets show
large historical fees, so the plumbing exists and could return. Read the `fees` object
off the returned bet rather than hardcoding zero. Real cost is AMM slippage against
`pool`.

## Bot policy

**Explicitly permitted.** The licensing section names "building bots, automated trading
systems, algorithmic tools, and integrations" as allowed uses. Prohibited: scraping by
means other than the API, and circumventing rate limits.

One restriction that touches this project: **API data may not be used to train AI/ML
models for commercial purposes without a data license** (`data@manifold.markets`).
Personal and non-commercial use is fine. Worth re-reading if this project ever
monetizes.

Bot flagging is a PR against `manifoldmarkets/manifold` adding the username to
`BOT_USERNAMES` in `common/src/envs/constants.ts`. It is a UI label, not an access
gate; nothing blocks API trading before it lands.

## Testing

`POST /v0/bet` accepts **`dryRun: true`**, returning a simulated result without placing
anything. Build the write-path test suite on it.

## Python libraries: write it yourself

- `manifoldpy` — last PyPI release **2023-03-01**. Predates the host migration, the
  current `search-markets` parameters, and every 2024-2026 schema change. Abandonware
  for our purposes.
- `manifoldbot` — alive but tiny, one maintainer, bot-framework shaped rather than
  thin-client shaped.
- `pymanifold` — **name collision.** A 2018 microfluidics simulator. Do not install.

There is no official Python SDK. Since the write path needs one static header and no
signing, a library earns nothing here. A `requests.Session`, a token bucket, and a few
dataclasses is roughly 200 lines and will not rot.

Per `AGENTS.md`, the **read path stays stdlib-only** (`urllib.request`) so the daily
record cannot be broken by a dependency. `requests` is acceptable on the write path,
which is gated behind F13 anyway.

## Verified curl

```bash
curl -s "https://api.manifold.markets/v0/search-markets?term=&contractType=BINARY&filter=open&sort=liquidity&limit=10"
curl -s "https://api.manifold.markets/v0/market/A319ydGB1B7f4PMOROL3/prob"
curl -s "https://api.manifold.markets/v0/market-probs?ids=A319ydGB1B7f4PMOROL3&ids=66cWxhCKvNUZT0u3qx5V"
```

## Not verified

- The 429 status code and any rate-limit headers. Not documented, absent from normal
  responses, and I did not trigger the limit to find out.
- Whether binary `resolution` takes values beyond `YES`/`NO`/`MKT`/`CANCEL`. `MKT` and
  `CANCEL` come from the docs; `YES` and `NO` were observed live.
- The `contractType` enum is published with a trailing "see code", so it is not
  exhaustive as documented.
