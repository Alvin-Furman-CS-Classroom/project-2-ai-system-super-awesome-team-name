# Adaptive Diabetic Diet Advisor

## System Overview

The full system is for people with type 2 diabetes to find a more effective method for determining whether or not a meal is blood-sugar friendly. The main function is for users to input foods that they will consume, the system will then analyze it based on collected data about certain food's glycemic index and macronutrients. The system will then determine the risk of the foods, and if the risk for a blood-sugar spike is high then the system will suggest modifications to the meal. The system will also learn from user feedback, for example the system predicted a meal would not spike blood sugar when it did in reality, then the system may recalculate the weight of certain foods and their risks. Its key capabilities are safety checking, meal modification, and personalization. 

The theme is appropriate for exploring AI concepts because it uses multiple AI techniques, with many of the techniques also working together. Some of the techniques include Knowledge bases, logic, search, and reinforcement learning. The knowledge bases are used to store nutritional data that logic rules query,  logic evaluates meals and identifies risk, search algorithms use logic outputs to find optimal modifications for the meals, and reinforcement learning is used to learn from user feedback. This shows how multiple AI techniques can work together to solve a real-world problem.

## Modules

### Module 1: Nutrition Knowledge Base & Feature Extraction

**Topics:** Knowledge Representation, Knowledge Bases (part of Propositional Logic)

**Input:** Food name (string) OR food database file (CSV/JSON with nutrition data)

**Output:** Structured nutrition features for a given food: glycemic index, glycemic load (per serving), macronutrients (carbs, fiber, protein, fat), processing level flag (processed/whole), serving size conversions

**Integration:** Provides nutrition data to all other modules. Module 2 queries this knowledge base to get food properties before applying safety rules. Module 3 uses this data to compute meal-level totals. Module 4 uses this data to find suitable food swaps.

**Prerequisites:** Course content on Knowledge Representation and Knowledge Bases (typically covered early with Propositional Logic). No prior modules required - this is a foundational data/knowledge module.

---

### Module 2: Single Food Safety Rule Engine

**Topics:** Propositional Logic, Knowledge Bases, Inference

**Input:** Food name (string) + serving size (e.g., "1 cup" or grams)

**Output:** Safety label (safe/caution/unsafe) + explanation string indicating which rule fired (e.g., "High glycemic load (>20) for serving size")

**Integration:** Used by Module 3 to evaluate each food in a meal before computing overall meal risk

**Prerequisites:** Course content on Propositional Logic, Knowledge Bases, and Inference Methods. Module 1 (nutrition knowledge base) must be completed first to provide food nutrition data.

---

### Module 3: Meal-Level Risk Analyzer

**Topics:** First-Order Logic (Quantifiers, Unification, Inference)

**Input:** List of food names with serving sizes (e.g., [("rice", "1 cup"), ("chicken", "4 oz"), ("broccoli", "0.5 cup")]) + Module 2 outputs for each food

**Output:** Overall meal risk category (low/medium/high spike risk) + risk score (numeric, 0-100) + contributing factors (e.g., "Total carbs exceed threshold", "Low fiber content")

**Integration:** Feeds into Module 4 (search/modification) to determine if meal needs changes and what constraints to satisfy

**Prerequisites:** Course content on First-Order Logic. Module 1 and Module 2 must be completed first.

---

### Module 4: Meal Modification & Alternative Generator

**Topics:** Search (Uniform Cost Search, A\*)

**Input:** Original meal (list of foods with portions) + target constraints (max allowed risk level, optional: calorie/carb limits) + user preferences (e.g., foods to avoid)

**Output:** One or more modified meal suggestions, each as a list of foods with adjusted portions/swaps/additions (e.g., [("rice", "0.75 cup"), ("chicken", "4 oz"), ("broccoli", "1 cup"), ("black beans", "0.25 cup")]) + explanation of changes made

**Integration:** Uses Module 3's risk score to determine if modification is needed; uses Module 2's rules to evaluate candidate modifications; suggestions displayed to user

**Prerequisites:** Course content on Search algorithms (Uniform Cost, A\*). Modules 2 and 3 must be completed first.

---

### Module 5: User Feedback & Threshold Adaptation

**Topics:** Reinforcement Learning (Policy Learning, Q-Learning)

**Input:** Historical meal records (meal + Module 3's predicted risk) + user-reported outcomes (e.g., "spike occurred" / "no spike" / "mild spike") + current user thresholds

**Output:** Updated user-specific thresholds (e.g., personalized glycemic load threshold, adjusted carb limits) stored as configuration parameters

**Integration:** Updated thresholds modify rule parameters in Modules 2 and 3, making future predictions more personalized to the user's actual responses. Uses reinforcement learning where correct predictions are rewarded and incorrect predictions are penalized, allowing the system to learn optimal threshold values through trial and feedback.

**Prerequisites:** Course content on Reinforcement Learning (Policy, MDP, Value Functions, Q-Learning). Modules 2, 3, and 4 must be completed first to generate predictions for comparison.

---

## Feasibility Study

_A timeline showing that each module's prerequisites align with the course schedule. Verify that you are not planning to implement content before it is taught._

| Module | Required Topic(s)                                   |Topic Covered By| Checkpoint Due       |
| ------ | ----------------------------------------------------| ---------------| ---------------------|
| 1      | Knowledge Representation, Knowledge Bases           | Week 2         | Checkpoint 1 (Feb 11)|
| 2      | Propositional Logic, Knowledge Bases, Inference     | Week 3         | Checkpoint 2 (Feb 26)|
| 3      | First-Order Logic                                   | Week 4         | Checkpoint 3 (Mar 19)|
| 4      | Search (Uniform Cost, A\*)                          | Week 5         | Checkpoint 4 (Apr 2) |
| 5      | Reinforcement Learning (Policy Learning, Q-Learning)| Week 8-9       | Checkpoint 5 (Apr 16)|


## Coverage Rationale

_Brief justification for your choice of topics. Why do these topics fit your theme? What trade-offs did you consider?_

Knowledge Bases are needed to store and retrieve nutritional data on foods. Propositional logic is needed to identify risk and apply safety rules for individual foods. First-Order Logic is needed for meal-level reasoning, allowing the system to evaluate combinations of food.
Search algorithms are needed to find best alternatives for when meals are high-risk. Reinforcement Learning is needed to personalize user experience with the system by adapting thresholds based on feedback. 

These topics work together as knowledge bases provide data for logic rules, logic evaluates safety, search uses logic outputs to find modifications, and reinforcement learning adapts based on outcomes. Originally Module 3 was also going to use propositional logic, however, I wanted to diversify my topics. Therefore, I chose to use First-Order Logic for Module 3. 