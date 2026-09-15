# Clean-State Checklist — crypto-trading

Run before ending any session. Session completion = the unit passed its
verification AND every box below is checked. Missing either means the session is
not done, however finished the work looks.

## Every session
- [ ] The unit I worked is at its terminal state in `strategy_ledger.json` (`passing` for a build unit; a real strategy-state transition), with evidence recorded — or honestly marked `blocked` / `active` with the reason.
- [ ] No orphaned artifacts: debug prints, commented-out blocks, stray TODO markers, scratch files.
- [ ] `PROGRESS.md` updated: current priority, blockers, running-log line for today.
- [ ] `./init.sh verify` passes from a cold state.
- [ ] Changes committed. One logical operation per commit. Docs updated in the same commit as the code they describe.

## Trading profile (the money-specific lines)
- [ ] **No secrets committed.** `git diff --cached` shows no key, secret, seed, or `.env`. `.gitignore` still covers them.
- [ ] **Point-in-time integrity intact.** No prior day's snapshot was rewritten (`git status` shows only today's snapshot added, never an older one modified). No signal I touched reads a data field unknowable at bar t.
- [ ] **No strategy advanced on my own say-so.** Any move out of `backtested` carries an independent-evaluator verdict in `docs/evals/`, and the pre-registered metric was committed before the result was seen.
- [ ] **No live-order path shipped without limits.** If any code can place a real order, position-size + max-drawdown limits and a kill-switch exist and are tested. (Until the paper gate, no such path should exist at all.)
- [ ] Pre-existing tests still pass — accountable for what I did not break.
- [ ] No `print()` / `breakpoint()` left behind in library code.
