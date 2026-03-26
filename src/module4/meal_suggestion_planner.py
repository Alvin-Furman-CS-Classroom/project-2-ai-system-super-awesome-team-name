"""Module 4: Search-based meal modification suggestions."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Sequence, Tuple, TypedDict

from src.module1.knowledge_base import NutritionKnowledgeBase
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
    "al dente",
    "from concentrate",
    "concentrate",
)


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

        start_meal = tuple((item["food_name"], item["serving_size"]) for item in meal_items)
        start_node = _Node(meal=start_meal, actions=tuple(), edits_count=0)
        frontier: List[Tuple[Tuple[int, int, int], int, _Node]] = []
        counter = 0
        heapq.heappush(frontier, (self._priority_tuple(start_node, original_level, algorithm), counter, start_node))

        best_seen_edits: Dict[Tuple[Tuple[str, str], ...], int] = {self._canonical(start_node.meal): 0}
        found_candidates: List[Suggestion] = []
        expansions = 0
        # Collect more than we will ultimately display, then pick a diverse subset.
        max_found_candidates = min(50, max(10, desired_count * 8))

        while (
            frontier
            and len(found_candidates) < max_found_candidates
            and expansions < self.max_expansions
        ):
            _, _, node = heapq.heappop(frontier)
            expansions += 1

            if node.edits_count > 0:
                analysis = self.meal_risk_analyzer.analyze_meal(
                    [{"food_name": f, "serving_size": s} for f, s in node.meal]
                )
                new_category = analysis["meal_risk_category"]
                if self._is_goal(original_level, new_category):
                    found_candidates.append(
                        {
                            "edited_meal": [{"food_name": f, "serving_size": s} for f, s in node.meal],
                            "actions": list(node.actions),
                            "resulting_category": new_category,
                            "resulting_score": float(analysis["risk_score"]),
                        }
                    )
                    continue

            if node.edits_count >= self.max_edits:
                continue

            for next_node in self._expand(node):
                key = self._canonical(next_node.meal)
                prev_best = best_seen_edits.get(key)
                if prev_best is not None and prev_best <= next_node.edits_count:
                    continue
                best_seen_edits[key] = next_node.edits_count
                counter += 1
                heapq.heappush(
                    frontier,
                    (self._priority_tuple(next_node, original_level, algorithm), counter, next_node),
                )

        found_candidates.sort(key=lambda s: (len(s["actions"]), s["resulting_score"]))
        target = "Any one of these suggestions should lower your meal risk by at least one category."
        diverse = self._select_diverse(found_candidates, desired_count)
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

    def _priority_tuple(self, node: _Node, original_level: int, algorithm: str) -> Tuple[int, int, int]:
        if algorithm.lower() == "ucs":
            return (node.edits_count, 0, 0)
        h = self._heuristic(node, original_level)
        return (node.edits_count + h, node.edits_count, h)

    def _heuristic(self, node: _Node, original_level: int) -> int:
        if node.edits_count == 0:
            return 1
        analysis = self.meal_risk_analyzer.analyze_meal(
            [{"food_name": f, "serving_size": s} for f, s in node.meal]
        )
        if self._is_goal(original_level, analysis["meal_risk_category"]):
            return 0
        return 1

    def _is_goal(self, original_level: int, new_category: str) -> bool:
        new_level = _RISK_TO_LEVEL.get(new_category, 0)
        return new_level <= max(0, original_level - 1)

    def _expand(self, node: _Node) -> List[_Node]:
        out: List[_Node] = []

        # Swap actions (same category only).
        for idx, (food_name, serving_size) in enumerate(node.meal):
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
                neighbors = self.matcher.find_nearest_neighbors(food_name, top_k=60, offset=0)
                for candidate, _ in neighbors:
                    if infer_food_category(candidate) == src_category:
                        pool.append(candidate)
            except Exception:
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
        return ranked[:8]

    def _add_candidates(self) -> List[str]:
        pool: List[str] = []
        for food in self._all_foods:
            category = infer_food_category(food)
            if category not in {"vegetable", "legume", "protein"}:
                continue
            features = self.knowledge_base.get_nutrition_features(food, "100g")
            if float(features["glycemic_index"]) <= 55.0 and float(features["fiber"]) >= 1.5:
                pool.append(food)
        pool.sort(key=lambda f: (-float(self.knowledge_base.get_nutrition_features(f, "100g")["fiber"]), f))
        return pool[:10]

    def _safe_gi(self, food_name: str) -> float:
        return float(self.knowledge_base.get_nutrition_features(food_name, "100g")["glycemic_index"])

    def _canonical(self, meal: Tuple[Tuple[str, str], ...]) -> Tuple[Tuple[str, str], ...]:
        return tuple(sorted(meal))

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

    def _changed_new_foods_from_actions(self, actions: Sequence[str]) -> List[str]:
        new_foods: List[str] = []
        for a in actions:
            if a.startswith("Swap "):
                # "Swap old -> new"
                if "->" in a:
                    new_food = a.split("->", 1)[1].strip()
                    new_foods.append(new_food)
            elif a.startswith("Add "):
                # "Add X (100g)"
                core = a[len("Add ") :]
                if " (" in core:
                    new_foods.append(core.split(" (", 1)[0].strip())
                else:
                    new_foods.append(core.strip())
        return new_foods

    def _select_diverse(self, candidates: Sequence[Suggestion], k: int) -> List[Suggestion]:
        """Select up to k suggestions that differ in underlying food changes."""
        if not candidates or k <= 0:
            return []

        sigs: List[set[str]] = []
        for c in candidates:
            new_foods = self._changed_new_foods_from_actions(c["actions"])
            sigs.append({self._normalize_food_for_diversity(f) for f in new_foods if f})

        selected: List[Suggestion] = []
        selected_sigs: List[set[str]] = []

        # Strict phase: require disjoint underlying new-food sets.
        for i, c in enumerate(candidates):
            if len(selected) >= k:
                break
            s = sigs[i]
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
            s = sigs[i]
            if all(len(s.intersection(prev)) <= 1 for prev in selected_sigs):
                selected.append(c)
                selected_sigs.append(s)

        return selected[:k]
