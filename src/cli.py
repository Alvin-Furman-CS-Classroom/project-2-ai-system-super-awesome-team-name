"""
Terminal UI for GlycemicGuard - Adaptive Diabetic Diet Advisor.

Provides command-line interface for interacting with Modules 1-5. When the user enters
a food name that does not exactly match the knowledge base, the CLI uses word embeddings
from the sentence-transformers library (see src.food_matcher.FoodMatcher) to suggest
semantically similar foods.
"""

import re
import sys
from pathlib import Path
from typing import FrozenSet, Optional

# Phrases that contain " and " but should stay one search query (not split into two foods).
_MEAL_COMPOUND_PHRASES: FrozenSet[str] = frozenset(
    {
        "mac and cheese",
        "macaroni and cheese",
        "bread and butter",
        "salt and pepper",
        "fish and chips",
        "peanut butter and jelly",
        "ham and cheese",
        "bacon and eggs",
        "egg and cheese",
        "rice and beans",
        "chips and salsa",
        "sweet and sour",
        "chicken and waffles",
        "cookies and cream",
        "gin and tonic",
        "oil and vinegar",
    }
)

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.module1.knowledge_base import NutritionKnowledgeBase, FoodNotFoundError, MissingDataError
from src.module2.food_safety_engine import FoodSafetyEngine
from src.module3.meal_risk_analyzer import MealRiskAnalyzer
from src.module4.meal_suggestion_planner import MealSuggestionPlanner
from src.food_matcher import FoodMatcher


def _print_art(lines: tuple[str, ...], indent: str = "  ") -> None:
    """Print multi-line ASCII art with consistent left padding."""
    for line in lines:
        print(f"{indent}{line}")


# Tiny terminal-safe doodles (ASCII only so old Windows consoles stay happy).
ART_WELCOME_MASCOT: tuple[str, ...] = (
    r"       _____       ",
    r"      /     \      ",
    r"     | ^   ^ |     ",
    r"      \  w  /      ",
    r"       -----       ",
    r"      _|   |_      ",
)

ART_MENU_SPARKLE: tuple[str, ...] = (
    r"    *  .  *  .  *  .  *  ",
    r"  .    ~ menu ~    .      ",
    r"    *  .  *  .  *  .  *  ",
)

ART_APPLE: tuple[str, ...] = (
    r"       ,,        ",
    r"      ( @ )       ",
    r"       `''        ",
)

ART_MEAL_PLATE: tuple[str, ...] = (
    r"      .------.      ",
    r"     /        \     ",
    r"    |   nom!   |    ",
    r"     \________/     ",
    r"       \____/       ",
)

ART_LOADING: tuple[str, ...] = (
    r"   ... mixing numbers ...   ",
)

ART_GOODBYE: tuple[str, ...] = (
    r"       \o/         ",
    r"        |   bye!   ",
    r"       / \         ",
    r"      z   z        ",
)


def normalize_food_name(name: str) -> str:
    """Normalize food name (same logic as Module 1's _normalize_name)."""
    if not name:
        return ""
    return " ".join(name.lower().strip().split())


def split_meal_line(line: str) -> list[str]:
    """
    Split one user line into several ingredient search strings.

    - Commas separate items: ``spaghetti, meatballs, tomato sauce``.
    - If there is no comma, `` and `` also separates items:
      ``spaghetti and meatballs`` → two parts.
    - Known *compound dishes* (e.g. ``mac and cheese``) stay as one query.
    """
    raw = (line or "").strip()
    if not raw:
        return []
    if raw.lower() in _MEAL_COMPOUND_PHRASES:
        return [raw]

    parts: list[str] = []
    for segment in re.split(r"\s*,\s*", raw):
        seg = segment.strip()
        if not seg:
            continue
        if seg.lower() in _MEAL_COMPOUND_PHRASES:
            parts.append(seg)
            continue
        if re.search(r"\s+and\s+", seg, flags=re.IGNORECASE):
            sub = re.split(r"\s+and\s+", seg, flags=re.IGNORECASE)
            parts.extend(s.strip() for s in sub if s.strip())
        else:
            parts.append(seg)
    return parts


def _prompt_serving_until_valid(kb: NutritionKnowledgeBase, food_name: str) -> Optional[str]:
    """Ask for a serving size and validate against the KB. Returns None if user cancels."""
    while True:
        serving_size = input(
            f"Enter serving size for '{food_name}' (default: 100g): "
        ).strip()
        if not serving_size:
            serving_size = "100g"
        if serving_size.lower() == "cancel":
            return None
        try:
            _ = kb.get_nutrition_features(food_name, serving_size)
        except ValueError:
            print("\nServing size format not recognized.")
            print("Examples: '100g', '200 g', '1 serving', '2.5 servings'.")
            print("Type 'cancel' to abort this item.")
            continue
        return serving_size


def prompt_food_selection(kb: NutritionKnowledgeBase, matcher: FoodMatcher) -> Optional[str]:
    """Prompt user for food selection with nearest neighbor search.
    
    Flow:
    1. Check for exact match - if found, return immediately (no prompt)
    2. If no exact match, find top 5 nearest neighbors using embeddings
    3. Show options, let user pick one or ask for "next 5"
    4. Repeat until user picks or cancels
    
    Args:
        kb: NutritionKnowledgeBase instance (Module 1).
        matcher: FoodMatcher instance for nearest neighbor search.
    
    Returns:
        Selected food name (normalized), or None if user cancels.
    """
    query = input("\nEnter food name: ").strip()
    
    if not query:
        return None
    
    # Step 1: Check for exact match (case-insensitive, whitespace-tolerant)
    normalized_query = normalize_food_name(query)
    all_foods = kb.list_all_foods()
    
    if normalized_query in all_foods:
        # Exact match found - return immediately without prompting
        return normalized_query
    
    # Step 2: No exact match - use nearest neighbor search
    offset = 0
    top_k = 5
    
    while True:
        # Get nearest neighbors
        neighbors = matcher.find_nearest_neighbors(query, top_k=top_k, offset=offset)
        
        if not neighbors:
            print(f"\nNo similar foods found for '{query}'.")
            return None
        
        # Display options (hide raw similarity scores from user)
        print(f"\nFound {len(neighbors)} similar foods:")
        for i, (food_name, _similarity) in enumerate(neighbors, 1):
            print(f"  {i}. {food_name}")
        
        # Prompt user
        print(f"\nOptions:")
        print(f"  Enter 1-{len(neighbors)} to select a food")
        if offset + top_k < len(kb.list_all_foods()):
            print(f"  Enter 'next' to see next {top_k} options")
        print(f"  Enter 'cancel' to start over")
        
        choice = input("Your choice: ").strip().lower()
        
        # Handle selection
        if choice == "cancel":
            return None
        
        if choice == "next":
            # Show next 5
            offset += top_k
            continue
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(neighbors):
                selected_food = neighbors[choice_num - 1][0]
                return selected_food
            else:
                print(f"Please enter a number between 1 and {len(neighbors)}.")
        except ValueError:
            print("Invalid input. Please enter a number, 'next', or 'cancel'.")

def select_food_by_query(query: str, kb: NutritionKnowledgeBase, matcher: FoodMatcher) -> Optional[str]:
    """
    Helper for meal input:
    - Accepts the user's raw `query`
    - Returns a normalized food name from the KB, or None if cancelled / no match
    """
    normalized_query = normalize_food_name(query)
    all_foods = kb.list_all_foods()

    if normalized_query in all_foods:
        return normalized_query

    offset = 0
    top_k = 5

    while True:
        neighbors = matcher.find_nearest_neighbors(query, top_k=top_k, offset=offset)

        if not neighbors:
            print(f"\nNo similar foods found for '{query}'.")
            return None

        print(f"\nFound {len(neighbors)} similar foods:")
        for i, (food_name, _similarity) in enumerate(neighbors, 1):
            print(f"  {i}. {food_name}")

        print(f"\nOptions:")
        print(f"  Enter 1-{len(neighbors)} to select a food")
        if offset + top_k < len(kb.list_all_foods()):
            print(f"  Enter 'next' to see next {top_k} options")
        print(f"  Enter 'cancel' to start over")

        choice = input("Your choice: ").strip().lower()

        if choice == "cancel":
            return None

        if choice == "next":
            offset += top_k
            continue

        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(neighbors):
                return neighbors[choice_num - 1][0]
            print(f"Please enter a number between 1 and {len(neighbors)}.")
        except ValueError:
            print("Invalid input. Please enter a number, 'next', or 'cancel'.")


def prompt_meal_items(
    kb: NutritionKnowledgeBase,
    matcher: FoodMatcher,
) -> Optional[list[dict]]:
    """
    Prompt the user to build a meal for Module 3.

    **One line of foods** (commas and/or ``and`` between items), then match each
    ingredient to the knowledge base and optionally use the **same serving for all**.

    Returns:
      - list of {"food_name": str, "serving_size": str}
      - None if cancelled
    """
    print("\nBuild your meal for Module 3.")
    print("Enter all foods on one line, separated by commas or by 'and'.")
    print("Examples: spaghetti, meatballs, tomato sauce")
    print("          spaghetti and meatballs")
    print("Type 'cancel' at any prompt to return to the main menu.\n")

    while True:
        line = input(
            "Enter your foods (comma-separated, or use 'and' between items):\n> "
        ).strip()
        if line.lower() == "cancel":
            return None
        parts = split_meal_line(line)
        if not parts:
            print("No foods found. Try again or type 'cancel'.")
            continue

        print(f"\nParsed {len(parts)} ingredient(s): {', '.join(parts)}")

        same = input(
            "Use the same serving size for every item? (y/n, default y): "
        ).strip().lower()
        use_same = same in ("", "y", "yes")
        default_serving = "100g"
        if use_same:
            sv = input(
                "Serving size for all items (default 100g): "
            ).strip()
            if sv.lower() == "cancel":
                return None
            if sv:
                default_serving = sv

        resolved: list[tuple[str, str]] = []
        shared_serving_validated = False
        for i, query in enumerate(parts, 1):
            print(f"\n--- Ingredient {i}/{len(parts)}: {query!r} ---")
            selected_food = select_food_by_query(query, kb, matcher)
            if selected_food is None:
                print("Skipped this ingredient. You can re-run meal entry to try again.")
                continue
            if use_same:
                if not shared_serving_validated:
                    while True:
                        try:
                            _ = kb.get_nutrition_features(
                                selected_food, default_serving
                            )
                            shared_serving_validated = True
                            break
                        except ValueError:
                            print(
                                "\nServing size format not recognized. "
                                "Examples: '100g', '200 g', '1 serving', '2.5 servings'."
                            )
                            default_serving = input(
                                "Serving size for all items (or 'cancel'): "
                            ).strip()
                            if default_serving.lower() == "cancel":
                                return None
                            if not default_serving:
                                default_serving = "100g"
                    serving = default_serving
                else:
                    serving = default_serving
            else:
                serving = _prompt_serving_until_valid(kb, selected_food)
                if serving is None:
                    return None
            resolved.append((selected_food, serving))

        if not resolved:
            print("No foods were added. Try again or type 'cancel'.")
            continue

        return [
            {"food_name": name, "serving_size": size} for name, size in resolved
        ]


def display_food_safety(features: dict, safety_result: dict):
    """Display a simplified, plain-language food safety summary."""
    print()
    _print_art(ART_APPLE)
    print("  +----------------------------------------------+")
    print("  |       One food - quick safety peek           |")
    print("  +----------------------------------------------+")
    
    # Safety label
    label = safety_result["safety_label"].upper()
    label_colors = {
        "SAFE": "✓",
        "CAUTION": "⚠",
        "UNSAFE": "✗"
    }
    symbol = label_colors.get(label, "•")
    plain_label = {
        "SAFE": "Lower spike risk",
        "CAUTION": "Medium spike risk",
        "UNSAFE": "High spike risk",
    }.get(label, label.title())

    print(f"\n  Overall: {symbol} {plain_label}")
    print(f"  Why: {safety_result['explanation']}")

    # Show only high-value, easy-to-understand metrics.
    print("\n  Quick facts (this serving):")
    print(f"    • Sugar-impact (glycemic load): {features['glycemic_load']:.1f}")
    print(
        f"    • Carbs: {features['carbohydrates']:.1f}g | "
        f"Fiber: {features['fiber']:.1f}g | Protein: {features['protein']:.1f}g"
    )
    print(f"    • Serving: {features['serving_size_grams']:.1f}g")
    print("  ─────────────────────────────────────────────")

    show_more = input("\n  More numbers? (y/n): ").strip().lower()
    if show_more in ("y", "yes"):
        print("\n  Extra detail:")
        print(f"    • Glycemic index (GI): {features['glycemic_index']:.1f}")
        print(f"    • Fat: {features['fat']:.1f}g")
        print(f"    • Processing: {features['processing_level']}")
        print("  ─────────────────────────────────────────────")


def meal_risk_category_plain(category: str) -> str:
    """Plain-language label for Module 3/4 meal risk categories."""
    return {
        "low": "Lower spike risk",
        "medium": "Medium spike risk",
        "high": "High spike risk",
    }.get(category, category)


def meal_risk_category_cute(category: str) -> str:
    """Short friendly label with a tiny accent for the meal summary."""
    return {
        "low": "Lower spike risk - nice and steady",
        "medium": "Medium spike risk - room to tweak",
        "high": "Higher spike risk - worth a second look",
    }.get(category, meal_risk_category_plain(category))


def print_meal_score_and_scale_legend(meal_analysis: dict) -> None:
    """Under the headline score, explain the 0-100 meal risk scale in plain language."""
    score = float(meal_analysis["risk_score"])
    print(f"\n  Meal risk score: {score:.1f} / 100")
    print()
    print("  ─── Reading your score (0-100) ───")
    print("  This is a single snapshot from your foods' sugar impact (fiber and protein")
    print("  can nudge it toward gentler). Think blood-sugar friendliness:")
    print()
    print("    0 - 40   Most friendly on this scale - usually easier on glucose swings.")
    print("    40 - 70  Middle ground - worth planning around if you are sensitive.")
    print("    70 - 100 Least friendly here - bigger spike potential for many people.")
    print()
    print("  Lower is generally kinder to blood sugar; higher means more caution.")
    print("  ───────────────────────────")


def print_module4_meal_improvements(suggestion_result: dict) -> None:
    """Print tweak ideas in a light, friendly way (no long Module 4 lecture)."""
    if not suggestion_result["suggestions"]:
        print()
        print("  * Optional tweaks")
        print("  ───────────────────────────")
        if suggestion_result["status"] == "low_risk_no_suggestions_needed":
            print("  You are already in a gentle zone - no homework needed here. Enjoy!")
        else:
            print("  We could not find a simple swap bundle that bumps you down a whole")
            print("  tier this time. Smaller starchy portions or different sides might")
            print("  still help in real life - worth chatting with your care team too.")
        print("  ───────────────────────────")
        return

    suggestions = suggestion_result["suggestions"]
    best = suggestions[0]
    print()
    print("  * Optional tweaks")
    print("  ───────────────────────────")
    print("  Here are some same-kind swaps or smaller servings that could soften")
    print("  the meal a notch (you pick what feels realistic!):")
    print()
    print("  >> Top pick")
    print(
        f"     After these changes: {meal_risk_category_plain(best['resulting_category'])} "
        f"| score {best['resulting_score']:.1f}/100"
    )
    print("     Steps:")
    for action in best["actions"]:
        print(f"       • {action}")

    if len(suggestions) > 1:
        print()
        print("  >> More ideas")
        for opt_idx, suggestion in enumerate(suggestions[1:], start=2):
            print()
            print(
                f"     Idea {opt_idx}: {meal_risk_category_plain(suggestion['resulting_category'])}, "
                f"score {suggestion['resulting_score']:.1f}/100"
            )
            for action in suggestion["actions"]:
                print(f"       • {action}")
    print("  ───────────────────────────")


def main():
    """Main entry point for terminal UI."""
    print()
    _print_art(ART_WELCOME_MASCOT)
    print("  +----------------------------------------------+")
    print("  |  GlycemicGuard - your friendly meal buddy  |")
    print("  +----------------------------------------------+")
    print("  (Nutrition nudges, not medical advice - always check with your care team.)")
    print()
    
    # Initialize knowledge base (Module 1)
    csv_path = "src/module1/nutrition_data.csv"
    print(f"\nLoading knowledge base from {csv_path}...")
    try:
        kb = NutritionKnowledgeBase(csv_path)
        print(f"Loaded {len(kb.list_all_foods())} foods.")
    except FileNotFoundError:
        print(f"Error: Could not find {csv_path}")
        print("Please ensure the nutrition data CSV file exists.")
        return
    
    # Initialize food matcher (for nearest neighbor search)
    print("\nInitializing food name matcher...")
    food_names = kb.list_all_foods()
    matcher = FoodMatcher(food_names, use_embeddings=True)
    
    # Initialize safety engine (Module 2)
    print("Initializing safety engine...")
    safety_engine = FoodSafetyEngine(kb)
    print("  All set! Pick a menu option whenever you are ready.\n")

    # Initialize meal risk analyzer (Module 3).
    meal_risk_analyzer = MealRiskAnalyzer(
        knowledge_base=kb,
        food_safety_engine=safety_engine,
        enable_effective_gl_adjustments=True,
    )
    meal_suggestion_planner = MealSuggestionPlanner(
        knowledge_base=kb,
        meal_risk_analyzer=meal_risk_analyzer,
        max_edits=8,
        max_expansions=2000,
    )
    
    # Main loop
    while True:
        print()
        _print_art(ART_MENU_SPARKLE)
        print("  ───────── What would you like to do? ─────────")
        print("    1  Peek at one food (safety & quick facts)")
        print("    2  Build a meal & see spike-friendly feedback")
        print("    3  Exit - thanks for stopping by!")
        print("  ─────────────────────────────────────────────")
        
        choice = input("\n  Pick 1, 2, or 3: ").strip()
        
        if choice == "1":
            try:
                # Prompt for food selection (with nearest neighbor search)
                selected_food = prompt_food_selection(kb, matcher)
                
                if selected_food is None:
                    print("\n  No problem - cancelled.")
                    continue
                
                # Loop until we get a valid serving size
                while True:
                    serving_size = input(
                        f"\nEnter serving size for '{selected_food}' (default: 100g): "
                    ).strip()
                    if not serving_size:
                        serving_size = "100g"
                    
                    try:
                        # Get nutrition features (Module 1)
                        features = kb.get_nutrition_features(selected_food, serving_size)
                        # Get safety evaluation (Module 2)
                        safety_result = safety_engine.evaluate_food(selected_food, serving_size)
                    except ValueError:
                        print("\nServing size format not recognized.")
                        print("Examples: '100g', '200 g', '1 serving', '2.5 servings'.")
                        print("Please try entering the serving size again.")
                        continue
                    
                    # Display results and break out of serving-size loop
                    display_food_safety(features, safety_result)
                    break
                
            except FoodNotFoundError as e:
                print(f"\nError: {e}")
            except MissingDataError as e:
                print(f"\nError: {e}")
            except Exception as e:
                print(f"\nUnexpected error: {e}")
        
        elif choice == "2":
            try:
                meal_items = prompt_meal_items(kb, matcher)
                if meal_items is None:
                    print("\n  No problem - cancelled.")
                    continue

                # Precompute per-food outputs and meal totals.
                per_food_results: list[dict] = []
                per_food_details: list[dict] = []
                total_gl = 0.0
                total_fiber_g = 0.0
                total_protein_g = 0.0

                for item in meal_items:
                    features = kb.get_nutrition_features(item["food_name"], item["serving_size"])
                    safety_result = safety_engine.evaluate_food(item["food_name"], item["serving_size"])

                    per_food_results.append(
                        {
                            "safety_label": safety_result["safety_label"],
                            "explanation": safety_result["explanation"],
                        }
                    )
                    per_food_details.append(
                        {
                            "food_name": item["food_name"],
                            "serving_size": item["serving_size"],
                            "features": features,
                            "safety_result": safety_result,
                        }
                    )

                    total_gl += float(features["glycemic_load"])
                    total_fiber_g += float(features["fiber"])
                    total_protein_g += float(features["protein"])

                print("\n  Crunching your meal... one moment!")
                _print_art(ART_LOADING)

                # Compute overall meal risk (Module 3) using precomputed totals.
                meal_analysis = meal_risk_analyzer.analyze_meal_from_precomputed(
                    meal_items=meal_items,
                    per_food_results=per_food_results,  # type: ignore[arg-type]
                    precomputed_totals={
                        "total_gl": total_gl,
                        "total_fiber_g": total_fiber_g,
                        "total_protein_g": total_protein_g,
                    },
                )

                # Compute Module 4 suggestions before printing anything, so the
                # whole report appears all at once.
                suggestion_result = meal_suggestion_planner.generate_suggestions(
                    meal_items,
                    original_category=meal_analysis["meal_risk_category"],
                    algorithm="astar",
                )

                print()
                _print_art(ART_MEAL_PLATE)
                print("  +----------------------------------------------+")
                print("  |           Your meal - the recap              |")
                print("  +----------------------------------------------+")
                print()
                print("  On your plate:")
                for idx, item in enumerate(meal_items, 1):
                    print(f"    {idx}. {item['food_name']} ({item['serving_size']})")

                cat = meal_analysis["meal_risk_category"]
                print()
                print(f"  Big picture: {meal_risk_category_cute(cat)}")
                print_meal_score_and_scale_legend(meal_analysis)

                # Keep this short and scannable: show top 3 factors.
                factors = meal_analysis["contributing_factors"][:3]
                print()
                print("  Here is what stood out:")
                for f in factors:
                    print(f"    • {f}")
                if len(meal_analysis["contributing_factors"]) > 3:
                    print("    • ...and a bit more detail if you open the full view below.")

                print_module4_meal_improvements(suggestion_result)

                show_more = input("\n  Show full meal breakdown? (y/n): ").strip().lower()
                if show_more in ("y", "yes"):
                    print("\n  Full contributing factors:")
                    for f in meal_analysis["contributing_factors"]:
                        print(f"    • {f}")

                    print("\n  Per-food details:")
                    for idx, detail in enumerate(per_food_details, 1):
                        features = detail["features"]
                        safety_result = detail["safety_result"]
                        label = safety_result["safety_label"].upper()
                        plain_label = {
                            "SAFE": "Lower spike risk",
                            "CAUTION": "Medium spike risk",
                            "UNSAFE": "High spike risk",
                        }.get(label, label.title())

                        print(f"\n    {idx}. {detail['food_name']} ({detail['serving_size']})")
                        print(f"       Result: {plain_label}")
                        print(f"       Why: {safety_result['explanation']}")
                        print(
                            f"       Quick facts: GL {features['glycemic_load']:.1f}, "
                            f"carbs {features['carbohydrates']:.1f}g, "
                            f"fiber {features['fiber']:.1f}g, "
                            f"protein {features['protein']:.1f}g"
                        )

            except FoodNotFoundError as e:
                print(f"\nError: {e}")
            except MissingDataError as e:
                print(f"\nError: {e}")
            except ValueError as e:
                print(f"\nError: {e}")
            except Exception as e:
                print(f"\nUnexpected error: {e}")

        elif choice == "3":
            print()
            _print_art(ART_GOODBYE)
            print("\n  Take care - see you at the next meal!\n")
            break
        
        else:
            print("\n  Oops - try 1, 2, or 3.")


if __name__ == "__main__":
    main()
