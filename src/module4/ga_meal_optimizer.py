"""
Genetic algorithm optimizer for Module 4 suggestions.

This is an *additional* optimizer option (algorithm="ga") alongside UCS/A*.
It reuses Module 4's existing action validity rules by generating and mutating
meals via `MealSuggestionPlanner._expand(...)` rather than inventing new edit
operators from scratch.

Design choices (as agreed):
- Genome: edited meal (action sequence is derived from meal diff vs start)
- Fitness priorities (lexicographic):
  1) category improvement (goal met first; then lower risk tier)
  2) lower risk score / lower effective GL
  3) fewer edits
- Constraint handling: discard/resample invalid offspring
- Diversity: reuse planner's existing final diversity filter
- Defaults: "balanced" runtime profile
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


MealTuple = Tuple[Tuple[str, str], ...]


@dataclass(frozen=True)
class GAConfig:
    population_size: int = 50
    generations: int = 30
    tournament_k: int = 3
    elite_keep: int = 8
    mutation_rate: float = 0.35
    crossover_rate: float = 0.7
    max_evaluations: int = 1500


@dataclass(frozen=True)
class Individual:
    meal: MealTuple
    actions: Tuple[str, ...]
    edits_count: int
    category: str
    risk_score: float
    effective_gl: float


def generate_candidates_ga(
    *,
    planner: object,
    start_meal: MealTuple,
    original_level: int,
    desired_count: int,
    config: Optional[GAConfig] = None,
) -> List[dict]:
    """
    Run GA and return a list of Suggestion dicts (same shape as search output).

    `planner` is a MealSuggestionPlanner instance; we intentionally keep this
    dependency loose to avoid circular imports.
    """
    cfg = config or GAConfig()
    rng = random.Random()

    # Local analysis cache (same shape as planner's search cache).
    analysis_cache: Dict[MealTuple, Tuple[str, float, float]] = {}

    # Seed population with:
    # - start meal
    # - all 1-step neighbors from start (deterministic seeding of "obvious" edits)
    # - random walks for the rest
    population: List[Individual] = []
    population.append(_make_individual(planner, start_meal, start_meal, analysis_cache))

    start_node = _node_from_meal(planner, start_meal, actions=tuple())
    for child in getattr(planner, "_expand")(start_node):
        population.append(_make_individual(planner, start_meal, child.meal, analysis_cache))

    while len(population) < cfg.population_size:
        meal = _random_walk_meal(planner, start_meal, rng=rng)
        population.append(_make_individual(planner, start_meal, meal, analysis_cache))

    evals_used = len({ind.meal for ind in population})

    best_seen = min(population, key=lambda ind: _fitness_key(ind, original_level))

    for _gen in range(cfg.generations):
        if evals_used >= cfg.max_evaluations:
            break

        # Sort once for elite selection.
        population.sort(key=lambda ind: _fitness_key(ind, original_level))
        elites = population[: max(1, min(cfg.elite_keep, len(population)))]
        next_pop: List[Individual] = list(elites)

        while len(next_pop) < cfg.population_size and evals_used < cfg.max_evaluations:
            parent_a = _tournament_select(population, original_level, cfg.tournament_k, rng)
            parent_b = _tournament_select(population, original_level, cfg.tournament_k, rng)

            if rng.random() < cfg.crossover_rate:
                child_meal = _crossover_meals(planner, start_meal, parent_a.meal, parent_b.meal, rng)
                if child_meal is None:
                    continue
            else:
                child_meal = parent_a.meal

            if rng.random() < cfg.mutation_rate:
                mutated = _mutate_meal(planner, child_meal, rng)
                if mutated is None:
                    continue
                child_meal = mutated

            ind = _make_individual(planner, start_meal, child_meal, analysis_cache)
            next_pop.append(ind)
            evals_used += 1

        population = next_pop
        best_seen = min(best_seen, min(population, key=lambda ind: _fitness_key(ind, original_level)), key=lambda i: _fitness_key(i, original_level))

    # Collect goal-satisfying candidates from population + best seen.
    pool = list(population)
    pool.append(best_seen)
    goals = [i for i in pool if getattr(planner, "_is_goal")(original_level, i.category)]

    # Convert Individuals to Suggestion dicts; keep extras because planner will do diversity + top-k.
    suggestions: List[dict] = []
    for i in goals:
        if i.edits_count <= 0:
            continue
        suggestions.append(
            {
                "edited_meal": [{"food_name": f, "serving_size": s} for f, s in i.meal],
                "actions": list(i.actions),
                "resulting_category": i.category,
                "resulting_score": float(i.risk_score),
            }
        )

    suggestions.sort(key=lambda s: (len(s["actions"]), float(s["resulting_score"])))
    return suggestions


def _fitness_key(ind: Individual, original_level: int) -> Tuple[int, int, float, float, int]:
    """
    Lower is better.

    1) Goal met first (0 if met, else 1)
    2) Lower tier (low < medium < high)
    3) Lower risk score
    4) Lower effective GL
    5) Fewer edits
    """
    level_map = {"low": 0, "safe": 0, "medium": 1, "caution": 1, "high": 2, "unsafe": 2}
    new_level = level_map.get(ind.category, 99)
    goal_met = 0 if new_level <= max(0, original_level - 1) else 1
    return (goal_met, new_level, float(ind.risk_score), float(ind.effective_gl), int(ind.edits_count))


def _tournament_select(
    population: Sequence[Individual],
    original_level: int,
    k: int,
    rng: random.Random,
) -> Individual:
    k = max(1, min(int(k), len(population)))
    contenders = rng.sample(list(population), k=k) if len(population) > 1 else list(population)
    return min(contenders, key=lambda ind: _fitness_key(ind, original_level))


def _node_from_meal(planner: object, meal: MealTuple, *, actions: Tuple[str, ...]) -> object:
    # _Node is defined inside meal_suggestion_planner; instantiate via its name on the module.
    # We avoid importing it directly here.
    node_cls = getattr(__import__("src.module4.meal_suggestion_planner", fromlist=["_Node"]), "_Node")
    return node_cls(meal=meal, actions=actions, edits_count=len(actions))


def _make_individual(
    planner: object,
    start_meal: MealTuple,
    meal: MealTuple,
    cache: Dict[MealTuple, Tuple[str, float, float]],
) -> Individual:
    cat, score, eg = getattr(planner, "_get_cached_analysis")(meal, cache)
    actions = _derive_actions_from_diff(planner, start_meal, meal)
    return Individual(
        meal=meal,
        actions=actions,
        edits_count=len(actions),
        category=cat,
        risk_score=float(score),
        effective_gl=float(eg),
    )


def _derive_actions_from_diff(planner: object, start_meal: MealTuple, meal: MealTuple) -> Tuple[str, ...]:
    """
    Reconstruct user-facing action strings from a (start_meal -> meal) diff.

    This keeps GA output consistent with the rest of Module 4.
    """
    orig_count = getattr(planner, "_original_count")
    actions: List[str] = []

    # Original slots: swaps and/or portion reductions.
    for idx in range(min(orig_count, len(start_meal), len(meal))):
        start_food, start_serv = start_meal[idx]
        new_food, new_serv = meal[idx]
        if new_food != start_food:
            actions.append(f"Swap {start_food} -> {new_food}")
        if new_food == start_food and new_serv.strip() != start_serv.strip():
            actions.append(f"Reduce portion of {start_food}: {start_serv} -> {new_serv}")
        if new_food != start_food and new_serv.strip() != start_serv.strip():
            # If both changed, treat as swap (primary) plus serving change.
            actions.append(f"Reduce portion of {new_food}: {start_serv} -> {new_serv}")

    # Added items: beyond original slots.
    for idx in range(orig_count, len(meal)):
        food, serv = meal[idx]
        actions.append(f"Add {food} ({serv})")

    # Cap to planner.max_edits by truncation (should be rare if we respect budgets elsewhere).
    max_edits = int(getattr(planner, "max_edits"))
    return tuple(actions[:max_edits])


def _random_walk_meal(planner: object, start_meal: MealTuple, *, rng: random.Random) -> MealTuple:
    """
    Build a random valid meal by walking through `_expand` from the start.
    """
    max_edits = int(getattr(planner, "max_edits"))
    steps = rng.randint(0, max_edits)
    node = _node_from_meal(planner, start_meal, actions=tuple())
    for _ in range(steps):
        children = getattr(planner, "_expand")(node)
        if not children:
            break
        node = rng.choice(children)
    return node.meal


def _crossover_meals(
    planner: object,
    start_meal: MealTuple,
    a: MealTuple,
    b: MealTuple,
    rng: random.Random,
) -> Optional[MealTuple]:
    """
    Meal-level crossover: for each original slot, pick gene from parent A or B.
    Added items are sampled from the union of parent-added items.
    """
    orig_count = getattr(planner, "_original_count")
    if orig_count <= 0:
        return None

    child: List[Tuple[str, str]] = []
    for idx in range(orig_count):
        if idx >= len(start_meal):
            return None
        pick_from_a = rng.random() < 0.5
        src = a if pick_from_a else b
        if idx >= len(src):
            src = start_meal
        child.append(src[idx])

    # Added part: union, then sample a small subset bounded by max_edits budget.
    a_added = list(a[orig_count:]) if len(a) > orig_count else []
    b_added = list(b[orig_count:]) if len(b) > orig_count else []
    union = list({x for x in a_added + b_added})
    rng.shuffle(union)

    max_edits = int(getattr(planner, "max_edits"))
    # Very rough bound: can't have more total actions than max_edits.
    # Add at most max_edits items, but usually much less.
    add_cap = min(len(union), max(0, max_edits - 1))
    child_added = union[:add_cap]

    meal = tuple(child + child_added)

    if _violates_duplicate_swap_constraint(planner, start_meal, meal):
        repaired = _repair_duplicate_swaps(planner, start_meal, meal, rng)
        if repaired is None:
            return None
        meal = repaired

    # Disallow duplicate food names overall (keeps consistency with `_expand` add rule).
    seen: set[str] = set()
    dedup: List[Tuple[str, str]] = []
    for f, s in meal:
        if f in seen:
            continue
        seen.add(f)
        dedup.append((f, s))
    return tuple(dedup)


def _mutate_meal(planner: object, meal: MealTuple, rng: random.Random) -> Optional[MealTuple]:
    """
    Mutation via a single valid expansion step from the current meal.
    """
    actions = _derive_actions_from_diff(planner, getattr(planner, "_start_meal"), meal)
    node = _node_from_meal(planner, meal, actions=actions)
    children = getattr(planner, "_expand")(node)
    if not children:
        return None
    child = rng.choice(children)
    return child.meal


def _violates_duplicate_swap_constraint(planner: object, start_meal: MealTuple, meal: MealTuple) -> bool:
    return bool(
        getattr(__import__("src.module4.meal_suggestion_planner", fromlist=["meal_has_duplicate_replacement_across_distinct_foods"]), "meal_has_duplicate_replacement_across_distinct_foods")(
            start_meal,
            meal,
            getattr(planner, "_original_count"),
        )
    )


def _repair_duplicate_swaps(
    planner: object,
    start_meal: MealTuple,
    meal: MealTuple,
    rng: random.Random,
) -> Optional[MealTuple]:
    """
    Simple repair: if two distinct originals map to the same replacement, revert
    one of the conflicting slots to its original food.
    """
    orig_count = getattr(planner, "_original_count")
    if orig_count <= 1:
        return None

    # Try a few random repairs.
    meal_list = list(meal)
    for _ in range(10):
        if not _violates_duplicate_swap_constraint(planner, start_meal, tuple(meal_list)):
            return tuple(meal_list)

        # Randomly revert one original slot.
        idx = rng.randrange(0, min(orig_count, len(meal_list)))
        meal_list[idx] = start_meal[idx]

    return None

