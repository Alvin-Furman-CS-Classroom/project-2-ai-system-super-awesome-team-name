"""
Food Safety Engine: Evaluates food safety using propositional logic rules.

Uses Module 1 (NutritionKnowledgeBase) to get nutrition features, then applies
propositional rules from safety_rules module to determine safety label and explanation.

Created 2/3/2026
Authors: Jia Lin and Della Avent
"""

from typing import Dict, Optional

from src.module1.knowledge_base import NutritionKnowledgeBase, FoodNotFoundError, MissingDataError
from src.module2.safety_rules import evaluate_propositions


class FoodSafetyEngine:
    """
    Evaluates blood-sugar safety of individual foods using propositional logic rules.
    
    Uses a NutritionKnowledgeBase (Module 1) to fetch nutrition features, then applies
    propositional rules to classify foods as safe, caution, or unsafe.
    """
    
    def __init__(self, knowledge_base: NutritionKnowledgeBase, thresholds: Optional[Dict] = None) -> None:
        """Initialize the food safety engine.
        
        Args:
            knowledge_base: Instance of NutritionKnowledgeBase (Module 1) to query for nutrition features.
            thresholds: Optional dict to override default thresholds. If None, uses defaults from safety_rules.
                       Format: {"safe_gl": 10.0, "caution_gl": 20.0, "safe_gi": 55.0, "caution_gi": 70.0}
        
        Raises:
            TypeError: If knowledge_base is not a NutritionKnowledgeBase instance.
        """
        # TODO: Validate knowledge_base is correct type
        # TODO: Store knowledge_base as instance variable
        # TODO: If thresholds provided, store them (or update safety_rules constants)
        #       For now, can ignore thresholds parameter if using module-level constants
        pass
    
    def evaluate_food(self, food_name: str, serving_size: str = "100g") -> Dict[str, str]:
        """Evaluate safety of a food at the given serving size.
        
        Args:
            food_name: Food name (case-insensitive, whitespace-tolerant).
            serving_size: Serving size string. Formats: "100g", "200 g", "1 serving", "2.5 servings".
                         Defaults to "100g".
        
        Returns:
            Dict with keys:
            - "safety_label": "safe", "caution", or "unsafe"
            - "explanation": Human-readable explanation of which rules fired
        
        Raises:
            FoodNotFoundError: If food name not found in knowledge base (from Module 1).
            MissingDataError: If required nutrition data missing (from Module 1).
            ValueError: If serving_size format invalid (from Module 1).
        """
        # TODO: Implement
        # 1. Call self.knowledge_base.get_nutrition_features(food_name, serving_size)
        #    This will raise FoodNotFoundError, MissingDataError, or ValueError if needed
        # 2. Pass features dict to evaluate_propositions() from safety_rules
        # 3. Get (label, explanation) tuple back
        # 4. Return {"safety_label": label, "explanation": explanation}
        pass
