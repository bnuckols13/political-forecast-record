# Evaluator Rubric

Score a session's output across six dimensions, 0–2 each (0 absent, 1 partial,
2 solid). The evaluator runs this, not the generator that produced the work.
12/12 is a clean session. Anything scoring 0 blocks the clean-state check until
addressed.

| # | Dimension | 0 | 1 | 2 |
|---|-----------|---|---|---|
| 1 | **Correctness** | doesn't do what was asked | works on the happy path only | works, edge cases considered |
| 2 | **Verification** | claimed done, no proof | verified by hand, not repeatable | verification command exists and passes |
| 3 | **Scope discipline** | touched unrelated things | minor drift | did exactly the one unit (WIP=1) |
| 4 | **Reliability** | breaks on re-run | works once | idempotent, survives a cold start |
| 5 | **Maintainability** | opaque, no docs | code clear, docs stale | code + docs updated together |
| 6 | **Handoff readiness** | next session must reconstruct | partial notes | PROGRESS + handoff let the next session start cold |

**Generator/evaluator split:** the agent that wrote the work does not fill this
in. Use a separate subagent, or a different model, for anything that matters.

---

## How to run the evaluator as a separate agent

The split is only real if a *different agent* does the checking. Running the
checker yourself, in the context that wrote the work, is a self-audit — the
generator wearing a second hat. Spawn a fresh subagent instead.

1. **Hand it the standard, not your opinion.** Give the evaluator the source of
   truth (the test command, the two-source rule, or for prose the `STYLE_GUIDE.md`
   + the project's voice exemplar + the correct prose skill), the artifact to
   judge, and nothing about how you feel about it.
2. **Ask for a verdict, not a rewrite.** The evaluator returns pass/fail plus every
   reach, near-miss, and violation, located precisely. It does not fix; fixing is
   the generator's job on the next pass. (Keeps the roles clean.)
3. **Prefer a different model or a skeptical framing** for anything high-stakes.
   A refutation-first prompt ("find why this is NOT clean") beats a confirmation
   prompt.
4. **Record the verdict as the evidence.** The ledger row's evidence field holds
   the evaluator's finding, not the generator's say-so.

**Prose specifically.** The gate is an independent evaluator subagent running
`/journalism-prose`, `/academic-prose`, `/literary-prose`, or `/erotic-prose`
against the STYLE_GUIDE and the voice exemplar, judging the positive standard
("would the author have written this sentence?") — not a ban-list scan the writer
runs on itself. The subagent that wrote the sentence never clears the sentence.
A "0 violations, no edits needed" verdict especially wants an independent agent:
that is the exact conclusion a self-auditing generator is biased to reach.
