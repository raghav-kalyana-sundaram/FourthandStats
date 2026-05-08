# Simulation Methodology

> Placeholder — Phase 6 (future). Not yet implemented.

The simulation layer will use team EPA ratings and their historical variance as inputs to Monte Carlo game simulations.

Key design decisions (to be finalized):
- EPA-based win probability model or logistic regression on point differential
- Variance model: rolling within-season std dev of per-game EPA
- Correlation between offensive EPA variance and defensive EPA variance
- Home field advantage treatment
- Playoff-specific adjustments (if any)
