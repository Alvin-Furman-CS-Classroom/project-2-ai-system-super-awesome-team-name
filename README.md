# GlycemicGuard: Adaptive Diabetic Diet Advisor

## Overview

Provide a concise system overview (200-300 words). Explain the unifying theme and how the modules combine into a coherent AI system.

## Team

- Jia Lin
- Della Avent

## Proposal

This system helps people with type 2 diabetes determine whether meals are blood-sugar friendly. Users input foods they plan to consume, and the system analyzes them using glycemic index and macronutrient data to assess blood-sugar spike risk. For high-risk meals, the system suggests modifications. It learns from user feedback to personalize predictions over time.

The system integrates five AI techniques: (1) Knowledge Bases store nutritional data, (2) Propositional Logic evaluates individual food safety, (3) First-Order Logic analyzes meal-level risk, (4) Search algorithms find optimal meal modifications, and (5) Reinforcement Learning adapts thresholds based on user outcomes. These modules work together—knowledge bases feed logic rules, logic evaluates safety, search uses logic outputs to find alternatives, and reinforcement learning personalizes the system based on feedback.

See `PROPOSAL.md` for full details. 



## Module Plan

Your system must include 5-6 modules. Fill in the table below as you plan each module.

| Module | Topic(s) | Inputs | Outputs | Depends On | Checkpoint |
| ------ | -------- | ------ | ------- | ---------- | ---------- |
| 1 | Knowledge Representation, Knowledge Bases | Food name (string) + optional serving size | Nutrition features dict: GI, glycemic load, macronutrients, processing level, serving conversions | None | Checkpoint 1 (Feb 11) |
| 2 | Propositional Logic, Knowledge Bases, Inference | Food name + serving size | Safety label (safe/caution/unsafe) + rule explanation | Module 1 | Checkpoint 2 (Feb 26) |
| 3 | First-Order Logic | List of foods with servings + Module 2 outputs | Meal risk category + risk score (0-100) + contributing factors | Modules 1, 2 | Checkpoint 3 (Mar 19) |
| 4 | Search (Uniform Cost, A*) | Original meal + constraints + user preferences | Modified meal suggestions with portion adjustments/swaps + change explanations | Modules 2, 3 | Checkpoint 4 (Apr 2) |
| 5 | Reinforcement Learning (Policy, Q-Learning) | Historical meals + predicted risks + user outcomes + current thresholds | Updated personalized thresholds (glycemic load, carb limits) | Modules 2, 3, 4 | Checkpoint 5 (Apr 16) |
| 6 | Web Interface / User Interface | User interactions (food inputs, serving sizes, meal building, feedback) | Visual display of nutrition info, risk assessments, meal suggestions, and personalized recommendations | Modules 1, 2, 3, 4, 5 | Optional / Future |

## Module 2: Single Food Safety Rule Engine

### Inputs

- **Food name**: A string identifier for the food (case-insensitive, whitespace-tolerant), e.g. `"cabbage cruciferous boiled"` or `"Arborio Rice   Boiled"`.
- **Serving size**: A string describing the amount, parsed by Module 1. Supported formats include:
  - `"100g"`, `"200 g"` (grams, with or without space before `g`)
  - `"1 serving"`, `"2.5 servings"`, `"0.5 serving"` (multiples of the food's base serving size)
- **Example call**: `engine.evaluate_food("cabbage cruciferous boiled", "100g")`

### Outputs

- **Safety label**: One of `"safe"`, `"caution"`, or `"unsafe"`, indicating blood-sugar spike risk for the given serving.
- **Explanation**: A human-readable string explaining which rules fired, for example:
  - `"Glycemic load 8.0 within safe range (≤10.0). Glycemic index 50.0 within safe range (≤55.0)."`
- **Next-module feed**: Module 3 (Meal-Level Risk Analyzer) will:
  - call Module 2 for each food in a meal to get `safety_label` and `explanation`,
  - use the per-food labels and Module 1 features as inputs when computing the overall meal risk score and risk category.

### AI Concepts and Design Rationale

- **Knowledge Bases**: Module 2 relies on Module 1's `NutritionKnowledgeBase` as its knowledge source for GI, GL, and macronutrients. It does not load or store raw nutrition data itself.
- **Propositional Logic and Inference**:
  - Encodes safety rules as propositions over numeric thresholds for glycemic index and glycemic load.
  - Applies a clear priority ordering: if any rule marks a food as unsafe, that wins over caution, which in turn wins over safe.
  - Produces an explanation string that directly reflects which threshold checks fired, supporting explainable, rule-based inference.
- **Why this fits the problem**:
  - Threshold-based rules over GI/GL align with clinical guidance and are easy to tune.
  - The logic is transparent for users and clinicians (no black-box model) and easy to explain in an in-person demo.
  - Separating the rules (`safety_rules.py`) from the engine (`food_safety_engine.py`) keeps Module 2 small, testable, and ready for reuse by both the CLI and the future web interface.

## Module 3: Meal-Level Risk Analyzer

### Inputs

- **Meal**: A non-empty list of foods with servings, each item shaped as:
  - `food_name` (string, same resolution as Module 1 / Module 2)
  - `serving_size` (string, same formats as Module 1, e.g. `"100g"`, `"1 serving"`)
- **Underlying data**: Module 3 uses **Module 2** for per-food `safety_label` / `explanation` and **Module 1** for summed glycemic load, fiber, and protein when **effective GL** mode is on.

### Outputs

- **Meal risk category**: One of `"low"`, `"medium"`, or `"high"` (blood-sugar spike risk for the whole meal).
- **Risk score**: A number from **0–100** (higher = higher spike risk).
- **Contributing factors**: Short, plain-language strings explaining the result (totals, fiber/protein balance when applicable, and per-food label summary).

### How to run (CLI)

1. Start the app: `python -m src.cli` (or `py -m src.cli` on Windows).
2. Choose **“Check meal risk”** (menu option **2**).
3. **Enter the whole meal on one line** — separate foods with commas and/or `and`, e.g. `spaghetti, meatballs, tomato sauce` or `spaghetti and meatballs`. The CLI splits that into ingredients and helps you pick the closest match in the database for each. Say **yes** to “same serving for all” (e.g. `100g` each) to set one serving for every item, or **no** to enter a serving per food.
4. The meal summary appears first, with optional detail for each labeled food.

**Note:** The CSV lists ingredients (e.g. pasta types, ground beef), not full restaurant dish names—listing components separately matches how the knowledge base works.

### AI concepts and design rationale

- **First-order style reasoning over a meal:** The analyzer aggregates over *all* foods (e.g., counts and existence of caution/unsafe labels, plus meal-level totals), not only a single item.
- **Meal-level glycemic load:** Summed GL with optional **fiber** and **protein** step bands to compute an *effective* GL so the meal outcome reflects the full plate, not only the worst single food.
- **Explainability:** Outputs connect Module 2 labels and numeric meal totals to a single meal decision and user-facing reasons.

---

## Module 4: Meal Modification & Alternative Generator

### Inputs
- **Original meal**: a non-empty list of meal items, each shaped as:
  - `{"food_name": str, "serving_size": str}`
- **Original meal risk category** (from Module 3): `low` / `medium` / `high`.
- **Search constraints** (defaults in `MealSuggestionPlanner`; CLI uses the same):
  - edit budget: up to `max_edits` (default **8**)
  - expansion cap: `max_expansions` (default **2000**) to bound runtime
  - action set: **portion reduction** (75% / 50% / 25% of current grams on eligible original items), **swap**, and **add**
  - portion reduction applies only to selected coarse categories (e.g. grains, fruit, legumes, sweets, beverages) with nonzero reference glycemic load; swaps never target foods added during search
  - swap validity: replacements must share the same **inferred** coarse food category as the original item (`infer_food_category`: **whole-word** tokens and multi-word phrases, not raw substrings—so e.g. `oat` does not match inside `goat`; small overrides include **vinegar**, **tempeh/tofu**, **rice milk** as beverage). For **grains/starches**, swaps also require the same **subfamily** (e.g. rice→rice, bread→bread, pasta→pasta—not rice→pasta salad).
  - **Uniqueness:** two *different* original foods in the meal cannot both be swapped to the *same* replacement in one suggestion (two identical lines, e.g. two rices, may still map to the same swap)
  - swap candidates: taken from the knowledge base only, ranked by lower glycemic index and load (standard portion)—**not** by word embeddings

### Outputs
- **Suggestion bundles** (3–5 depending on original category):
  - `medium` (or `caution`): up to **3** suggestions
  - `high`: up to **5** suggestions
  - `low`: no suggestions needed
- Each suggestion includes `edited_meal` (full item list for programs/tests) plus human-readable **actions**, e.g.:
  - `Reduce portion of white rice steamed: 200g -> 100g`
  - `Swap white rice steamed -> brown rice boiled`
  - `Add broccoli cruciferous steamed (100g)`

### Dependencies
- **Module 3**: evaluates candidate meals and provides the meal risk category used by Module 4’s goal test.
- **Module 2**: indirectly via Module 3 for per-food safety labeling.
- **Module 1**: used to list foods, generate/filter plausible “add” candidates, and rank same-category **swap** candidates using GI/GL from the database.

**Note:** Optional **word embeddings** (`FoodMatcher` / sentence-transformers) are only for helping users match **typed food names** to KB rows during meal entry—not for Module 4 swap generation.

### CLI (meal risk menu)
When you choose **“2. Check meal risk”**, after Module 3’s summary the CLI shows **optional tweaks**: a **top pick** (resulting category, score, bullet **steps** only) and **more ideas** the same way. It does not re-print the full revised meal list (that remains in the structured `Suggestion` objects for code/tests). Swaps stay in the same food group; no free-text replacement entry.

### AI concepts and design rationale
- **Search (Uniform Cost Search, A\*)**:
  - Module 4 explores a discrete state space where each action is a small meal edit (portion / swap / add).
  - The goal test checks whether the candidate meal is at least **one risk tier down** relative to Module 3’s category.
  - The frontier uses lexicographic priority (edit count, goal distance for A\*, risk score, and **effective glycemic load** when scores tie at the high-risk cap) so search favors materially lower sugar impact.
  - Returned suggestions are ranked to prefer fewer edits and lower resulting risk scores.
- **Constraint satisfaction**:
  - Swaps are constrained to **same-category replacements** to keep suggestions realistic; category labels come from token/phrase rules on KB food names. **Grains/starches** additionally require the same **subfamily** (rice vs bread vs pasta vs potato, etc.).
  - The search rejects meals where **distinct** original items would both become the same swapped-in food.
  - Swaps only modify foods that existed in the original meal (added items are not later swapped away).
- **Diversity filtering**:
  - Prevents redundant suggestions that only differ by preparation-style tokens (e.g., “boiled” vs “steamed”).

### Testing
- Unit tests: `unit_tests/module4/test_meal_suggestion_planner.py`
- Integration test: `integration_tests/module4/test_module4_with_module3.py`

## Repository Layout

```
your-repo/
├── src/                              # main system source code
│   ├── module1/                      # Module 1: Nutrition Knowledge Base
│   │   └── MODULE1_PLAN.md           # Detailed implementation plan for Module 1
│   ├── module2/                      # Module 2: Single Food Safety Rules
│   ├── module3/                      # Module 3: Meal-Level Risk Analyzer
│   ├── module4/                       # Module 4: Meal Modification & Search
│   └── module5/                      # Module 5: Reinforcement Learning
├── unit_tests/                       # unit tests (parallel structure to src/)
│   ├── module1/                      # Unit tests for Module 1
│   ├── module2/                      # Unit tests for Module 2
│   ├── module3/                      # Unit tests for Module 3
│   ├── module4/                      # Unit tests for Module 4
│   └── module5/                      # Unit tests for Module 5
├── integration_tests/                # integration tests (new folder for each module)
│   ├── module2/                      # Integration tests for Module 2 (uses Module 1)
│   ├── module3/                      # Integration tests for Module 3 (uses Modules 1, 2)
│   ├── module4/                      # Integration tests for Module 4 (uses Modules 2, 3)
│   └── module5/                      # Integration tests for Module 5 (uses Modules 2, 3, 4)
├── data/                             # Sample nutrition data files (CSV/JSON)
│   ├── sample_nutrition_data.csv     # Sample nutrition data in CSV format
│   └── sample_nutrition_data.json    # Sample nutrition data in JSON format
├── .claude/skills/code-review/SKILL.md  # rubric-based agent review
├── AGENTS.md                         # instructions for your LLM agent
├── PROPOSAL.md                       # Full project proposal
└── README.md                         # system overview and checkpoints
```

## Setup

- **Python 3** (3.8+).
- **Optional for food name matching:** The CLI uses **word embeddings** via the [sentence-transformers](https://www.sbert.net/) library to suggest similar foods when the user’s input does not exactly match a food in the knowledge base. Install with:
  ```bash
  pip install sentence-transformers
  ```
  If not installed, the CLI falls back to simple substring matching. No other external APIs are required for core modules (1–2).

## Running

- **Terminal UI:** From the project root, run:
  ```bash
  python3 -m src.cli
  ```
  The CLI loads the nutrition knowledge base and the food safety engine; when you enter a food name, it uses **sentence-transformers** to compute **word embeddings** and find semantically similar foods if there is no exact match.

## Testing

**Unit Tests** (`unit_tests/`): Mirror the structure of `src/`. Each module should have corresponding unit tests.

**Integration Tests** (`integration_tests/`): Create a new subfolder for each module beyond the first, demonstrating how modules work together.

- **Module 2 tests**:
  - All Module 2 tests (unit + end-to-end with Module 1) live in `unit_tests/module2`:
    - `python3 -m unittest discover -s unit_tests/module2 -p "test_*.py" -v`
  - These use the real nutrition CSV in `src/module1/nutrition_data.csv` plus hand-crafted feature dicts for rule-level tests.

## Checkpoint Log

| Checkpoint | Date | Modules Included | Status | Evidence |
| ---------- | ---- | ---------------- | ------ | -------- |
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |

## Required Workflow (Agent-Guided)

Before each module:

1. Write a short module spec in this README (inputs, outputs, dependencies, tests).
2. Ask the agent to propose a plan in "Plan" mode.
3. Review and edit the plan. You must understand and approve the approach.
4. Implement the module in `src/`.
5. Unit test the module, placing tests in `unit_tests/` (parallel structure to `src/`).
6. For modules beyond the first, add integration tests in `integration_tests/` (new subfolder per module).
7. Run a rubric review using the code-review skill at `.claude/skills/code-review/SKILL.md`.

Keep `AGENTS.md` updated with your module plan, constraints, and links to APIs/data sources.

## References

- **Word embeddings / similar-food matching:** We use the [sentence-transformers](https://www.sbert.net/) library (e.g. model `all-MiniLM-L6-v2`) to compute sentence embeddings for food names and to find nearest-neighbor matches. This provides semantic similarity rather than plain substring matching. See `src/food_matcher.py`.
- **Nutrition data:** CSV-backed knowledge base in `src/module1/` (see Module 1 plan and data files).
