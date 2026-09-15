"""Cluster keys and the election watchlist.

The `cluster` field on every journal record is the unit of evidence. F05 made
that field load-bearing: significance is computed across clusters, never across
forecasts, so mislabelling one is not a tidiness problem, it is a wrong answer.

-------------------------------------------------------------------------------
The rule

  A cluster is a set of outcomes that share a dominant common error term.

If being wrong about one outcome makes you wrong about the others in the same
direction and for the same reason, they belong to one cluster. Every US House,
Senate and governor race on 2026-11-03 resolves against one national polling
environment, so they are `us-2026-midterms` collectively, not four hundred
observations.

Applying it:

  SAME cluster    All races on one national election night in one country.
                  Multiple questions about the same race (winner, margin, seat
                  count). Turnout and result questions for the same election.

  SEPARATE        Different countries, even in the same month. Different
                  election nights in the same country separated by months.
                  A process question whose resolution does not depend on a
                  vote count at all.

  JUDGEMENT       France 2027 presidential (April) and legislative (June). The
                  legislative follows the presidential and is heavily
                  conditioned on it, but they are two months apart with
                  different electorates and can diverge sharply. Recorded as two
                  clusters with the dependence noted, because treating them as
                  one discards real information while treating them as fully
                  independent overstates the denominator by exactly one. Erring
                  toward separate is the aggressive choice, so the note matters.

The convention is `<iso2>-<year>-<body>`: `nz-2026-general`, `us-2026-midterms`,
`fr-2027-presidential`. Lowercase, hyphenated, stable forever once used, because
a renamed cluster silently splits a record that was one observation.

-------------------------------------------------------------------------------
The watchlist

Chosen for independence per unit of effort rather than for importance. A close
race in a country nobody else is pricing is worth more to this project than a
famous one, on both of F05's axes at once: it is a separate cluster, and it is
thin enough that a ten-point disagreement is plausible.

Slip risk is recorded because an election that does not happen is not a
resolution. Haiti, South Sudan, Guinea-Bissau and Libya are on the list as
warnings, not targets.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Election:
    cluster: str
    country: str
    date: str  # ISO date, or YYYY-MM when only the month is fixed
    kind: str
    note: str
    slip_risk: str = "low"  # low | moderate | high | near-certain
    search_terms: tuple[str, ...] = field(default_factory=tuple)

    @property
    def scheduled(self) -> bool:
        return self.slip_risk in ("low", "moderate")

    @property
    def sort_key(self) -> str:
        """A date that orders correctly against both formats.

        Naive string comparison puts a month-only date ahead of every dated
        election in the same month, because "2027-06" is a prefix of
        "2027-06-06" and prefixes sort first. France's legislative election,
        known only to be in June, would jump ahead of Mexico's on June 6 for no
        reason other than that we know less about it.

        When only the month is known the expected day is mid-month, so that is
        what it sorts as. The ordering between a mid-month estimate and a real
        date in the same month is genuinely unknown; this makes it deterministic
        and documented rather than an accident of string comparison.
        """
        return self.date if len(self.date) == 10 else f"{self.date}-15"


# Ordered by date. Not exhaustive: this is the tractable subset, not the calendar.
WATCHLIST: tuple[Election, ...] = (
    Election("il-2026-knesset", "Israel", "2026-10-27", "legislative",
             "Coalition formation resolves after the vote and is separately forecastable.",
             search_terms=("Israel election", "Knesset", "Netanyahu")),
    Election("us-2026-midterms", "United States", "2026-11-03", "legislative",
             "One cluster covering every federal and state race that night. The "
             "correlated-risk baseline, and approximately one observation.",
             search_terms=("Senate 2026", "House 2026", "midterms")),
    Election("nz-2026-general", "New Zealand", "2026-11-07", "legislative",
             "MMP coalition arithmetic with dense public polling. Four days after "
             "the US midterms and completely independent of them. The best "
             "instrumented target in the near window.",
             search_terms=("New Zealand election", "NZ general election", "Labour National")),
    Election("cv-2026-presidential", "Cape Verde", "2026-11-15", "presidential",
             "Stable democracy, thin polling, almost certainly unpriced.",
             search_terms=("Cape Verde",)),
    Election("ch-2026-referendums", "Switzerland", "2026-11-29", "referendum",
             "Not an election, but cleanly independent, well polled by gfs.bern, "
             "and resolving on a fixed date.",
             search_terms=("Swiss referendum", "Switzerland referendum")),
    Election("gm-2026-presidential", "Gambia", "2026-12-05", "presidential",
             "Barrow incumbency against a fragmented opposition.",
             search_terms=("Gambia",)),
    Election("gw-2026-general", "Guinea-Bissau", "2026-12-06", "general",
             "Coup-interrupted in November 2025.", slip_risk="high",
             search_terms=("Guinea-Bissau",)),
    Election("ht-2026-general", "Haiti", "2026-12-13", "general",
             "No elected officials seated since 2023. Whether it happens at all is "
             "the more forecastable question than who wins.", slip_risk="high",
             search_terms=("Haiti election",)),
    Election("ss-2026-general", "South Sudan", "2026-12-22", "general",
             "Postponed in 2015, 2018, 2022 and 2024.", slip_risk="high",
             search_terms=("South Sudan",)),
    Election("ng-2027-general", "Nigeria", "2027-01-16", "general",
             "Revised from February by the Electoral Act 2026. Three-way "
             "fragmentation and weak polling, so high variance both ways.",
             search_terms=("Nigeria election", "Nigeria president")),
    Election("de-2027-presidential", "Germany", "2027-01-30", "presidential",
             "Indirect, decided by Federal Convention arithmetic. Solvable by "
             "counting, which makes it a clean calibration check.",
             search_terms=("German president", "Bundesversammlung")),
    Election("sv-2027-general", "El Salvador", "2027-02-28", "general",
             "Moved up from 2029. The winner is near-certain; margin and seat "
             "count are the forecastable quantities.",
             search_terms=("El Salvador", "Bukele")),
    Election("ee-2027-riigikogu", "Estonia", "2027-03", "legislative",
             "Reform Party collapsing in polling with EKRE and Isamaa rising. "
             "Excellent public polling for a small country.",
             search_terms=("Estonia election", "Riigikogu")),
    Election("fr-2027-presidential", "France", "2027-04", "presidential",
             "Two rounds. Macron term-limited, RN polling first, left fragmented. "
             "Deep polling and heavy English coverage, so likely well priced.",
             search_terms=("France president", "French election", "Le Pen", "RN")),
    Election("fi-2027-eduskunta", "Finland", "2027-04-18", "legislative",
             "Four-party competitive field with reliable Yle polling.",
             search_terms=("Finland election", "Finnish parliamentary")),
    Election("mx-2027-deputies", "Mexico", "2027-06-06", "legislative",
             "Sheinbaum midterm. Whether Morena holds its supermajority is the "
             "live question.",
             search_terms=("Mexico election", "Morena")),
    Election("fr-2027-legislative", "France", "2027-06", "legislative",
             "Expected but not yet called; the incoming president sets the date. "
             "Conditional on fr-2027-presidential and strongly influenced by it. "
             "Recorded separately with that dependence noted.",
             slip_risk="moderate",
             search_terms=("France legislative", "Assemblee nationale")),
    Election("gt-2027-general", "Guatemala", "2027-06-27", "general",
             "Runoff likely in August. 2023 showed the establishment can be beaten "
             "and that candidate disqualification is a live mechanism.",
             search_terms=("Guatemala election",)),
    Election("gr-2027-legislative", "Greece", "2027-07", "legislative",
             "Statutory deadline rather than a called date. New Democracy "
             "weakening, PASOK fragmenting.", slip_risk="moderate",
             search_terms=("Greece election", "Greek election")),
    Election("ke-2027-general", "Kenya", "2027-08-10", "general",
             "Ruto's first re-election bid after the 2024 protests and the "
             "Gachagua impeachment. Constitutionally fixed date, real uncertainty, "
             "decent domestic polling.",
             search_terms=("Kenya election", "Ruto")),
    Election("es-2027-general", "Spain", "2027-08", "legislative",
             "Statutory deadline. Sanchez minority under corruption pressure, so a "
             "snap election earlier is plausible.", slip_risk="moderate",
             search_terms=("Spain election", "Sanchez")),
    Election("ar-2027-general", "Argentina", "2027-10-24", "general",
             "Milei's re-election bid with the peso and the inflation path as the "
             "driver. Heavy English coverage.",
             search_terms=("Argentina election", "Milei")),
    Election("ch-2027-federal", "Switzerland", "2027-10-24", "legislative",
             "Proportional, stable, precisely pollable. Good calibration fodder "
             "precisely because it is boring.",
             search_terms=("Swiss election", "Swiss federal")),
    Election("pl-2027-sejm", "Poland", "2027-11", "legislative",
             "Tusk coalition against PiS and Konfederacja under cohabitation "
             "stress after Nawrocki's 2025 win.", slip_risk="moderate",
             search_terms=("Poland election", "Sejm", "Tusk")),
)

# The twelve with the best independence per unit of effort: five regions, almost
# no shared driver, all with usable English-language polling.
SHORTLIST = (
    "nz-2026-general", "ee-2027-riigikogu", "fi-2027-eduskunta", "fr-2027-presidential",
    "ch-2027-federal", "ke-2027-general", "ar-2027-general", "gt-2027-general",
    "mx-2027-deputies", "ng-2027-general", "pl-2027-sejm", "gr-2027-legislative",
)


def by_cluster(key: str) -> Election | None:
    return next((e for e in WATCHLIST if e.cluster == key), None)


def upcoming(before: str) -> tuple[Election, ...]:
    """Elections dated at or before `before` (ISO date or YYYY-MM prefix)."""
    cutoff = before if len(before) == 10 else f"{before}-15"
    return tuple(e for e in WATCHLIST if e.sort_key <= cutoff)


def tractable() -> tuple[Election, ...]:
    """Everything not carrying high slip risk. An election that does not happen
    is not a resolution, and a forecast on one is a forecast you cannot score."""
    return tuple(e for e in WATCHLIST if e.scheduled)


def shortlist() -> tuple[Election, ...]:
    return tuple(e for e in WATCHLIST if e.cluster in SHORTLIST)
