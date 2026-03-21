# Breakout Labels

## Purpose

A breakout label converts next-season outcomes into a research target that can be compared against prior-season signals.

For PR1, the label definition is intentionally simple and explicitly marked as a **proposed v1 placeholder** for wide receivers.

## Proposed v1 WR breakout label

A WR is labeled as a breakout in outcome season `Y+1` if all of the following are true:

1. The player finishes with at least **200.0 PPR fantasy points**.
2. The player averages at least **12.0 PPR points per game**.
3. The player plays at least **12 games**.
4. The player did **not** already exceed 200.0 PPR fantasy points in the feature season `Y`.

## Why this is a placeholder

This definition is useful for scaffolding because it is:

- explicit
- deterministic
- easy to test
- easy to replace in future PRs

It is **not** a claim that this is the best or only breakout definition.

## Future refinements for later PRs

Possible future label variants include:

- percentile-based finish thresholds
- ADP-relative outperformance
- role-change breakouts
- age-adjusted breakouts
- cohort-specific thresholds
- multi-tier labels such as soft breakout vs. hard breakout

## Timestamp safety rule

Breakout labels are computed from the **next season's realized outcomes**, but they are used **only for evaluation**, never as model inputs. Any feature built from outcome-season data would violate the repository's research protocol.
