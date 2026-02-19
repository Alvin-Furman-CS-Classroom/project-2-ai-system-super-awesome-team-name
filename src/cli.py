"""
Terminal UI for GlycemicGuard - Adaptive Diabetic Diet Advisor.

Provides command-line interface for interacting with Modules 1-5.
"""

import sys
from pathlib import Path
from typing import Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.module1.knowledge_base import NutritionKnowledgeBase, FoodNotFoundError, MissingDataError
from src.module2.food_safety_engine import FoodSafetyEngine
from src.food_matcher import FoodMatcher


def normalize_food_name(name: str) -> str:
    """Normalize food name (same logic as Module 1's _normalize_name)."""
    if not name:
        return ""
    return " ".join(name.lower().strip().split())


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
        
        # Display options
        print(f"\nFound {len(neighbors)} similar foods:")
        for i, (food_name, similarity) in enumerate(neighbors, 1):
            print(f"  {i}. {food_name} (similarity: {similarity:.2f})")
        
        # Prompt user
        print(f"\nOptions:")
        print(f"  Enter 1-{len(neighbors)} to select a food")
        if offset + top_k < len(kb.list_all_foods()):
            print(f"  Enter 'next' to see next {top_k} options")
        print(f"  Enter 'cancel' to go back")
        
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


def display_food_safety(features: dict, safety_result: dict):
    """Display nutrition features and safety information."""
    print("\n" + "="*50)
    print("FOOD SAFETY ANALYSIS")
    print("="*50)
    
    # Safety label
    label = safety_result["safety_label"].upper()
    label_colors = {
        "SAFE": "✓",
        "CAUTION": "⚠",
        "UNSAFE": "✗"
    }
    symbol = label_colors.get(label, "•")
    print(f"\nSafety: {symbol} {label}")
    print(f"Explanation: {safety_result['explanation']}")
    
    # Nutrition features
    print(f"\nNutrition Information:")
    print(f"  Glycemic Index (GI): {features['glycemic_index']:.1f}")
    print(f"  Glycemic Load (GL): {features['glycemic_load']:.1f}")
    print(f"  Serving Size: {features['serving_size_grams']:.1f}g")
    print(f"\nMacronutrients (per serving):")
    print(f"  Carbohydrates: {features['carbohydrates']:.1f}g")
    print(f"  Fiber: {features['fiber']:.1f}g")
    print(f"  Protein: {features['protein']:.1f}g")
    print(f"  Fat: {features['fat']:.1f}g")
    print(f"  Processing Level: {features['processing_level']}")
    print("="*50)


def main():
    """Main entry point for terminal UI."""
    print("="*50)
    print("GlycemicGuard - Adaptive Diabetic Diet Advisor")
    print("="*50)
    
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
    print("Ready!\n")
    
    # Main loop
    while True:
        print("\n" + "="*50)
        print("MAIN MENU")
        print("="*50)
        print("1. Check food safety")
        print("2. Exit")
        
        choice = input("\nChoose option: ").strip()
        
        if choice == "1":
            try:
                # Prompt for food selection (with nearest neighbor search)
                selected_food = prompt_food_selection(kb, matcher)
                
                if selected_food is None:
                    print("Cancelled.")
                    continue
                
                # Get serving size
                serving_size = input(f"\nEnter serving size for '{selected_food}' (default: 100g): ").strip()
                if not serving_size:
                    serving_size = "100g"
                
                # Get nutrition features (Module 1)
                features = kb.get_nutrition_features(selected_food, serving_size)
                
                # Get safety evaluation (Module 2)
                safety_result = safety_engine.evaluate_food(selected_food, serving_size)
                
                # Display results
                display_food_safety(features, safety_result)
                
            except FoodNotFoundError as e:
                print(f"\nError: {e}")
            except MissingDataError as e:
                print(f"\nError: {e}")
            except ValueError as e:
                print(f"\nError: {e}")
            except Exception as e:
                print(f"\nUnexpected error: {e}")
        
        elif choice == "2":
            print("\nGoodbye!")
            break
        
        else:
            print("Invalid choice. Please enter 1 or 2.")


if __name__ == "__main__":
    main()
