# Module 2: Single Food Safety Rules (Propositional Logic) - Implementation Plan

## Module Overview

**Topic:** Propositional Logic, Knowledge Bases, Inference  
**Checkpoint Due:** Checkpoint 2 (Feb 26)  
**Dependencies:** Module 1 (Nutrition Knowledge Base)

## Specification Summary

### Inputs
- Food name (string) — e.g., "white rice", "apple"
- Serving size (string, optional default) — e.g., "100g", "1 serving"

**Note:** Module 2 receives the same inputs that Module 1 accepts. It uses Module 1 to fetch nutrition features, then applies propositional logic rules to classify safety.

### Outputs
- **Safety label:** One of `"safe"`, `"caution"`, or `"unsafe"` (blood-sugar risk for that food at that serving).
- **Rule explanation:** Human-readable explanation of which rule(s) fired and why (e.g., "High glycemic load (15.2) exceeds safe threshold (10)").

### Integration Points
- **Upstream:** Module 1 — call `get_nutrition_features(food_name, serving_size)` to get GI, GL, macronutrients, processing level, etc.
- **Downstream:** Module 3 will consume safety labels and explanations per food to compute meal-level risk; Module 4 may use safety rules when suggesting swaps.

---

## Architecture & Design

### 1. Propositional Logic Representation

**Rules as propositions:**
- Encode safety criteria as logical conditions over nutrition features (propositions).
- Each rule is a condition that can be true/false; combined they determine the safety label.

**Example rule structure (conceptual):**
- Proposition: `glycemic_load <= SAFE_GL_THRESHOLD` → contributes to "safe"
- Proposition: `glycemic_load > CAUTION_GL_THRESHOLD` → contributes to "caution"
- Proposition: `glycemic_load > UNSAFE_GL_THRESHOLD` OR `glycemic_index > UNSAFE_GI_THRESHOLD` → "unsafe"
- Optional: propositions on processing level, fiber, or carbs per serving

**Thresholds (configurable constants):**
- Safe GL (e.g., ≤ 10), Caution GL (e.g., 10–20), Unsafe GL (e.g., > 20)
- Safe GI (e.g., ≤ 55), Caution GI (e.g., 55–70), Unsafe GI (e.g., > 70)

### 2. Inference Approach

**Forward evaluation (no backward chaining required):**
- Given a single food and serving, we have one set of feature values.
- Evaluate each proposition (rule condition) against those values.
- **Inference:** Combine proposition outcomes to assign exactly one label (safe / caution / unsafe), with a deterministic priority (e.g., if any "unsafe" condition holds → unsafe; else if any "caution" → caution; else → safe).
- Build explanation by recording which propositions were true and what their thresholds were.

### 3. Knowledge Base Usage

- Module 2 holds a reference to (or receives) a `NutritionKnowledgeBase` instance (Module 1).
- No separate persistent knowledge base for Module 2; the "knowledge" is the set of rules (thresholds and logic), which can live in code or a small config (e.g., dict or constants).
- Rule definitions can be viewed as a tiny internal knowledge base (propositional rules) that we evaluate using Module 1’s output.

### 4. File Structure

```
src/
├── module1/
│   └── ... (existing)
├── module2/
│   ├── __init__.py
│   ├── safety_rules.py       # Rule definitions (thresholds, proposition evaluation)
│   └── food_safety_engine.py # Main class: uses Module 1, applies rules, returns label + explanation
└── ...

unit_tests/
├── module2/
│   ├── __init__.py
│   └── test_food_safety_engine.py  # Unit tests (can mock Module 1)
└── ...

integration_tests/
├── module2/
│   └── test_module2_integration.py # Uses real Module 1 + real CSV
└── ...
```

**Alternative (simpler):** One file `src/module2/food_safety.py` containing both rule constants and the engine class, if the rule set stays small.

### 5. Key Methods (Proposed)

- `FoodSafetyEngine(knowledge_base: NutritionKnowledgeBase, thresholds: dict = None)`
  - Optional `thresholds` overrides default GL/GI limits.
- `evaluate_food(food_name: str, serving_size: str = "100g") -> dict`
  - Returns `{"safety_label": "safe"|"caution"|"unsafe", "explanation": "..."}`.
  - Internally: call `knowledge_base.get_nutrition_features(food_name, serving_size)`, then evaluate propositions and build explanation.
- `_evaluate_rules(features: dict) -> tuple[str, str]`
  - Private: given a features dict (from Module 1), evaluate all propositions and return `(label, explanation)`.
- Rule constants or a small `RuleSet` (e.g., list of (name, condition_fn, label_contribution)) for clarity and testability.

---

## Implementation Steps

### Phase 1: Rule Definition and Thresholds
1. **Define propositional rules and thresholds**
   - Choose default numeric thresholds (e.g., GL: safe ≤10, caution ≤20, unsafe >20; GI: safe ≤55, caution ≤70, unsafe >70).
   - Document sources or rationale (e.g., clinical guidelines, course materials).
   - Implement helper functions or a small evaluator that, given a `features` dict, compute which propositions hold (e.g., `is_safe_gl(gl)`, `is_unsafe_gi(gi)`).

### Phase 2: Food Safety Engine
2. **Create `FoodSafetyEngine` (or equivalent) class**
   - Constructor accepts a `NutritionKnowledgeBase` instance (from Module 1) and optional threshold overrides.
   - Implement `evaluate_food(food_name, serving_size)`:
     - Call `self.knowledge_base.get_nutrition_features(food_name, serving_size)`.
     - Handle Module 1 exceptions (`FoodNotFoundError`, `MissingDataError`, `ValueError`); either re-raise or map to a clear "unsafe" or "error" outcome and explanation.
   - Implement internal `_evaluate_rules(features)` that returns `(safety_label, explanation)`.

### Phase 3: Label Logic and Explanation
3. **Implement inference (label selection)**
   - Define priority: e.g., if any rule says "unsafe" → label = "unsafe"; else if any "caution" → "caution"; else → "safe".
   - Build explanation string from the propositions that fired (e.g., "Glycemic load 18.5 exceeds safe threshold (10); within caution range (≤20).").

### Phase 4: Integration and Edge Cases
4. **Integration with Module 1**
   - In integration tests, instantiate `NutritionKnowledgeBase` with project CSV and pass it to `FoodSafetyEngine`.
   - Verify end-to-end: food name + serving size → correct label and sensible explanation.
5. **Edge cases**
   - Food not in knowledge base → propagate or wrap `FoodNotFoundError` with clear message.
   - Missing data → same for `MissingDataError`.
   - Boundary values (exactly at threshold) → define whether boundaries are safe/caution/unsafe and test.

---

## Testing Strategy

### Unit Tests (`unit_tests/module2/`)
- **With mocked Module 1:** Provide a fake knowledge base that returns fixed feature dicts.
  - Test that for given features (e.g., GL=8, GI=50) → "safe" and explanation mentions safe GL/GI.
  - Test GL at boundary (10, 20) and just above (11, 21) → expected labels.
  - Test GI at boundaries and above.
  - Test that "unsafe" wins over "caution" and "safe" when multiple rules fire.
- **Rule logic only:** If `_evaluate_rules` is testable in isolation, test it with various feature dicts (no Module 1).

### Integration Tests (`integration_tests/module2/`)
- Use real `NutritionKnowledgeBase` with `unit_tests/module1/test_nutrition_data.csv` or `src/module1/nutrition_data.csv`.
- Call `evaluate_food` for known foods and assert expected labels and that explanations are non-empty and mention relevant metrics (e.g., GL, GI).

### Test Data
- Reuse or mirror Module 1 test CSV: include foods with low/medium/high GI and GL so that safe, caution, and unsafe are all achievable.

---

## Edge Cases & Considerations

1. **Exact threshold values**
   - Decide: is GL=10 safe or caution? Document and stick to it (e.g., safe if ≤10, caution if 10 < GL ≤ 20).

2. **Missing or invalid data**
   - If Module 1 raises `MissingDataError` or `ValueError`, Module 2 can return a conservative label (e.g., "caution" with explanation "Could not fully evaluate: missing data") or re-raise. Document choice.

3. **Multiple rules firing**
   - Always produce exactly one label (safe/caution/unsafe) and one explanation; explanation can list all relevant rule outcomes.

4. **Configurable thresholds**
   - Module 5 (Reinforcement Learning) may later adjust thresholds. Design so thresholds are injectable (e.g., constructor or setter) rather than hard-coded in many places.

5. **Explanation clarity**
   - Prefer short, consistent phrasing so Module 3 or the UI can display them without parsing (e.g., "High glycemic load (18.5 > 10). Glycemic index within safe range (52).").

---

## Data Flow Summary

```
Input: food_name, serving_size
         ↓
Module 1: get_nutrition_features(food_name, serving_size)
         ↓
Features dict (GI, GL, carbs, fiber, protein, fat, processing_level, serving_size_grams)
         ↓
Module 2: Evaluate propositional rules (thresholds on GI, GL, etc.)
         ↓
Output: { "safety_label": "safe"|"caution"|"unsafe", "explanation": "..." }
         ↓
Module 3 (later): Per-food labels + explanations → meal-level risk
```

---

## Success Criteria

Module 2 is complete when:
- [ ] `FoodSafetyEngine` (or equivalent) exists and accepts a Module 1 knowledge base.
- [ ] For any (food_name, serving_size) that Module 1 supports, the engine returns a valid safety label and a non-empty explanation.
- [ ] Propositional rules are explicit (thresholds and conditions documented or in named constants).
- [ ] Unit tests cover rule logic with mocked Module 1; at least one test per label (safe, caution, unsafe).
- [ ] Integration tests demonstrate evaluation using real Module 1 and CSV data.
- [ ] Edge cases (unknown food, missing data, boundary values) are handled and documented.
- [ ] Code is clean and documented (docstrings for public API); no external dependencies beyond Module 1 and standard library.

---

## Next Steps After Module 2

- Module 3 will take a list of foods with servings and their Module 2 outputs to compute meal-level risk (First-Order Logic).
- Keep rule thresholds easy to change for Module 5 (personalization via reinforcement learning).
- Consider exporting rule definitions (e.g., threshold names and values) so the UI or Module 3 can display "why" in a structured way if needed.

---

## Questions to Resolve

1. **Threshold source:** Use standard clinical/dietetic ranges (e.g., GI Foundation) or course-provided values? Document in plan and code.
2. **Processing level:** Should "ultra_processed" alone trigger caution/unsafe, or only in combination with high GI/GL?
3. **Explanation format:** Plain string only, or a list of "reason" objects for structured display later?
4. **File split:** Single `food_safety.py` vs separate `safety_rules.py` and `food_safety_engine.py` — choose based on team preference and rubric expectations for "propositional logic" visibility.

---

## Implementation Order

1. Define default thresholds and rule conditions (propositions) in code or config.
2. Implement `_evaluate_rules(features)` (or equivalent) and unit-test it with dummy feature dicts.
3. Implement `FoodSafetyEngine` constructor and `evaluate_food()` using Module 1.
4. Add exception handling for Module 1 errors.
5. Write unit tests with mocked knowledge base.
6. Write integration tests with real Module 1.
7. Add docstrings and document threshold rationale.
8. Run rubric/code review against Checkpoint 2 requirements.
