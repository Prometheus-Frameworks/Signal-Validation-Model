# `late_veteran_wr_breakout_v0`

## Purpose and authority

`late_veteran_wr_breakout_v0` is a deterministic research slice for testing a narrow historical question: which WRs entering career year three or later had small supported roles and then broke out alongside a material increase in target share?

It is separate from the repository's generic breakout label. It produces a retrospective observed-row backtest and an unordered 2026 research packet. It does not produce a live ranking, projection, recommendation, promoted artifact, Forecast input, Fantasy consumer, or autonomous news feed.

The preregistered primary definition below was frozen in [Signal-Validation-Model #16](https://github.com/Prometheus-Frameworks/Signal-Validation-Model/issues/16) before the v0 results were inspected. Sensitivity results are diagnostic and cannot silently replace the primary definition.

The implementation branch was cut from Signal-Validation-Model commit
`0b8f600a4779df4c64420844649b732edeb6c3e2`.

## Pinned historical input

The historical source is TIBER-Data's promoted `player_season_coverage_v0` artifact at this exact identity:

| Property | Pin |
|---|---|
| Repository | `Prometheus-Frameworks/TIBER-Data` |
| Source snapshot commit | `3606b6a0af5add2ebea1f7de141a299cebe70a34` |
| Artifact last-changed commit | `711d6ee158d4e3bd116d1df4d76dea282200454d` |
| Path | `exports/promoted/nfl/player_season_coverage_v0.json` |
| Git blob | `f7b2918b978d842cd8753a7f3dedd3836934859b` |
| SHA-256 | `d45f612b207085df00b4b080e4f55ce1abbd060dcbf30b0bee777ff833ddd8ac` |
| Promotion review | `TIBER-Data#202` |
| Promotion decision | `promote_player_season_coverage_v0_2021_2025` |
| Window | 2021–2025, `REG`, QB/RB/WR/TE |
| Grain | `player_id + season + season_type` |
| Counts | 3,016 player-season rows; 1,191 WR rows |

The build consumes the committed promoted bytes. It does not rerun the network-backed nflreadpy builders. The adapter verifies the content digest and required nested field shape before analysis.

### Field semantics used by v0

- `player_id` is the GSIS identifier and is the canonical join key.
- `rookie_year` is TIBER-Data's source-backed `nflreadpy.load_players().rookie_season` value.
- `career_year = season - rookie_year + 1`. This is calendar career year, not recorded-season order or an accrued-service-credit calculation.
- PPR PPG is `production_summary.season_ppg`, published to two decimal places.
- Target share is `usage_summary.target_share`, published to four decimal places.
- Outcome games are `games_played`.
- Air-yard share and WOPR are retained as inspectable context but do not decide primary eligibility or the outcome labels.

Threshold comparisons use the published promoted values; the research layer does not manufacture additional precision.

## Frozen primary definition

### Football-archetype eligibility

A feature-season row is `football_archetype_eligible` only when all of the following are supported:

1. `position == WR`;
2. `feature_career_year >= 2`;
3. `target_career_year = feature_career_year + 1` and `target_career_year >= 3`;
4. feature PPR PPG is `< 7.0`;
5. feature target share is `< 0.10`;
6. every calendar season from the player's source-backed rookie year through the feature season has a supported row;
7. no earlier supported season has PPR PPG `>= 10.0` or target share `>= 0.15`.

The historical artifact begins in 2021. A player whose rookie year precedes 2021 is `prior_history_incomplete`, not eligible or ineligible. A missing player-season row is not converted to a zero and is not proof of inactivity, injury, roster status, or absence from the league.

### Market-qualified eligibility

`market_qualified_eligible` adds a comparable governed redraft market observation: overall ADP `>= 200`, or explicitly unranked within a declared source population and configuration.

No governed dated redraft ADP source is bound to v0. Market state therefore remains `unavailable`, and a football-only candidate must not be described as deeply undrafted. Missing market evidence neither qualifies nor disqualifies a player.

### Outcome labels

Outcome fields never participate in feature-side eligibility.

An observed outcome row is evaluation-valid only when its player identity,
season, rookie year, and career year agree with the feature-side derived target
season/tenure. A mismatch is an explicit outcome tenure conflict and coverage
exclusion; it does not retroactively change feature eligibility.

- `fantasy_breakout`: outcome games `>= 8`, outcome PPR PPG `>= 10.0`, and PPG increase `>= 3.0`.
- `role_expansion`: outcome target share `>= 0.15` and target-share increase `>= 0.05`. State is `confirmed`, `not_confirmed`, or `unavailable`.
- `archetype_hit`: `fantasy_breakout == true` and `role_expansion == confirmed`.

Each component is published separately. There is no opaque score.

### Sensitivity grid

The diagnostic grid compares:

- feature PPG ceilings: `5`, `7`, `9`;
- feature target-share ceilings: `0.08`, `0.10`, `0.12`;
- outcome PPG floors: `10`, `12`;
- target-share increases: `0.04`, `0.05`, `0.06`, `0.08`; and
- market cutoffs, only if supported: ADP `180`, `200`, `240`, and explicitly unranked.

Sensitivity output may motivate a separately versioned definition. It cannot rewrite v0 after observing the same outcomes.

## Evaluation universe and completeness limits

The full ledger contains every promoted observed WR stat row. The declared
population is the structural Y3+ screen: a source-backed feature career year of
at least two and a derived target career year of at least three. Rows below that
tenure boundary remain visible as `outside_declared_population`; they are not
coverage exclusions.

Within the declared population, complete rookie-to-feature exposure, valid
required feature fields, and a valid adjacent-season outcome are required for
the evaluable universe. Rows that fail one of those support requirements are
coverage exclusions, not false negatives. The promoted ledger is not a complete
historical active-roster census, and the resulting base rate is not a leaguewide
base rate.

The strict history rule has material consequences:

- 2021→2022 contains no fully supported Y3+ evaluations because every such player necessarily began before the 2021 artifact boundary.
- Jauan Jennings' 2023→2024 pair can reproduce the observed breakout and role-expansion labels, but his 2020 rookie season is outside the artifact. He remains a provisional positive control with `prior_history_incomplete`.
- Parker Washington's 2024→2025 control has continuous supported history and can be fully evaluated.
- A known player without a required feature or outcome row remains in the exclusion ledger with an explicit unavailable state rather than disappearing.

The population ledger uses explicit states including `eligible`, `ineligible`, `prior_history_incomplete`, `tenure_conflict`, `unavailable_feature_row`, `unresolved_identity`, `market_unavailable`, and `outside_declared_population`.

## Role and opportunity limits

Target share is available for every observed WR row and is sufficient for the v0 outcome-side role-expansion label. It does not describe route-level process.

The promoted input has no source-backed `routes_run`, `route_participation`, `snap_share`, red-zone targets, red-zone carries, or games-missed values. Those fields are unavailable on every WR row. They cannot influence eligibility, support a current role claim, or be replaced with zero.

Current official depth-chart ingestion, future route allocation, injury-contingency share, and depth-chart-to-usage translation are outside this research contract.

## 2026 pilot receipt boundary

The manual pilot input is:

```text
data/raw/late_veteran_wr_breakout_2026_pilot_receipts_v0.json
```

Its immutable evidence cutoff is `2026-08-09T19:28:02Z`, the creation timestamp of issue #16. It contains two pre-cutoff Baltimore Ravens editorial receipts for Devontez Walker. Their claims are paraphrased and classified as `candidate_external_observation`; they are not promoted TIBER truth.

The checked-in packet is byte-pinned to SHA-256
`114af8226458759c15f89428601b6cf007080387f35a8fe83667db52ba22f3c8`.
The builder verifies that digest before parsing the receipt JSON.

The pilot output keeps five classes separate:

- `observed`: governed historical rows and explicitly cited candidate external observations;
- `inferred`: research interpretation whose supporting observations are named;
- `operator`: a separately supplied operator thesis or correction; none is supplied in the raw v0 packet;
- `forecast`: `not_activated` unless separately governed Forecast evidence exists; and
- `unknown`: unresolved routes, snaps, target allocation, market state, injury-contingency share, and role translation.

Walker is the declared pilot. Roman Wilson, Jordan Whittington, Luke McCaffrey, Jacob Cowing, Tyquan Thornton, and Ryan Flournoy are declared comparison identities. The packet is unordered and contains no ranking field; comparison order is not a ranking.

## CLI

Run the bounded build with the exact command surface:

```bash
signal-validation build-late-veteran-wr-breakout-v0 \
  --player-season-input ../TIBER-Data/exports/promoted/nfl/player_season_coverage_v0.json \
  --pilot-receipts-input data/raw/late_veteran_wr_breakout_2026_pilot_receipts_v0.json \
  --output-dir outputs
```

`--pilot-receipts-input` defaults to the checked-in raw JSON path above. Passing it explicitly makes the receipt identity visible in reproducibility logs.

## Outputs

One deterministic run writes exactly these six research artifacts:

1. `outputs/validation_reports/late_veteran_wr_breakout_v0_definition.json`
2. `outputs/validation_reports/late_veteran_wr_breakout_v0_summary.json`
3. `outputs/validation_reports/late_veteran_wr_breakout_v0_historical_pairs.csv`
4. `outputs/case_studies/late_veteran_wr_breakout_v0_examples.md`
5. `outputs/case_studies/late_veteran_wr_breakout_2026_pilot.json`
6. `outputs/validation_reports/late_veteran_wr_breakout_v0_receipt.json`

The receipt binds input paths, commit and content pins, cutoff, frozen thresholds, implementation identity, and output digests. No output belongs under `outputs/candidate_rankings/`.

The summary ends in exactly one terminal decision:

```text
late_veteran_wr_breakout_v0_research_validated
late_veteran_wr_breakout_v0_requires_data_or_definition_followup
late_veteran_wr_breakout_v0_blocked
```

## Checked-in v0 result

Against the pinned 2021–2025 input, the full ledger contains 1,191 observed WR
rows. Of those, 198 are outside the declared Y3+ population and 993 are inside
it. The declared population contains 869 coverage exclusions—754 with
incomplete prior history and 115 with a missing adjacent outcome—leaving 124
evaluable feature/outcome pairs.

The frozen football-only screen yields 2 true positives, 50 false positives, 7
false negatives, and 65 true negatives: precision `0.0385`, recall `0.2222`,
and an evaluable-population archetype-hit rate of `0.0726`. These are
descriptive results for the supported stat-row population, not leaguewide
estimates.

The terminal decision is
`late_veteran_wr_breakout_v0_requires_data_or_definition_followup`. Governed
comparable redraft market evidence is unavailable, route/snap role fields have
zero coverage, and sensitivity output remains diagnostic only. No alternate
threshold set is selected from these outcomes.

## Non-promotion boundary

All six outputs are research artifacts. This work authorizes no merge, promotion, deployment, Forecast binding, Fantasy activation, Player State Card, ledger mutation, public recommendation, automated ingestion, or advice. Any downstream consumer requires a separate governed activation.
