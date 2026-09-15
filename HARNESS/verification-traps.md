# The ten named traps

Each one has cost somebody the project. Ordered by how easily it survives a casual
review.

1. **Answer-key leakage.** An agent asked to forecast a resolved question finds the
   resolution and reports a brilliant hit rate. Defence: forward-only; `write()` raises
   past close.

2. **Citation looks like evidence.** Research agents produce links that resolve
   94–100% of the time and claims the source actually supports 48–77% of the time.
   Search depth makes it worse, not better. Defence: verify claims against re-retrieved
   source text; prefer depth on few sources.

3. **Resulting bias.** Scoring the outcome instead of the decision. Defence: no verdict
   on a single question, ever; cluster-level only.

4. **Correlated events read as independent.** The error in three costumes at once.
   Defence: cluster-level inference raises on forecast-level input.

5. **Overfitting reads as alpha.** Defence: pre-registration with git-proven ordering,
   plus an independent evaluator.

6. **Self-critique reads as verification.** A model reviewing its own output with no
   new information is a second sample from the same distribution. Intrinsic
   self-correction degrades reasoning performance monotonically. Defence: fresh
   context, different model, refutation-first prompt.

7. **Capital lock-up reads as free.** A market resolving in fourteen months holds the
   capital for fourteen months. Defence: annualise.

8. **Closing price leaks backward.** Defence: price recorded at forecast time; later
   prices raise on any scoring path.

9. **One model reads as N=1.** The analyses you would have run given different data
   count too. Choosing to cluster by state rather than race, to drop markets under a
   liquidity floor, to switch scoring rules — each would have gone differently on
   different data. Defence: the trial log, and pre-registration.

10. **Repeated holdout checks read as free.** With k look-and-adjust cycles against a
    holdout of size n, illusion of order sqrt(k/n) is available to someone doing
    nothing but guessing. At 200 resolved questions and 50 cycles that is 0.5, which is
    the whole signal. Defence: ladder discipline (record a new best only on an
    improvement exceeding eta, round reported scores to eta) and batched evaluation,
    since statistical cost scales with rounds of adaptivity rather than queries.
