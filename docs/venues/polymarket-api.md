# Polymarket API — reference

Verified against the live API 2026-09-15. Docs: https://docs.polymarket.com

**Start here: order placement is geo-blocked from Pennsylvania.** I called
`GET https://polymarket.com/api/geoblock` from this machine and got back
`{"blocked": true, "country": "US", "region": "PA"}`. Reads work fine from here;
`POST /order` returns 403 with "Trading restricted in your region." The US is
*close-only* rather than hard-blocked, so existing positions can be exited but not
opened.

So Polymarket's role here is a **price-comparison and cross-venue reference source**,
not a trading venue. That is still worth having: a second independent price on the
same question is a check on whether a Kalshi or Manifold price is idiosyncratic.

A separate CFTC-regulated US product exists (QCX LLC, `polymarket.us`, its own docs
and its own `polymarket-us` package). **None of the detail below transfers to it.**

## Hosts

| Host | Purpose | Auth |
|---|---|---|
| `gamma-api.polymarket.com` | discovery: events, markets, search | none |
| `clob.polymarket.com` | order book, prices, trading | reads open |
| `data-api.polymarket.com` | positions, holders, resolutions | none for reads |

## Use the keyset endpoints

`GET /markets` and `GET /events` return **live deprecation headers with an already
expired sunset date**:

```
deprecation: true
sunset: Fri, 01 May 2026 00:00:00 GMT
warning: 299 - "use /markets/keyset"
```

They still answer four months past sunset. Build on `/markets/keyset` and
`/events/keyset` with `after_cursor`. Limit caps at 100.

## Traps

1. **`outcomePrices` is a JSON-encoded string containing an array of strings.**
   `"[\"0.0395\", \"0.9605\"]"`. Double-parse it. Same for `outcomes`,
   `clobTokenIds`, and `umaResolutionStatuses`. Pairing is positional: index 0 is
   Yes.
2. **`active` is not a liveness flag and is silently unfilterable.** Every one of
   100 sampled `closed=true` markets had `active: true`, including a resolved 2024
   election market. Passing `?active=false` returns markets with `active: true` —
   unknown params return 200 and are discarded. Use `closed` and `acceptingOrders`.
3. **`bestBid` is absent in about a third of open markets** — the key is omitted
   rather than sent as `0` or `null`. Always `.get()`.
4. **Best bid AND best ask are both the LAST element** of `/book`'s arrays. Bids
   ascend, asks descend.
5. **Stdlib `urllib` is 403'd by Cloudflare.** The `Python-urllib/3.12` user agent
   is blocked on both Gamma and CLOB; `requests` and any custom UA work. This is
   the one place in this project where the stdlib-only rule cannot hold, which is
   fine because nothing on the daily record path touches Polymarket.
6. **Two documented fields contradict reality.** `/midpoint` returns key `mid`, not
   `mid_price` as the spec says, and `/price` returns a **string** where the spec
   declares a number. A schema-generated client breaks on both.
7. **`closedTime` is not ISO 8601** (`"2024-11-06 15:17:41+00"`, Postgres
   timestamptz). `endDate` is.
8. **Keyset `order` takes camelCase**, not the snake_case the docs show.
   `order=volume_num` → 422; `order=volumeNum` → 200.

## Identity

**Key on `conditionId`** — the on-chain CTF identifier, stable across Gamma, CLOB,
Data API and the subgraphs, and the join key every other endpoint accepts. The Gamma
numeric `id` exists nowhere else, `slug` is editable, and `questionID` was observed
**diverging** from the Data API's `question_id` on a negRisk market, so never join on
it. Store `clobTokenIds` as the price-query keys.

## Binary detection is counterintuitive

**`outcomes == ["Yes","No"]` does not mean binary.** In a 100-market sample, 100/100
had exactly that, and 91 were legs of multi-outcome events. Polymarket models "next
prime minister" as N separate Yes/No markets under one event.

Tested across 4,649 markets: the exact rule is that the parent event has exactly one
market. The practical single-field test is `groupItemTitle == ""`, accurate to about
0.04% (2 false positives in 4,649). `negRisk == false` alone is insufficient — 1,312
non-negRisk markets are still multi-outcome legs.

## Fees

`fee = C × feeRate × p × (1 − p)`, **takers only**. Zero-fee is over as of the
March 2026 rollout. Politics is 0.04, crypto 0.07, geopolitics still 0.

Because of the `p(1−p)` term the dollar fee peaks at 50¢ but as a percentage of
notional it is steeply regressive toward long shots — crypto is ~1.75% at 50¢ and
~7% at 1¢. Model fees per price, never as flat basis points. Read `feeSchedule` off
the market rather than hardcoding the table.

## Client

For read-only comparison use, **`requests` directly**. The endpoints are open and
the payloads complete.

**Never `py-clob-client`.** Its README states the repository is archived and "the
client is no longer functional and should not be used." It is still installable from
PyPI with no deprecation marker, so `pip install` succeeds and then fails at runtime.
This is what every pre-2026 tutorial hands you. The current official package is
`polymarket-client`, which ships breaking changes in every 0.x minor.

## Rate limits

IP-based via Cloudflare, which throttles rather than rejecting. Gamma `/markets` is
300 per 10s; CLOB `/book`, `/price`, `/midpoint` are 1,500 per 10s each. No
`x-ratelimit-*` or `retry-after` headers on successful reads, so budget cannot be
introspected and must be modelled.
