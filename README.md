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

List dependencies, setup steps, and any environment variables required to run the system.

## Running

Provide commands or scripts for running modules and demos.

## Testing

**Unit Tests** (`unit_tests/`): Mirror the structure of `src/`. Each module should have corresponding unit tests.

**Integration Tests** (`integration_tests/`): Create a new subfolder for each module beyond the first, demonstrating how modules work together.

Provide commands to run tests and describe any test data needed.

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

List libraries, APIs, datasets, and other references used by the system.
