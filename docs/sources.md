# Data sources, ranked by cluster independence

Verified live 2026-09-15.

F05 established that the unit of independence is the correlated-event group, and
that roughly 80 clusters are needed at a 10% edge. **That makes this document a
ranking of sources by how many independent clusters each one feeds**, not by how
much data each one holds. A source with a million rows that all load on one
national polling error is worth about one observation.

---

## The point-in-time problem has followed us here

`crypto-trading` bars any backtest from using a field that was not knowable on the
bar being traded, and treats provider-revised fundamentals as lookahead. The same
trap exists in this domain and it is easier to fall into, because the defaults are
wrong rather than merely available.

**FRED serves today's revised values by default.** Use ALFRED semantics —
`output_type=4` with an explicit `realtime_end` — or a backtest silently learns an
unemployment rate nobody had on the day in question.

**VoteHub retroactively rewrote its published history.** Its own metadata documents
a methodology change on 2026-01-17 that changed previously-published averages. A
series pulled today is not the series that existed in December.

**No archive of any of this exists.** Which gives three things to start snapshotting
immediately, on the same accrue-or-lose argument that put the forecast journal first:

1. VoteHub's computed averages
2. snoutcounter's CSVs
3. The OIRA under-review XML

---

## Genuinely independent clusters

These resolve on separate timelines under separate error terms. Each is closer to
its own cluster, which is what the sufficiency math actually needs.

| Source | Independent questions/yr | Auto-resolvable | Key |
|---|---|---|---|
| **reginfo.gov OIRA XML** | 159 under review now, 611 completed YTD | yes | none |
| Federal Register | 2,122 final + 1,279 proposed rules; 1,054 open comment periods | yes | none |
| Congress.gov `/nomination` | ~2,147 live in the 119th | yes | required |
| CourtListener | 152,214 opinions on one query, same-day indexing | yes | `/search/` works anonymously |
| Congress.gov `/bill` | tens of thousands | coarse stages only | required |
| FRED releases | scheduled prints | yes | required |

### The best find: OIRA's under-review XML

`reginfo.gov/public/do/XMLViewFileAction?f=EO_RULES_UNDER_REVIEW.xml`

Keyless, RUNDATE-stamped daily, one of 49 XML reports. Each record carries RIN,
stage, economic significance, date received, and legal deadline. On completion a
`<DECISION>` field takes exactly four values. Year to date:

| Decision | Count |
|---|---|
| Consistent with Change | 543 |
| Consistent without Change | 42 |
| **Withdrawn** | **20** |
| Statutory / Judicial Deadline | 6 |

That is a **~3.3% withdrawal base rate**, calibratable, joinable to the Federal
Register by RIN, and a leading indicator for whether a rule lands. It belongs in the
F08 base-rate book as a first entry.

---

## The same national cluster

All of these load on one polling-error term. Buying one buys most of the rest.
Useful for context and nearly worthless for accumulating independent observations.

Polling averages, Cook PVI, presidential-results-by-district, MEDSL district
returns, DDHQ forecast outputs.

Own MEDSL (CC0) because everything else derives from it, and compute PVI rather than
paying for what is a deterministic function of data already held.

### Polling, since 538 died

**FiveThirtyEight's poll CSVs are gone.** `projects.fivethirtyeight.com/polls/data/*.csv`
302s to abcnews.go.com. Wayback pins the death between 2025-03-06 and 2025-03-18.

**The backfill is recoverable.** `http://web.archive.org/web/{timestamp}id_/https://projects.fivethirtyeight.com/polls/data/{file}.csv`
returns the real CSV with the full 40-column schema (note the `id_` suffix, which
requests the raw capture rather than the rewritten page). Verified: 736 rows of 2024
generic ballot. Useful snapshots — generic ballot `20221013105339`, approval
`20241226121050`, senate `20241118073720`, president `20241011032649`, house
`20241126021208`.

**VoteHub** (`https://api.votehub.com/polls`) is the live replacement: free,
unauthenticated, CC BY 4.0, 5,607 polls through 2026-09-13. An undocumented averages
host at `polling.votehub.com/site/averages` carries 50 computed series with
confidence intervals.

> **Caveat worth catching.** The documented `/polls` approval feed stops at
> 2026-08-28 while race polling runs to 2026-09-10 and the computed approval average
> runs to today, from metadata claiming it is built from exactly that query. Either
> the average extrapolates or the public feed lags the internal database. Do not
> assume the feed contains what sits behind the published average.

**Silver Bulletin** paywalls the averages and gives away the inputs: two XLSX files
(pollster ratings, 12,300+ raw polls) plus a Google Sheets CSV of approval polls
carrying his own `weight`, `influence` and `adjusted_*` columns.

**snoutcounter** (GPL-3.0) publishes computed averages with standard errors plus six
historical generic-ballot cycles, which is the backtest spine. One maintainer, one
star: mirror it, never fetch at runtime.

**Gallup ended presidential approval tracking in February 2026**, closing a series
that ran back to FDR.

---

## Dead, confirmed by testing rather than assumed

- **ProPublica Congress API** — retired July 2024, returns 401. **Campaign Finance
  API** — every key-request path 301s to a dead store.
- **OpenSecrets API** — discontinued 2025-04-15. Bulk data survives under
  education-only CC BY-NC-SA, and that share-alike propagates to anything derived.
- **DDHQ's public polling API** — `polling.decisiondeskhq.com/api/v1/polls/*` returns
  **HTTP 200 with `[]`** on all six endpoints, with and without cycle parameters.
  A live shell serving no data.
- **lda.senate.gov died 2026-06-30**; the House equivalent dies 2026-07-31. Both
  consolidated into **lda.gov**. Any hardcoded old domain is already broken.
- `elex` (AP client, archived, wraps v2 against a v3 API), FollowTheMoney (frozen at
  2024), Google Civic representatives endpoints, Bing News Search, GDELT's GEO API.

---

## Key registration, and the trap in it

**One api.data.gov key pools 1,000 requests/hour across every federal API that uses
it.** Their wording: "For each API key, these limits are applied across all
api.data.gov API requests." **Register a separate key per service** or one busy
collector starves the others.

Per-service ceilings: Congress.gov 5,000/hr, GovInfo 36,000/hr, OpenFEC 1,000/hr
**upgradeable to 7,200/hr by emailing APIinfo@fec.gov**. `DEMO_KEY` is documented at
30/hr and enforced at 10.

### Get these three today

1. **FRED** — `fredaccount.stlouisfed.org/apikeys`, free, 120/min. Read the ALFRED
   note above before writing any backtest against it.
2. **OpenFEC** — `api.open.fec.gov/developers/`, and email APIinfo@fec.gov the same
   day for the 7,200/hr tier. Turnaround is unknown and it is a 20x difference.
3. **Congress.gov** — `api.congress.gov/sign-up/`, a **separate** key because of the
   pooling above. Unlocks `/nomination`, the highest question-density source here.

Two free extras with no reason to wait: **LDA.gov** registration (120/min, and it
fixes the dead senate domain), and the **FEC e-filing RSS feed**, which is
unauthenticated, costs no quota, and surfaces independent expenditures roughly six
minutes after filing.

---

## Client libraries

**None exists, maintained, for OpenFEC, regulations.gov, the Federal Register, or
roll-call XML.** Plain `requests` against documented REST.

`fecfile` (2025-05-03) is alive and worth having for raw `.fec` parsing.
`congressgov` 2.1.2 requires Python >= 3.13 and will not install here.

**`congress-legislators` is not on raw.githubusercontent** — that 404s. The JSON and
CSV live at `https://unitedstates.github.io/congress-legislators/legislators-current.json`;
only the YAML sits at the repo root. This is the ID crosswalk joining Congress.gov to
Senate vote XML to Voteview to FEC, so a wrong URL here blocks everything downstream.

**GovTrack's API is alive** despite its own 2016 retirement notice (431,751 bills,
votes current to 2026-09-14), but `/developers` and `/data` 404, robots.txt
disallows `/api`, `/vote_voter` 502s, and there are no terms. Fine for enrichment,
never as a resolution dependency.

**CourtListener's `/search/` endpoint works anonymously** (1.09M opinions) while
`/opinions/` returns 401. Sustained use warrants a token.
