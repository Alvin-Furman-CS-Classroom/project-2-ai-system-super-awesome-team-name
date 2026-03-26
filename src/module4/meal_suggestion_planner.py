"""Module 4: Search-based meal modification suggestions."""

from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Sequence, Tuple, TypedDict

from src.module1.knowledge_base import NutritionKnowledgeBase
from src.module3.meal_risk_analyzer import MealRiskAnalyzer

logger = logging.getLogger(__name__)

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
SWAP_NEIGHBORS_TOP_K: int = 60
SWAP_CANDIDATE_SLICE: int = 8

ADD_CANDIDATE_GI_MAX: float = 55.0
ADD_CANDIDATE_MIN_FIBER: float = 1.5
ADD_CANDIDATE_SLICE: int = 10

ABSOLUTE_MAX_FOUND_CANDIDATES: int = 50
MIN_FOUND_CANDIDATES: int = 10
FOUND_CANDIDATES_MULTIPLIER: int = 8

DEFAULT_ADD_SERVING_SIZE: str = "100g"

MAX_ALLOWED_DIVERSITY_OVERLAP: int = 1
EMPTY_DIVERSITY_SIGNATURE_SENTINEL: str = ""


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


def infer_food_category(food_name: str) -> str:
    """Assign a coarse category from food name tokens."""
    name = (food_name or "").lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for token in keywords:
            if token in name:
                return category
    return "other"


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
        matcher: Optional[object] = None,
        max_edits: int = 5,
        max_expansions: int = 300,
    ) -> None:
        self.knowledge_base = knowledge_base
        self.meal_risk_analyzer = meal_risk_analyzer
        self.matcher = matcher
        self.max_edits = max_edits
        self.max_expansions = max_expansions
        self._all_foods = self.knowledge_base.list_all_foods()
        self._original_count: int = 0

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
        target = "Any one of these suggestions should lower your meal risk by at least one category."
        start_meal = tuple((item["food_name"], item["serving_size"]) for item in meal_items)
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
    ) -> Tuple[_Node, List[Tuple[Tuple[int, int, float], int, _Node]], int, Dict[Tuple[Tuple[str, str], ...], int], Dict[Tuple[Tuple[str, str], ...], Tuple[str, float]]]:
        """Initialize frontier and memoization for the search."""
        start_node = _Node(meal=start_meal, actions=tuple(), edits_count=0)
        frontier: List[Tuple[Tuple[int, int, float], int, _Node]] = []
        counter = 0
        heapq.heappush(
            frontier,
            (self._priority_tuple(start_node, original_level, algorithm, analysis_category=None, risk_score=0.0), counter, start_node),
        )
        best_seen_edits: Dict[Tuple[Tuple[str, str], ...], int] = {
            self._canonical(start_node.meal): 0
        }
        analysis_cache: Dict[Tuple[Tuple[str, str], ...], Tuple[str, float]] = {}
        return start_node, frontier, counter, best_seen_edits, analysis_cache

    def _try_add_goal_candidate(
        self,
        *,
        node: _Node,
        original_level: int,
        analysis_cache: Dict[Tuple[Tuple[str, str], ...], Tuple[str, float]],
        found_candidates: List[Suggestion],
    ) -> bool:
        """If the node satisfies the goal, append it and return True."""
        if node.edits_count <= 0:
            return False

        analysis_category, risk_score = self._get_cached_analysis(
            node.meal, analysis_cache
        )
        if not self._is_goal(original_level, analysis_category):
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
        frontier: List[Tuple[Tuple[int, int, float], int, _Node]],
        counter: int,
        best_seen_edits: Dict[Tuple[Tuple[str, str], ...], int],
        original_level: int,
        algorithm: str,
        analysis_cache: Dict[Tuple[Tuple[str, str], ...], Tuple[str, float]],
    ) -> int:
        """Expand a node and enqueue successors into the frontier."""
        for next_node in self._expand(node):
            key = self._canonical(next_node.meal)
            prev_best = best_seen_edits.get(key)
            if prev_best is not None and prev_best <= next_node.edits_count:
                continue

            best_seen_edits[key] = next_node.edits_count
            counter += 1

            next_analysis_category, next_risk_score = self._get_cached_analysis(
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
    ) -> Tuple[int, int, float]:
        """
        Explicit lexicographic priority:
          1) edits_count (or edits_count + goal-distance for A*)
          2) edits_count (tie-break)
          3) resulting risk score (lower is better)
        """
        if algorithm.lower() == "ucs":
            return (node.edits_count, node.edits_count, float(risk_score))

        goal_met = False if analysis_category is None else self._is_goal(original_level, analysis_category)
        h = 0 if goal_met else 1
        return (node.edits_count + h, node.edits_count, float(risk_score))

    def _get_cached_analysis(
        self,
        meal: Tuple[Tuple[str, str], ...],
        cache: Dict[Tuple[Tuple[str, str], ...], Tuple[str, float]],
    ) -> Tuple[str, float]:
        """Memoize Module 3 analysis results during search."""
        key = self._canonical(meal)
        cached = cache.get(key)
        if cached is not None:
            return cached

        analysis = self.meal_risk_analyzer.analyze_meal(
            [{"food_name": f, "serving_size": s} for f, s in meal]
        )
        result = (analysis["meal_risk_category"], float(analysis["risk_score"]))
        cache[key] = result
        return result

    def _is_goal(self, original_level: int, new_category: str) -> bool:
        new_level = _RISK_TO_LEVEL.get(new_category, 0)
        return new_level <= max(0, original_level - 1)

    def _expand(self, node: _Node) -> List[_Node]:
        out: List[_Node] = []

        # Swap actions (same category only).
        for idx in range(self._original_count):
            food_name, serving_size = node.meal[idx]
            for replacement in self._swap_candidates(food_name):
                if replacement == food_name:
                    continue
                new_meal = list(node.meal)
                new_meal[idx] = (replacement, serving_size)
                action = f"Swap {food_name} -> {replacement}"
                out.append(
                    _Node(
                        meal=tuple(new_meal),
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

        pool: List[str] = []
        if self.matcher is not None and hasattr(self.matcher, "find_nearest_neighbors"):
            try:
                neighbors = self.matcher.find_nearest_neighbors(
                    food_name, top_k=SWAP_NEIGHBORS_TOP_K, offset=0
                )
                for candidate, _ in neighbors:
                    if infer_food_category(candidate) == src_category:
                        pool.append(candidate)
            except (AttributeError, TypeError, ValueError) as e:
                # Best-effort: if neighbor search fails, fall back to scanning all foods.
                logger.debug("Swap candidate neighbor search failed for %r: %s", food_name, e)
                pool = []

        if not pool:
            for candidate in self._all_foods:
                if infer_food_category(candidate) == src_category:
                    pool.append(candidate)

        # Keep lower-risk-direction candidates first.
        src_gi = self._safe_gi(food_name)
        ranked = sorted(
            {c for c in pool if c != food_name},
            key=lambda c: (self._safe_gi(c) > src_gi, self._safe_gi(c), c),
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
        (swaps on original positions + added items). Cooking/prep modifiers are
        normalized so prep variants don't count as “different foods.”
        """
        orig_count = len(start_meal)
        edited = [(i["food_name"], i["serving_size"]) for i in candidate["edited_meal"]]

        signature: set[str] = set()
        # Include swapped-in foods (positions that correspond to original meal items).
        for idx in range(orig_count):
            original_food = start_meal[idx][0]
            edited_food = edited[idx][0] if idx < len(edited) else original_food
            if edited_food != original_food:
                signature.add(self._normalize_food_for_diversity(edited_food))

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
