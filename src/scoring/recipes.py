"""Explicit deterministic WR scoring recipes used by PR5 comparisons."""

from __future__ import annotations

from dataclasses import dataclass

COMPONENT_NAMES = (
    "usage_signal",
    "efficiency_signal",
    "development_signal",
    "stability_signal",
    "cohort_signal",
    "role_signal",
    "penalty_signal",
)


@dataclass(frozen=True)
class RecipeThresholds:
    usage_targets_per_game_floor: float
    usage_targets_per_game_ceiling: float
    usage_target_share_floor: float
    usage_target_share_ceiling: float
    efficiency_ppg_per_target_floor: float
    efficiency_ppg_per_target_ceiling: float
    efficiency_ppg_floor: float
    efficiency_ppg_ceiling: float
    development_finish_anchor: float
    development_finish_floor: float
    development_finish_ceiling: float
    development_expected_gap_floor: float
    development_expected_gap_ceiling: float
    cohort_ppg_delta_floor: float
    cohort_ppg_delta_ceiling: float
    cohort_finish_delta_floor: float
    cohort_finish_delta_ceiling: float
    cohort_count_floor: float
    cohort_count_ceiling: float
    role_route_participation_floor: float
    role_route_participation_ceiling: float
    role_target_share_floor: float
    role_target_share_ceiling: float
    role_air_yard_share_floor: float
    role_air_yard_share_ceiling: float
    role_routes_consistency_floor: float
    role_routes_consistency_ceiling: float
    role_target_earning_floor: float
    role_target_earning_ceiling: float
    role_opportunity_concentration_floor: float
    role_opportunity_concentration_ceiling: float
    stability_games_floor: float
    stability_games_ceiling: float
    stability_total_ppr_floor: float
    stability_total_ppr_ceiling: float
    penalty_finish_anchor: float
    penalty_finish_floor: float
    penalty_finish_ceiling: float
    penalty_games_anchor: float
    penalty_games_floor: float
    penalty_games_ceiling: float
    penalty_target_share_anchor: float
    penalty_target_share_floor: float
    penalty_target_share_ceiling: float


@dataclass(frozen=True)
class SignalRecipe:
    name: str
    description: str
    scoring_version: str
    component_weights: dict[str, float]
    usage_weights: dict[str, float]
    efficiency_weights: dict[str, float]
    development_weights: dict[str, float]
    stability_weights: dict[str, float]
    cohort_weights: dict[str, float]
    role_weights: dict[str, float]
    penalty_weights: dict[str, float]
    thresholds: RecipeThresholds


def _validate_unit_weight_group(group_name: str, weights: dict[str, float]) -> None:
    total = round(sum(weights.values()), 8)
    if total != 1.0:
        raise ValueError(f"{group_name} weights must sum to 1.0, got {total}")
    if any(weight < 0 for weight in weights.values()):
        raise ValueError(f"{group_name} weights must all be non-negative")


def _validate_threshold_pair(name: str, floor: float, ceiling: float) -> None:
    if ceiling <= floor:
        raise ValueError(f"{name} ceiling must be greater than floor")


def validate_recipe(recipe: SignalRecipe) -> None:
    if set(recipe.component_weights) != set(COMPONENT_NAMES):
        raise ValueError(
            f"recipe {recipe.name} component_weights must exactly match {sorted(COMPONENT_NAMES)}"
        )
    if recipe.component_weights["penalty_signal"] > 0:
        raise ValueError("penalty_signal must be zero or negative in final component weights")

    _validate_unit_weight_group("usage", recipe.usage_weights)
    _validate_unit_weight_group("efficiency", recipe.efficiency_weights)
    _validate_unit_weight_group("development", recipe.development_weights)
    _validate_unit_weight_group("stability", recipe.stability_weights)
    _validate_unit_weight_group("cohort", recipe.cohort_weights)
    _validate_unit_weight_group("role", recipe.role_weights)
    _validate_unit_weight_group("penalty", recipe.penalty_weights)

    thresholds = recipe.thresholds
    _validate_threshold_pair(
        "usage_targets_per_game",
        thresholds.usage_targets_per_game_floor,
        thresholds.usage_targets_per_game_ceiling,
    )
    _validate_threshold_pair(
        "usage_target_share",
        thresholds.usage_target_share_floor,
        thresholds.usage_target_share_ceiling,
    )
    _validate_threshold_pair(
        "efficiency_ppg_per_target",
        thresholds.efficiency_ppg_per_target_floor,
        thresholds.efficiency_ppg_per_target_ceiling,
    )
    _validate_threshold_pair(
        "efficiency_ppg",
        thresholds.efficiency_ppg_floor,
        thresholds.efficiency_ppg_ceiling,
    )
    _validate_threshold_pair(
        "development_finish",
        thresholds.development_finish_floor,
        thresholds.development_finish_ceiling,
    )
    _validate_threshold_pair(
        "development_expected_gap",
        thresholds.development_expected_gap_floor,
        thresholds.development_expected_gap_ceiling,
    )
    _validate_threshold_pair(
        "cohort_ppg_delta",
        thresholds.cohort_ppg_delta_floor,
        thresholds.cohort_ppg_delta_ceiling,
    )
    _validate_threshold_pair(
        "cohort_finish_delta",
        thresholds.cohort_finish_delta_floor,
        thresholds.cohort_finish_delta_ceiling,
    )
    _validate_threshold_pair(
        "cohort_count",
        thresholds.cohort_count_floor,
        thresholds.cohort_count_ceiling,
    )
    _validate_threshold_pair(
        "role_route_participation",
        thresholds.role_route_participation_floor,
        thresholds.role_route_participation_ceiling,
    )
    _validate_threshold_pair(
        "role_target_share",
        thresholds.role_target_share_floor,
        thresholds.role_target_share_ceiling,
    )
    _validate_threshold_pair(
        "role_air_yard_share",
        thresholds.role_air_yard_share_floor,
        thresholds.role_air_yard_share_ceiling,
    )
    _validate_threshold_pair(
        "role_routes_consistency",
        thresholds.role_routes_consistency_floor,
        thresholds.role_routes_consistency_ceiling,
    )
    _validate_threshold_pair(
        "role_target_earning",
        thresholds.role_target_earning_floor,
        thresholds.role_target_earning_ceiling,
    )
    _validate_threshold_pair(
        "role_opportunity_concentration",
        thresholds.role_opportunity_concentration_floor,
        thresholds.role_opportunity_concentration_ceiling,
    )
    _validate_threshold_pair(
        "stability_games",
        thresholds.stability_games_floor,
        thresholds.stability_games_ceiling,
    )
    _validate_threshold_pair(
        "stability_total_ppr",
        thresholds.stability_total_ppr_floor,
        thresholds.stability_total_ppr_ceiling,
    )
    _validate_threshold_pair(
        "penalty_finish",
        thresholds.penalty_finish_floor,
        thresholds.penalty_finish_ceiling,
    )
    _validate_threshold_pair(
        "penalty_games",
        thresholds.penalty_games_floor,
        thresholds.penalty_games_ceiling,
    )
    _validate_threshold_pair(
        "penalty_target_share",
        thresholds.penalty_target_share_floor,
        thresholds.penalty_target_share_ceiling,
    )


def _recipe(
    *,
    name: str,
    description: str,
    scoring_version: str,
    component_weights: dict[str, float],
    usage_weights: dict[str, float],
    efficiency_weights: dict[str, float],
    development_weights: dict[str, float],
    stability_weights: dict[str, float],
    cohort_weights: dict[str, float],
    role_weights: dict[str, float],
    penalty_weights: dict[str, float],
    thresholds: RecipeThresholds,
) -> SignalRecipe:
    recipe = SignalRecipe(
        name=name,
        description=description,
        scoring_version=scoring_version,
        component_weights=component_weights,
        usage_weights=usage_weights,
        efficiency_weights=efficiency_weights,
        development_weights=development_weights,
        stability_weights=stability_weights,
        cohort_weights=cohort_weights,
        role_weights=role_weights,
        penalty_weights=penalty_weights,
        thresholds=thresholds,
    )
    validate_recipe(recipe)
    return recipe


BASE_THRESHOLDS = RecipeThresholds(
    usage_targets_per_game_floor=4.0,
    usage_targets_per_game_ceiling=10.0,
    usage_target_share_floor=0.12,
    usage_target_share_ceiling=0.30,
    efficiency_ppg_per_target_floor=0.8,
    efficiency_ppg_per_target_ceiling=2.5,
    efficiency_ppg_floor=6.0,
    efficiency_ppg_ceiling=18.0,
    development_finish_anchor=48.0,
    development_finish_floor=0.0,
    development_finish_ceiling=36.0,
    development_expected_gap_floor=0.0,
    development_expected_gap_ceiling=4.0,
    cohort_ppg_delta_floor=0.0,
    cohort_ppg_delta_ceiling=6.0,
    cohort_finish_delta_floor=0.0,
    cohort_finish_delta_ceiling=36.0,
    cohort_count_floor=1.0,
    cohort_count_ceiling=24.0,
    role_route_participation_floor=0.45,
    role_route_participation_ceiling=0.95,
    role_target_share_floor=0.10,
    role_target_share_ceiling=0.30,
    role_air_yard_share_floor=0.08,
    role_air_yard_share_ceiling=0.35,
    role_routes_consistency_floor=0.55,
    role_routes_consistency_ceiling=0.95,
    role_target_earning_floor=0.12,
    role_target_earning_ceiling=0.42,
    role_opportunity_concentration_floor=0.18,
    role_opportunity_concentration_ceiling=0.52,
    stability_games_floor=8.0,
    stability_games_ceiling=17.0,
    stability_total_ppr_floor=80.0,
    stability_total_ppr_ceiling=260.0,
    penalty_finish_anchor=12.0,
    penalty_finish_floor=0.0,
    penalty_finish_ceiling=12.0,
    penalty_games_anchor=11.0,
    penalty_games_floor=0.0,
    penalty_games_ceiling=11.0,
    penalty_target_share_anchor=0.14,
    penalty_target_share_floor=0.0,
    penalty_target_share_ceiling=0.14,
)


RECIPES: dict[str, SignalRecipe] = {
    "baseline_v1": _recipe(
        name="baseline_v1",
        description="PR4 baseline score carried forward as the explicit benchmark recipe.",
        scoring_version="wr_signal_score_v1",
        component_weights={
            "usage_signal": 0.35,
            "efficiency_signal": 0.20,
            "development_signal": 0.20,
            "stability_signal": 0.15,
            "cohort_signal": 0.0,
            "role_signal": 0.0,
            "penalty_signal": -0.10,
        },
        usage_weights={"targets_per_game": 0.55, "target_share": 0.45},
        efficiency_weights={"ppg_per_target": 0.60, "ppg": 0.40},
        development_weights={"finish_room": 0.50, "expected_gap": 0.50},
        stability_weights={"games_played": 0.65, "total_ppr": 0.35},
        cohort_weights={"ppg_delta": 0.50, "finish_delta": 0.30, "cohort_count": 0.20},
        role_weights={
            "route_participation": 0.18,
            "target_share": 0.22,
            "air_yard_share": 0.15,
            "routes_consistency": 0.12,
            "target_earning_index": 0.18,
            "opportunity_concentration": 0.15,
        },
        penalty_weights={"already_elite": 0.60, "missed_games": 0.25, "thin_share": 0.15},
        thresholds=BASE_THRESHOLDS,
    ),
    "usage_heavy": _recipe(
        name="usage_heavy",
        description="Pushes more weight toward earned passing-game opportunity and durable workload.",
        scoring_version="wr_signal_score_usage_heavy_v1",
        component_weights={
            "usage_signal": 0.45,
            "efficiency_signal": 0.15,
            "development_signal": 0.15,
            "stability_signal": 0.18,
            "cohort_signal": 0.0,
            "role_signal": 0.0,
            "penalty_signal": -0.07,
        },
        usage_weights={"targets_per_game": 0.65, "target_share": 0.35},
        efficiency_weights={"ppg_per_target": 0.45, "ppg": 0.55},
        development_weights={"finish_room": 0.40, "expected_gap": 0.60},
        stability_weights={"games_played": 0.75, "total_ppr": 0.25},
        cohort_weights={"ppg_delta": 0.50, "finish_delta": 0.30, "cohort_count": 0.20},
        role_weights={
            "route_participation": 0.18,
            "target_share": 0.22,
            "air_yard_share": 0.15,
            "routes_consistency": 0.12,
            "target_earning_index": 0.18,
            "opportunity_concentration": 0.15,
        },
        penalty_weights={"already_elite": 0.50, "missed_games": 0.35, "thin_share": 0.15},
        thresholds=RecipeThresholds(
            **{**BASE_THRESHOLDS.__dict__, "usage_targets_per_game_floor": 4.5, "usage_targets_per_game_ceiling": 11.0}
        ),
    ),
    "efficiency_heavy": _recipe(
        name="efficiency_heavy",
        description="Rewards strong conversion and scoring efficiency more aggressively than raw volume.",
        scoring_version="wr_signal_score_efficiency_heavy_v1",
        component_weights={
            "usage_signal": 0.22,
            "efficiency_signal": 0.38,
            "development_signal": 0.20,
            "stability_signal": 0.12,
            "cohort_signal": 0.0,
            "role_signal": 0.0,
            "penalty_signal": -0.08,
        },
        usage_weights={"targets_per_game": 0.45, "target_share": 0.55},
        efficiency_weights={"ppg_per_target": 0.70, "ppg": 0.30},
        development_weights={"finish_room": 0.35, "expected_gap": 0.65},
        stability_weights={"games_played": 0.55, "total_ppr": 0.45},
        cohort_weights={"ppg_delta": 0.50, "finish_delta": 0.30, "cohort_count": 0.20},
        role_weights={
            "route_participation": 0.18,
            "target_share": 0.22,
            "air_yard_share": 0.15,
            "routes_consistency": 0.12,
            "target_earning_index": 0.18,
            "opportunity_concentration": 0.15,
        },
        penalty_weights={"already_elite": 0.45, "missed_games": 0.20, "thin_share": 0.35},
        thresholds=RecipeThresholds(
            **{
                **BASE_THRESHOLDS.__dict__,
                "efficiency_ppg_per_target_floor": 0.9,
                "efficiency_ppg_per_target_ceiling": 2.7,
                "development_expected_gap_ceiling": 4.5,
            }
        ),
    ),
    "balanced_conservative": _recipe(
        name="balanced_conservative",
        description="Keeps components balanced but increases caution around fragile profiles and already-elite finishes.",
        scoring_version="wr_signal_score_balanced_conservative_v1",
        component_weights={
            "usage_signal": 0.30,
            "efficiency_signal": 0.18,
            "development_signal": 0.17,
            "stability_signal": 0.20,
            "cohort_signal": 0.0,
            "role_signal": 0.0,
            "penalty_signal": -0.15,
        },
        usage_weights={"targets_per_game": 0.50, "target_share": 0.50},
        efficiency_weights={"ppg_per_target": 0.55, "ppg": 0.45},
        development_weights={"finish_room": 0.50, "expected_gap": 0.50},
        stability_weights={"games_played": 0.70, "total_ppr": 0.30},
        cohort_weights={"ppg_delta": 0.50, "finish_delta": 0.30, "cohort_count": 0.20},
        role_weights={
            "route_participation": 0.18,
            "target_share": 0.22,
            "air_yard_share": 0.15,
            "routes_consistency": 0.12,
            "target_earning_index": 0.18,
            "opportunity_concentration": 0.15,
        },
        penalty_weights={"already_elite": 0.55, "missed_games": 0.25, "thin_share": 0.20},
        thresholds=RecipeThresholds(
            **{
                **BASE_THRESHOLDS.__dict__,
                "stability_games_floor": 9.0,
                "penalty_games_anchor": 12.0,
                "penalty_games_ceiling": 12.0,
                "penalty_target_share_anchor": 0.16,
                "penalty_target_share_ceiling": 0.16,
            }
        ),
    ),
    "upside_chaser": _recipe(
        name="upside_chaser",
        description="Favors room for growth and explosive efficiency while softening the conservative penalties.",
        scoring_version="wr_signal_score_upside_chaser_v1",
        component_weights={
            "usage_signal": 0.24,
            "efficiency_signal": 0.26,
            "development_signal": 0.30,
            "stability_signal": 0.10,
            "cohort_signal": 0.0,
            "role_signal": 0.0,
            "penalty_signal": -0.05,
        },
        usage_weights={"targets_per_game": 0.45, "target_share": 0.55},
        efficiency_weights={"ppg_per_target": 0.65, "ppg": 0.35},
        development_weights={"finish_room": 0.30, "expected_gap": 0.70},
        stability_weights={"games_played": 0.55, "total_ppr": 0.45},
        cohort_weights={"ppg_delta": 0.50, "finish_delta": 0.30, "cohort_count": 0.20},
        role_weights={
            "route_participation": 0.18,
            "target_share": 0.22,
            "air_yard_share": 0.15,
            "routes_consistency": 0.12,
            "target_earning_index": 0.18,
            "opportunity_concentration": 0.15,
        },
        penalty_weights={"already_elite": 0.45, "missed_games": 0.15, "thin_share": 0.40},
        thresholds=RecipeThresholds(
            **{
                **BASE_THRESHOLDS.__dict__,
                "development_finish_anchor": 60.0,
                "development_finish_ceiling": 48.0,
                "development_expected_gap_ceiling": 5.0,
                "penalty_target_share_anchor": 0.12,
                "penalty_target_share_ceiling": 0.12,
            }
        ),
    ),
    "cohort_balanced": _recipe(
        name="cohort_balanced",
        description="Balanced recipe that adds cohort-relative peer expectation context while keeping the original usage/efficiency spine.",
        scoring_version="wr_signal_score_cohort_balanced_v1",
        component_weights={
            "usage_signal": 0.28,
            "efficiency_signal": 0.17,
            "development_signal": 0.18,
            "stability_signal": 0.15,
            "cohort_signal": 0.30,
            "role_signal": 0.0,
            "penalty_signal": -0.08,
        },
        usage_weights={"targets_per_game": 0.55, "target_share": 0.45},
        efficiency_weights={"ppg_per_target": 0.55, "ppg": 0.45},
        development_weights={"finish_room": 0.40, "expected_gap": 0.60},
        stability_weights={"games_played": 0.65, "total_ppr": 0.35},
        cohort_weights={"ppg_delta": 0.55, "finish_delta": 0.25, "cohort_count": 0.20},
        role_weights={
            "route_participation": 0.18,
            "target_share": 0.22,
            "air_yard_share": 0.15,
            "routes_consistency": 0.12,
            "target_earning_index": 0.18,
            "opportunity_concentration": 0.15,
        },
        penalty_weights={"already_elite": 0.55, "missed_games": 0.25, "thin_share": 0.20},
        thresholds=RecipeThresholds(**{**BASE_THRESHOLDS.__dict__, "cohort_count_ceiling": 18.0}),
    ),
    "cohort_upside": _recipe(
        name="cohort_upside",
        description="Cohort-aware upside recipe that prioritizes players who already outperform peer expectations and still have room to climb.",
        scoring_version="wr_signal_score_cohort_upside_v1",
        component_weights={
            "usage_signal": 0.20,
            "efficiency_signal": 0.18,
            "development_signal": 0.24,
            "stability_signal": 0.08,
            "cohort_signal": 0.36,
            "role_signal": 0.0,
            "penalty_signal": -0.06,
        },
        usage_weights={"targets_per_game": 0.45, "target_share": 0.55},
        efficiency_weights={"ppg_per_target": 0.60, "ppg": 0.40},
        development_weights={"finish_room": 0.30, "expected_gap": 0.70},
        stability_weights={"games_played": 0.55, "total_ppr": 0.45},
        cohort_weights={"ppg_delta": 0.65, "finish_delta": 0.20, "cohort_count": 0.15},
        role_weights={
            "route_participation": 0.18,
            "target_share": 0.22,
            "air_yard_share": 0.15,
            "routes_consistency": 0.12,
            "target_earning_index": 0.18,
            "opportunity_concentration": 0.15,
        },
        penalty_weights={"already_elite": 0.45, "missed_games": 0.20, "thin_share": 0.35},
        thresholds=RecipeThresholds(**{**BASE_THRESHOLDS.__dict__, "cohort_ppg_delta_ceiling": 7.0, "cohort_finish_delta_ceiling": 42.0, "cohort_count_ceiling": 16.0}),
    ),
    "role_balanced": _recipe(
        name="role_balanced",
        description="Balanced role-aware recipe that adds explicit prior-season route and share concentration signals.",
        scoring_version="wr_signal_score_role_balanced_v1",
        component_weights={
            "usage_signal": 0.24,
            "efficiency_signal": 0.15,
            "development_signal": 0.16,
            "stability_signal": 0.13,
            "cohort_signal": 0.18,
            "role_signal": 0.20,
            "penalty_signal": -0.06,
        },
        usage_weights={"targets_per_game": 0.50, "target_share": 0.50},
        efficiency_weights={"ppg_per_target": 0.55, "ppg": 0.45},
        development_weights={"finish_room": 0.40, "expected_gap": 0.60},
        stability_weights={"games_played": 0.65, "total_ppr": 0.35},
        cohort_weights={"ppg_delta": 0.50, "finish_delta": 0.30, "cohort_count": 0.20},
        role_weights={
            "route_participation": 0.20,
            "target_share": 0.20,
            "air_yard_share": 0.15,
            "routes_consistency": 0.15,
            "target_earning_index": 0.15,
            "opportunity_concentration": 0.15,
        },
        penalty_weights={"already_elite": 0.50, "missed_games": 0.25, "thin_share": 0.25},
        thresholds=RecipeThresholds(
            **{
                **BASE_THRESHOLDS.__dict__,
                "cohort_count_ceiling": 18.0,
                "role_route_participation_floor": 0.50,
                "role_target_share_ceiling": 0.32,
                "role_air_yard_share_ceiling": 0.38,
                "role_routes_consistency_floor": 0.60,
                "role_target_earning_ceiling": 0.45,
                "role_opportunity_concentration_ceiling": 0.56,
            }
        ),
    ),
    "role_upside": _recipe(
        name="role_upside",
        description="Role-aware upside recipe that prioritizes concentrated, sticky passing-game roles with room to convert into a breakout.",
        scoring_version="wr_signal_score_role_upside_v1",
        component_weights={
            "usage_signal": 0.18,
            "efficiency_signal": 0.16,
            "development_signal": 0.22,
            "stability_signal": 0.08,
            "cohort_signal": 0.14,
            "role_signal": 0.28,
            "penalty_signal": -0.06,
        },
        usage_weights={"targets_per_game": 0.40, "target_share": 0.60},
        efficiency_weights={"ppg_per_target": 0.60, "ppg": 0.40},
        development_weights={"finish_room": 0.30, "expected_gap": 0.70},
        stability_weights={"games_played": 0.55, "total_ppr": 0.45},
        cohort_weights={"ppg_delta": 0.60, "finish_delta": 0.25, "cohort_count": 0.15},
        role_weights={
            "route_participation": 0.18,
            "target_share": 0.22,
            "air_yard_share": 0.18,
            "routes_consistency": 0.10,
            "target_earning_index": 0.17,
            "opportunity_concentration": 0.15,
        },
        penalty_weights={"already_elite": 0.45, "missed_games": 0.20, "thin_share": 0.35},
        thresholds=RecipeThresholds(
            **{
                **BASE_THRESHOLDS.__dict__,
                "development_finish_anchor": 60.0,
                "development_finish_ceiling": 48.0,
                "development_expected_gap_ceiling": 5.0,
                "cohort_ppg_delta_ceiling": 7.0,
                "role_route_participation_floor": 0.48,
                "role_target_share_ceiling": 0.34,
                "role_air_yard_share_ceiling": 0.40,
                "role_routes_consistency_floor": 0.58,
                "role_target_earning_ceiling": 0.48,
                "role_opportunity_concentration_ceiling": 0.58,
            }
        ),
    ),
}

DEFAULT_RECIPE = RECIPES["baseline_v1"]


def get_recipe(name: str) -> SignalRecipe:
    try:
        return RECIPES[name]
    except KeyError as exc:
        raise ValueError(f"unknown recipe: {name}") from exc
