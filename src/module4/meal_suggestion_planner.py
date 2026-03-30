"""Module 4: Search-based meal modification suggestions.

Uses **uniform-cost** or **A\*** search over meals edited by **portion reduction**,
**same-category swaps**, and **adds**. The **goal** is a meal whose Module 3 risk
tier improves by at least one step (e.g. high→medium). The frontier orders states
by edit count, (A\* goal distance), risk score, and **effective glycemic load**
so many tied high scores still prefer materially lower sugar impact.

**Swaps** use the knowledge base only: same inferred coarse category as the
original, then—within ``grain_starch``—the same **subfamily** (rice→rice,
bread→bread, pasta→pasta, etc.), ranked by lower glycemic index and load.
Category rules use **whole-word** tokens and phrases (plus small overrides such
as **rice milk** as beverage). **Embeddings are not used** here.

**Portion reduction** scales current servings by 75%, 50%, and 25% on eligible
original lines (carb-heavy categories with nonzero reference GL). **Adds** pick
low-GI, higher-fiber vegetables/legumes/proteins from the KB.
"""

from __future__ import annotations

import heapq
import re
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Literal, Optional, Sequence, Tuple, TypedDict

from src.module1.knowledge_base import FoodNotFoundError, MissingDataError, NutritionKnowledgeBase
from src.module3.meal_risk_analyzer import MealRiskAnalyzer

MealRiskCategory = Literal["low", "medium", "high"]

_RISK_TO_LEVEL: Dict[str, int] = {
    "low": 0,
    "safe": 0,
    "medium": 1,
    "caution": 1,
    "high": 2,
    "unsafe": 2,
}

_CATEGORY_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "grain_starch": (
        "rice",
        "bread",
        "bagel",
        "pasta",
        "noodle",
        "quinoa",
        "oat",
        "barley",
        "couscous",
        "polenta",
        "potato",
        "sweet potato",
        "yam",
    ),
    "fruit": ("apple", "banana", "orange", "berry", "fruit", "mango", "grape", "melon", "pear", "pineapple"),
    "vegetable": (
        "broccoli",
        "cabbage",
        "pepper",
        "spinach",
        "kale",
        "mushroom",
        "squash",
        "tomato",
        "carrot",
        "vegetable",
        "lettuce",
        "onion",
        "beet",
        "bok choy",
        "cauliflower",
    ),
    "legume": ("bean", "lentil", "chickpea", "peas", "hummus"),
    "protein": (
        "chicken",
        "turkey",
        "beef",
        "pork",
        "salmon",
        "tuna",
        "fish",
        "shrimp",
        "scallop",
        "egg",
        "tofu",
        "tempeh",
        "sausage",
        "burger",
    ),
    "dairy": ("milk", "yogurt", "cheese", "kefir", "cream"),
    "beverage": ("juice", "coffee", "tea", "drink", "soda", "smoothie", "water"),
    "snack_sweet": ("cookie", "cake", "chips", "candy", "dessert", "chocolate", "pastry", "croissant"),
    "fat_condiment": ("oil", "butter", "dressing", "vinaigrette", "sauce", "mayo"),
}

# Cooking/prep modifiers that should not create artificial “different” foods.
# Used only for diversity selection (so we don’t return “brown rice steamed”
# and “brown rice boiled” as two separate suggestions).
_DIVERSITY_PREP_TERMS: Tuple[str, ...] = (
    "boiled",
    "sweetened",
    "steamed",
    "grilled",
    "sauteed",
    "saute",
    "baked",
    "fried",
    "roasted",
    "pureed",
    "pickled",
    "smoked",
    "canned",
    "fresh",
    "frozen",
    "raw",
    "overcooked",
    "iced",
    "al dente",
    "from concentrate",
    "concentrate",
)

# Search tuning and candidate-generation constants.
SWAP_CANDIDATE_SLICE: int = 8

ADD_CANDIDATE_GI_MAX: float = 55.0
ADD_CANDIDATE_MIN_FIBER: float = 1.5
ADD_CANDIDATE_SLICE: int = 10

ABSOLUTE_MAX_FOUND_CANDIDATES: int = 50
MIN_FOUND_CANDIDATES: int = 10
FOUND_CANDIDATES_MULTIPLIER: int = 8

DEFAULT_ADD_SERVING_SIZE: str = "100g"

# Portion reduction: multiply current serving grams by each factor (gentler → stronger).
PORTION_REDUCTION_FACTORS: Tuple[float, ...] = (0.75, 0.5, 0.25)
MIN_PORTION_GRAMS: float = 10.0
PORTION_REDUCTION_CATEGORIES: FrozenSet[str] = frozenset(
    {"grain_starch", "fruit", "snack_sweet", "beverage", "legume"}
)

MAX_ALLOWED_DIVERSITY_OVERLAP: int = 1
EMPTY_DIVERSITY_SIGNATURE_SENTINEL: str = ""


def _format_grams_serving(grams: float) -> str:
    """Format a gram amount as a serving string (e.g. ``150g``, ``12.5g``)."""
    g = round(float(grams), 1)
    if abs(g - round(g)) < 1e-6:
        return f"{int(round(g))}g"
    return f"{g}g"


class MealItem(TypedDict):
    food_name: str
    serving_size: str


class Suggestion(TypedDict):
    edited_meal: List[MealItem]
    actions: List[str]
    resulting_category: MealRiskCategory
    resulting_score: float


class SuggestionResult(TypedDict):
    target_message: str
    suggestions: List[Suggestion]
    status: Literal["low_risk_no_suggestions_needed", "suggestions_found", "no_suggestions_found"]


@dataclass(frozen=True)
class _Node:
    meal: Tuple[Tuple[str, str], ...]
    actions: Tuple[str, ...]
    edits_count: int


def _name_tokens(food_name: str) -> set[str]:
    """Whole-word tokens from a food name (lowercase)."""
    return set(re.findall(r"[a-z0-9]+", (food_name or "").lower()))


def infer_food_category(food_name: str) -> str:
    """
    Assign a coarse category using **whole tokens**, not raw substring search.

    This avoids bugs like matching the grain keyword ``oat`` inside ``goat``,
    which incorrectly classified cheese as a starch.
    """
    name = (food_name or "").lower()
    tokens = _name_tokens(food_name)
    if not tokens:
        return "other"

    # Overrides: words that imply a category even if another token (e.g. rice) appears.
    if "tempeh" in tokens or "tofu" in tokens:
        return "protein"
    if "vinegar" in tokens:
        return "fat_condiment"
    # Plant/dairy drink named with "rice"; not a starchy rice dish (avoids rice→rice milk swaps).
    if "rice milk" in name:
        return "beverage"

    # Multi-word phrases first (longest first so "sweet potato" beats "potato").
    phrases: List[Tuple[str, str]] = []
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if " " in kw:
                phrases.append((category, kw))
    phrases.sort(key=lambda x: -len(x[1]))
    for category, phrase in phrases:
        if phrase in name:
            return category

    for category, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if " " in kw:
                continue
            if kw in tokens:
                return category
    return "other"


# Token sets for starch subfamilies (rice→rice, bread→bread, pasta→pasta, …).
_PASTA_TOKENS: FrozenSet[str] = frozenset(
    {
        "pasta",
        "noodle",
        "ravioli",
        "linguine",
        "fettuccine",
        "penne",
        "macaroni",
        "lasagna",
        "gnocchi",
        "spaghetti",
        "orzo",
        "tagliatelle",
        "farfalle",
        "rigatoni",
    }
)


def infer_grain_starch_subfamily(food_name: str) -> Optional[str]:
    """
    Within ``grain_starch``, assign a **swap subfamily** so replacements stay sensible
    (e.g. rice dishes swap to other rice foods, not pasta salad or bread).

    Returns ``None`` if the food is not classified as ``grain_starch``.
    """
    if infer_food_category(food_name) != "grain_starch":
        return None
    name = (food_name or "").lower()
    tokens = _name_tokens(food_name)

    if "bread" in tokens or "bagel" in tokens:
        return "bread"
    if tokens & _PASTA_TOKENS:
        return "pasta"
    if "rice" in tokens:
        return "rice"
    if "sweet potato" in name or ("sweet" in tokens and "potato" in tokens):
        return "potato"
    if "potato" in tokens or "yam" in tokens:
        return "potato"
    if "quinoa" in tokens:
        return "quinoa"
    if "oat" in tokens or "oats" in tokens:
        return "oat"
    if "barley" in tokens:
        return "barley"
    if "couscous" in tokens:
        return "couscous"
    if "polenta" in tokens:
        return "polenta"
    return "other_starch"


def meal_has_duplicate_replacement_across_distinct_foods(
    start_meal: Tuple[Tuple[str, str], ...],
    new_meal: Tuple[Tuple[str, str], ...],
    orig_count: int,
) -> bool:
    """
    True if two *different* original foods were swapped to the *same* replacement.

    Same replacement for two identical original names (e.g. two rice lines) is allowed.
    """
    by_new: Dict[str, set[str]] = {}
    for i in range(min(orig_count, len(start_meal), len(new_meal))):
        old_f, _ = start_meal[i]
        new_f, _ = new_meal[i]
        if new_f == old_f:
            continue
        by_new.setdefault(new_f, set()).add(old_f)
    for olds in by_new.values():
        if len(olds) >= 2:
            return True
    return False


def suggestion_count_for_category(risk_category: str) -> int:
    """Return requested suggestion count from initial risk."""
    level = _RISK_TO_LEVEL.get(risk_category, 0)
    if level >= 2:
        return 5
    if level == 1:
        return 3
    return 0


class MealSuggestionPlanner:
    """Generate meal edits that lower meal risk by at least one tier."""

    def __init__(
        self,
        knowledge_base: NutritionKnowledgeBase,
        meal_risk_analyzer: MealRiskAnalyzer,
        *,
        max_edits: int = 8,
        max_expansions: int = 2000,
    ) -> None:
        self.knowledge_base = knowledge_base
        self.meal_risk_analyzer = meal_risk_analyzer
        self.max_edits = max_edits
        self.max_expansions = max_expansions
        self._all_foods = self.knowledge_base.list_all_foods()
        self._original_count: int = 0
        self._start_meal: Tuple[Tuple[str, str], ...] = ()

    def generate_suggestions(
        self,
        meal_items: Sequence[MealItem],
        *,
        original_category: str,
        algorithm: str = "astar",
        top_k: Optional[int] = None,
    ) -> SuggestionResult:
        """Search for practical swap/add bundles that reduce risk tier."""
        original_level = _RISK_TO_LEVEL.get(original_category, 0)
        desired_count = top_k if top_k is not None else suggestion_count_for_category(original_category)
        if original_level <= 0 or desired_count <= 0:
            return {
                "target_message": "This meal is already low risk. No risk-lowering changes are required.",
                "suggestions": [],
                "status": "low_risk_no_suggestions_needed",
            }

        self._original_count = len(meal_items)
        start_meal = tuple((item["food_name"], item["serving_size"]) for item in meal_items)
        self._start_meal = start_meal
        target = "Any one of these suggestions should lower your meal risk by at least one category."
        found_candidates = self._collect_goal_candidates(start_meal, original_level, desired_count, algorithm)
        diverse = self._select_diverse(found_candidates, desired_count, start_meal=start_meal)
        if diverse:
            return {
                "target_message": target,
                "suggestions": diverse,
                "status": "suggestions_found",
            }
        return {
            "target_message": "No suggestions found within current search limits.",
            "suggestions": [],
            "status": "no_suggestions_found",
        }

    def _collect_goal_candidates(
        self,
        start_meal: Tuple[Tuple[str, str], ...],
        original_level: int,
        desired_count: int,
        algorithm: str,
    ) -> List[Suggestion]:
        """Run the search and return all goal-satisfying candidates found."""
        start_node, frontier, counter, best_seen_edits, analysis_cache = self._init_search(
            start_meal=start_meal,
            original_level=original_level,
            algorithm=algorithm,
        )
        found_candidates: List[Suggestion] = []
        expansions = 0
        max_found_candidates = min(
            ABSOLUTE_MAX_FOUND_CANDIDATES,
            max(MIN_FOUND_CANDIDATES, desired_count * FOUND_CANDIDATES_MULTIPLIER),
        )

        while (
            frontier
            and expansions < self.max_expansions
            and len(found_candidates) < max_found_candidates
        ):
            _, _, node = heapq.heappop(frontier)
            expansions += 1

            if self._try_add_goal_candidate(
                node=node,
                original_level=original_level,
                analysis_cache=analysis_cache,
                found_candidates=found_candidates,
            ):
                continue

            if node.edits_count >= self.max_edits:
                continue

            counter = self._enqueue_children(
                node=node,
                frontier=frontier,
                counter=counter,
                best_seen_edits=best_seen_edits,
                original_level=original_level,
                algorithm=algorithm,
                analysis_cache=analysis_cache,
            )

        # Lexicographic-like ranking key: fewer edits first, then lower risk score.
        found_candidates.sort(key=lambda s: (len(s["actions"]), s["resulting_score"]))
        return found_candidates

    def _init_search(
        self,
        *,
        start_meal: Tuple[Tuple[str, str], ...],
        original_level: int,
        algorithm: str,
    ) -> Tuple[
        _Node,
        List[Tuple[Tuple[int, int, float, float], int, _Node]],
        int,
        Dict[Tuple[Tuple[str, str], ...], int],
        Dict[Tuple[Tuple[str, str], ...], Tuple[str, float, float]],
    ]:
        """Initialize frontier and memoization for the search."""
        start_node = _Node(meal=start_meal, actions=tuple(), edits_count=0)
        frontier: List[Tuple[Tuple[int, int, float, float], int, _Node]] = []
        counter = 0
        analysis_cache: Dict[Tuple[Tuple[str, str], ...], Tuple[str, float, float]] = {}
        st_cat, st_score, st_eg = self._get_cached_analysis(start_meal, analysis_cache)
        heapq.heappush(
            frontier,
            (
                self._priority_tuple(
                    start_node,
                    original_level,
                    algorithm,
                    analysis_category=st_cat,
                    risk_score=st_score,
                    effective_gl=st_eg,
                ),
                counter,
                start_node,
            ),
        )
        best_seen_edits: Dict[Tuple[Tuple[str, str], ...], int] = {
            self._canonical(start_node.meal): 0
        }
        return start_node, frontier, counter, best_seen_edits, analysis_cache

    def _try_add_goal_candidate(
        self,
        *,
        node: _Node,
        original_level: int,
        analysis_cache: Dict[Tuple[Tuple[str, str], ...], Tuple[str, float, float]],
        found_candidates: List[Suggestion],
    ) -> bool:
        """If the node satisfies the goal, append it and return True."""
        if node.edits_count <= 0:
            return False

        analysis_category, risk_score, _ = self._get_cached_analysis(
            node.meal, analysis_cache
        )
        if not self._is_goal(original_level, analysis_category):
            return False

        if meal_has_duplicate_replacement_across_distinct_foods(
            self._start_meal,
            node.meal,
            self._original_count,
        ):
            return False

        found_candidates.append(
            {
                "edited_meal": [{"food_name": f, "serving_size": s} for f, s in node.meal],
                "actions": list(node.actions),
                "resulting_category": analysis_category,
                "resulting_score": float(risk_score),
            }
        )
        return True

    def _enqueue_children(
        self,
        *,
        node: _Node,
        frontier: List[Tuple[Tuple[int, int, float, float], int, _Node]],
        counter: int,
        best_seen_edits: Dict[Tuple[Tuple[str, str], ...], int],
        original_level: int,
        algorithm: str,
        analysis_cache: Dict[Tuple[Tuple[str, str], ...], Tuple[str, float, float]],
    ) -> int:
        """Expand a node and enqueue successors into the frontier."""
        for next_node in self._expand(node):
            key = self._canonical(next_node.meal)
            prev_best = best_seen_edits.get(key)
            if prev_best is not None and prev_best <= next_node.edits_count:
                continue

            best_seen_edits[key] = next_node.edits_count
            counter += 1

            next_analysis_category, next_risk_score, next_effective_gl = self._get_cached_analysis(
                next_node.meal, analysis_cache
            )
            heapq.heappush(
                frontier,
                (
                    self._priority_tuple(
                        next_node,
                        original_level,
                        algorithm,
                        analysis_category=next_analysis_category,
                        risk_score=next_risk_score,
                        effective_gl=next_effective_gl,
                    ),
                    counter,
                    next_node,
                ),
            )
        return counter

    def _priority_tuple(
        self,
        node: _Node,
        original_level: int,
        algorithm: str,
        *,
        analysis_category: Optional[str],
        risk_score: float,
        effective_gl: float,
    ) -> Tuple[int, int, float, float]:
        """
        Explicit lexicographic priority:
          1) edits_count (or edits_count + goal-distance for A*)
          2) edits_count (tie-break)
          3) resulting risk score (lower is better)
          4) effective glycemic load (lower is better)

        Many high-risk meals share ``risk_score == 100`` (score cap); tie-breaking
        on ``effective_gl`` steers search toward portion reductions and swaps that
        materially lower sugar impact.
        """
        if algorithm.lower() == "ucs":
            return (
                node.edits_count,
                node.edits_count,
                float(risk_score),
                float(effective_gl),
            )

        goal_met = False if analysis_category is None else self._is_goal(original_level, analysis_category)
        h = 0 if goal_met else 1
        return (
            node.edits_count + h,
            node.edits_count,
            float(risk_score),
            float(effective_gl),
        )

    def _get_cached_analysis(
        self,
        meal: Tuple[Tuple[str, str], ...],
        cache: Dict[Tuple[Tuple[str, str], ...], Tuple[str, float, float]],
    ) -> Tuple[str, float, float]:
        """Memoize Module 3 analysis results during search."""
        key = self._canonical(meal)
        cached = cache.get(key)
        if cached is not None:
            return cached

        analysis = self.meal_risk_analyzer.analyze_meal(
            [{"food_name": f, "serving_size": s} for f, s in meal]
        )
        raw_eg = analysis.get("effective_gl")
        effective_gl = float(raw_eg) if raw_eg is not None else float("inf")
        result = (analysis["meal_risk_category"], float(analysis["risk_score"]), effective_gl)
        cache[key] = result
        return result

    def _is_goal(self, original_level: int, new_category: str) -> bool:
        new_level = _RISK_TO_LEVEL.get(new_category, 0)
        return new_level <= max(0, original_level - 1)

    def _expand(self, node: _Node) -> List[_Node]:
        out: List[_Node] = []

        # Portion reduction first (often lowers effective GL immediately; listed before
        # swaps so equal-priority heap ties favor smaller servings in expansion order).
        for idx in range(self._original_count):
            food_name, serving_size = node.meal[idx]
            if infer_food_category(food_name) not in PORTION_REDUCTION_CATEGORIES:
                continue
            if self._safe_gl(food_name) <= 0.0:
                continue
            grams = self._serving_grams_for_item(food_name, serving_size)
            if grams is None or grams < MIN_PORTION_GRAMS:
                continue
            for factor in PORTION_REDUCTION_FACTORS:
                new_grams = grams * factor
                if new_grams < MIN_PORTION_GRAMS:
                    continue
                new_serving = _format_grams_serving(new_grams)
                if round(new_grams, 1) >= round(grams, 1):
                    continue
                new_meal = list(node.meal)
                new_meal[idx] = (food_name, new_serving)
                new_meal_t = tuple(new_meal)
                action = f"Reduce portion of {food_name}: {serving_size} -> {new_serving}"
                out.append(
                    _Node(
                        meal=new_meal_t,
                        actions=node.actions + (action,),
                        edits_count=node.edits_count + 1,
                    )
                )

        # Swap actions (same category only).
        for idx in range(self._original_count):
            food_name, serving_size = node.meal[idx]
            for replacement in self._swap_candidates(food_name):
                if replacement == food_name:
                    continue
                new_meal = list(node.meal)
                new_meal[idx] = (replacement, serving_size)
                new_meal_t = tuple(new_meal)
                if meal_has_duplicate_replacement_across_distinct_foods(
                    self._start_meal,
                    new_meal_t,
                    self._original_count,
                ):
                    continue
                action = f"Swap {food_name} -> {replacement}"
                out.append(
                    _Node(
                        meal=new_meal_t,
                        actions=node.actions + (action,),
                        edits_count=node.edits_count + 1,
                    )
                )

        # Add actions (low-risk add list).
        for add_food in self._add_candidates():
            if any(name == add_food for name, _ in node.meal):
                continue
            new_meal = tuple(list(node.meal) + [(add_food, "100g")])
            action = f"Add {add_food} (100g)"
            out.append(
                _Node(
                    meal=new_meal,
                    actions=node.actions + (action,),
                    edits_count=node.edits_count + 1,
                )
            )
        return out

    def _swap_candidates(self, food_name: str) -> List[str]:
        src_category = infer_food_category(food_name)
        if src_category == "other":
            return []

        pool = [
            c
            for c in self._all_foods
            if c != food_name and infer_food_category(c) == src_category
        ]

        # Grain/starch: same coarse category is not enough (rice vs pasta salad).
        if src_category == "grain_starch":
            src_sub = infer_grain_starch_subfamily(food_name)
            if src_sub is not None:
                pool = [
                    c
                    for c in pool
                    if infer_grain_starch_subfamily(c) == src_sub
                ]

        # Prefer same-or-lower GI first, then lower GL at a standard portion, then name.
        src_gi = self._safe_gi(food_name)
        ranked = sorted(
            pool,
            key=lambda c: (
                self._safe_gi(c) > src_gi,
                self._safe_gi(c),
                self._safe_gl(c),
                c,
            ),
        )
        return ranked[:SWAP_CANDIDATE_SLICE]

    def _add_candidates(self) -> List[str]:
        ranked: List[Tuple[float, str]] = []
        for food in self._all_foods:
            category = infer_food_category(food)
            if category not in {"vegetable", "legume", "protein"}:
                continue
            features = self.knowledge_base.get_nutrition_features(food, "100g")
            gi = float(features["glycemic_index"])
            fiber_g = float(features["fiber"])
            if gi <= ADD_CANDIDATE_GI_MAX and fiber_g >= ADD_CANDIDATE_MIN_FIBER:
                ranked.append((fiber_g, food))
        ranked.sort(key=lambda t: (-t[0], t[1]))
        return [name for _, name in ranked[:ADD_CANDIDATE_SLICE]]

    def _safe_gi(self, food_name: str) -> float:
        return float(self.knowledge_base.get_nutrition_features(food_name, "100g")["glycemic_index"])

    def _safe_gl(self, food_name: str) -> float:
        return float(
            self.knowledge_base.get_nutrition_features(food_name, "100g")["glycemic_load"]
        )

    def _serving_grams_for_item(self, food_name: str, serving_size: str) -> Optional[float]:
        """Resolve the meal item's serving size to grams using Module 1 scaling rules."""
        try:
            feats = self.knowledge_base.get_nutrition_features(food_name, serving_size)
        except (FoodNotFoundError, MissingDataError, ValueError, TypeError):
            return None
        raw = feats.get("serving_size_grams")
        if raw is None:
            return None
        grams = float(raw)
        if grams <= 0:
            return None
        return grams

    def _canonical(self, meal: Tuple[Tuple[str, str], ...]) -> Tuple[Tuple[str, str], ...]:
        # Canonicalize while preserving which positions correspond to the original
        # meal (so swaps are restricted to removing/replacing original foods).
        orig_part = meal[: self._original_count]
        added_part = meal[self._original_count :]
        return (orig_part, tuple(sorted(added_part)))

    def _normalize_food_for_diversity(self, food_name: str) -> str:
        """Normalize food name for diversity checks.

        Strips common cooking/prep modifiers so two suggestions that only differ
        by prep style don't count as “different foods”.
        """
        lowered = (food_name or "").lower().strip()
        # Multi-word modifiers first (so "from concentrate" is removed as a phrase).
        for term in sorted(_DIVERSITY_PREP_TERMS, key=len, reverse=True):
            lowered = lowered.replace(term, " ")
        return " ".join(lowered.split())

    def _candidate_diversity_signature(
        self,
        candidate: Suggestion,
        *,
        start_meal: Tuple[Tuple[str, str], ...],
    ) -> set[str]:
        """Build a diversity signature from the candidate meal edit.

        The signature is the set of *underlying* food names introduced by edits
        (swaps on original positions + added items), plus stable keys for
        portion-only changes on original slots. Cooking/prep modifiers are
        normalized so prep variants don't count as “different foods.”
        """
        orig_count = len(start_meal)
        edited = [(i["food_name"], i["serving_size"]) for i in candidate["edited_meal"]]

        signature: set[str] = set()
        # Include swapped-in foods (positions that correspond to original meal items).
        for idx in range(orig_count):
            original_food, original_size = start_meal[idx]
            edited_food = edited[idx][0] if idx < len(edited) else original_food
            edited_size = edited[idx][1] if idx < len(edited) else original_size
            if edited_food != original_food:
                signature.add(self._normalize_food_for_diversity(edited_food))
            elif edited_size.strip() != original_size.strip():
                signature.add(f"portion:{idx}:{edited_size.strip()}")

        # Include added foods (items beyond original positions).
        for idx in range(orig_count, len(edited)):
            signature.add(self._normalize_food_for_diversity(edited[idx][0]))

        # If the signature is empty (should be rare since goal candidates imply edits),
        # return a sentinel so it doesn't accidentally become “disjoint from everything.”
        return signature if signature else {EMPTY_DIVERSITY_SIGNATURE_SENTINEL}

    def _select_diverse(
        self,
        candidates: Sequence[Suggestion],
        k: int,
        *,
        start_meal: Tuple[Tuple[str, str], ...],
    ) -> List[Suggestion]:
        """Select up to k suggestions with distinct underlying edits."""
        if not candidates or k <= 0:
            return []

        selected: List[Suggestion] = []
        selected_sigs: List[set[str]] = []
        candidate_sigs: List[set[str]] = [
            self._candidate_diversity_signature(c, start_meal=start_meal) for c in candidates
        ]

        # Strict phase: require disjoint underlying new-food sets.
        for i, c in enumerate(candidates):
            if len(selected) >= k:
                break
            s = candidate_sigs[i]
            if all(s.isdisjoint(prev) for prev in selected_sigs):
                selected.append(c)
                selected_sigs.append(s)

        if len(selected) >= k:
            return selected[:k]

        # Relaxed phase: allow up to 1 overlap.
        for i, c in enumerate(candidates):
            if len(selected) >= k:
                break
            if c in selected:
                continue
            s = candidate_sigs[i]
            if all(len(s.intersection(prev)) <= MAX_ALLOWED_DIVERSITY_OVERLAP for prev in selected_sigs):
                selected.append(c)
                selected_sigs.append(s)

        return selected[:k]
