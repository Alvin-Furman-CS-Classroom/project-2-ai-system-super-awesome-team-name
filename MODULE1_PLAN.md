# Module 1: Nutrition Knowledge Base & Feature Extraction - Implementation Plan

## Module Overview

**Topic:** Knowledge Representation, Knowledge Bases  
**Checkpoint Due:** Checkpoint 1 (Feb 11)  
**Dependencies:** None (foundational module)

## Specification Summary

### Inputs
- Food name (string) - e.g., "white rice", "apple"
- Optional serving size (string, default: "100g") - e.g., "1 cup", "150g"

**Note:** The nutrition database file (CSV/JSON) is loaded by developers during setup, not by clients during use.

### Outputs
Structured nutrition features for a given food:
- Glycemic Index (GI) - numeric value (typically 0-100)
- Glycemic Load (GL) - per serving, calculated as (GI × carbs per serving) / 100
- Macronutrients:
  - Carbohydrates (grams per serving)
  - Fiber (grams per serving)
  - Protein (grams per serving)
  - Fat (grams per serving)
- Processing level flag (processed/whole/unprocessed)
- Serving size conversions (standardized serving sizes and conversions)

### Integration Points
- Module 2 will query this knowledge base to get food properties before applying safety rules
- Module 3 will use this data to compute meal-level totals
- Module 4 will use this data to find suitable food swaps

---

## Architecture & Design

### 1. Knowledge Representation Structure

**Core Data Structure:**
- Use a class-based approach to represent food items with structured attributes
- Consider both in-memory representation (for runtime queries) and persistent storage (for database files)

**Proposed Structure:**
```
FoodItem:
  - name: str (canonical name)
  - aliases: List[str] (alternative names, e.g., "rice" -> "white rice", "jasmine rice")
  - glycemic_index: float (0-100)
  - macronutrients: dict
    - carbohydrates: float (grams per 100g)
    - fiber: float (grams per 100g)
    - protein: float (grams per 100g)
    - fat: float (grams per 100g)
  - processing_level: str (enum: "whole", "minimally_processed", "processed", "ultra_processed")
  - serving_sizes: dict
    - standard: str (e.g., "100g", "1 cup", "1 piece")
    - conversions: dict (mapping from serving unit to grams)
```

### 2. Knowledge Base Implementation

**Approach:**
- Create a `NutritionKnowledgeBase` class that:
  - Loads data from CSV/JSON files
  - Provides lookup methods by food name
  - Handles name normalization and aliases
  - Calculates derived values (glycemic load) on demand
  - Supports both file-based initialization and programmatic data entry

**Key Methods:**
- `__init__(data_file: str = None)` - Initialize knowledge base, auto-loads from default data file if provided
- `load_from_file(filepath: str, format: str)` - Load database from CSV/JSON (for developers/setup)
- `get_food(food_name: str) -> FoodItem` - Retrieve food by name (with alias matching)
- `calculate_glycemic_load(food: FoodItem, serving_size: str) -> float` - Compute GL for a serving
- `get_nutrition_features(food_name: str, serving_size: str = "100g") -> dict` - Main client-facing method

### 3. File Structure

```
src/
├── module1/
│   ├── __init__.py
│   ├── knowledge_base.py          # NutritionKnowledgeBase class
│   ├── food_item.py                # FoodItem data class
│   └── data_loader.py              # CSV/JSON parsing utilities
└── ...

unit_tests/
├── module1/
│   ├── __init__.py
│   ├── test_knowledge_base.py
│   ├── test_food_item.py
│   └── test_data_loader.py
└── ...

data/                                    # Optional: sample data files
├── sample_nutrition_data.csv
└── sample_nutrition_data.json
```

---

## Implementation Steps

### Phase 1: Core Data Structures
1. **Create `FoodItem` class** (`src/module1/food_item.py`)
   - Define attributes with type hints
   - Implement `__repr__` and `__eq__` for testing
   - Add validation for numeric ranges (GI: 0-100, macronutrients: non-negative)

2. **Create `NutritionKnowledgeBase` class** (`src/module1/knowledge_base.py`)
   - Initialize with empty storage (dict mapping food names to FoodItem objects)
   - Implement `add_food(food: FoodItem)` method
   - Implement `get_food(name: str) -> Optional[FoodItem]` with fuzzy matching
   - Implement `calculate_glycemic_load()` helper method

### Phase 2: Data Loading
3. **Create data loader utilities** (`src/module1/data_loader.py`)
   - CSV parser: Read nutrition data from CSV files
     - Expected columns: name, glycemic_index, carbs, fiber, protein, fat, processing_level, serving_size
   - JSON parser: Read from JSON files (array of food objects)
   - Handle missing values gracefully (use defaults or raise informative errors)
   - Normalize food names (lowercase, strip whitespace)

4. **Integrate loading into KnowledgeBase**
   - Modify `__init__()` to optionally accept a data file path and auto-load on initialization
   - Add `load_from_file(filepath: str, format: str = 'auto')` method (for developers)
   - Auto-detect format from file extension
   - Populate internal storage from loaded data
   - Default behavior: try to load from `data/sample_nutrition_data.csv` if it exists

### Phase 3: Feature Extraction API
5. **Implement main output method**
   - `get_nutrition_features(food_name: str, serving_size: str = "100g") -> dict`
   - Returns structured dict with all required features
   - Handles serving size conversions
   - Calculates glycemic load for the specified serving

6. **Add helper methods**
   - `normalize_food_name(name: str) -> str` - Name normalization
   - `convert_serving_size(serving: str) -> float` - Convert to grams
   - `list_all_foods() -> List[str]` - For debugging/exploration

### Phase 4: Error Handling & Edge Cases
7. **Handle missing foods**
   - Return `None` or raise `FoodNotFoundError` with suggestions
   - Consider partial matches (e.g., "rice" matches "white rice")

8. **Handle invalid serving sizes**
   - Validate serving size format
   - Provide clear error messages

9. **Handle missing data**
   - Use defaults for optional fields
   - Document which fields are required vs optional

---

## Testing Strategy

### Unit Tests

**`test_food_item.py`:**
- Test FoodItem creation with valid data
- Test validation (reject negative values, GI > 100)
- Test equality and representation

**`test_knowledge_base.py`:**
- Test empty knowledge base initialization
- Test adding foods programmatically
- Test `get_food()` with exact matches
- Test `get_food()` with aliases/fuzzy matching
- Test `calculate_glycemic_load()` with various serving sizes
- Test `get_nutrition_features()` returns correct structure
- Test error handling for missing foods

**`test_data_loader.py`:**
- Test CSV loading with valid file
- Test JSON loading with valid file
- Test handling of missing columns/fields
- Test handling of invalid data types
- Test name normalization

### Integration Tests
- Not required for Module 1 (first module), but consider:
  - End-to-end: Load file → Query food → Get features
  - Multiple file formats (CSV and JSON)

### Test Data
- Create sample CSV and JSON files with 10-15 common foods
- Include edge cases: foods with missing optional fields, various processing levels, different serving sizes

---

## Edge Cases & Considerations

1. **Food Name Variations**
   - "white rice" vs "rice" vs "jasmine rice"
   - Case sensitivity: "Apple" vs "apple"
   - Whitespace: " white rice " vs "white rice"
   - **Solution:** Normalize names, maintain alias mapping

2. **Serving Size Conversions**
   - Different units: "1 cup", "100g", "1 piece", "1 oz"
   - Need conversion factors (cup to grams varies by food)
   - **Solution:** Store conversion factors per food, or use standard USDA conversions

3. **Missing Data**
   - Some foods may not have GI values
   - Some foods may have incomplete macronutrient data
   - **Solution:** Use defaults (e.g., GI = 50 if unknown), document assumptions

4. **Glycemic Load Calculation**
   - GL = (GI × carbs in serving) / 100
   - Requires knowing carbs per serving, not just per 100g
   - **Solution:** Calculate carbs for specified serving size first

5. **Processing Level Classification**
   - Subjective classification (whole vs processed)
   - **Solution:** Use standard categories, allow manual override

---

## Data Sources & References

**Potential Data Sources:**
- USDA FoodData Central (public API or CSV downloads)
- Glycemic Index Foundation database
- Custom curated dataset for common foods

**Data Format Example (CSV):**
```csv
name,glycemic_index,carbohydrates,fiber,protein,fat,processing_level,serving_size_100g
white rice,73,28.0,0.4,2.7,0.3,processed,100g
apple,36,14.0,2.4,0.3,0.2,whole,100g
```

**Data Format Example (JSON):**
```json
[
  {
    "name": "white rice",
    "glycemic_index": 73,
    "macronutrients": {
      "carbohydrates": 28.0,
      "fiber": 2.4,
      "protein": 2.7,
      "fat": 0.3
    },
    "processing_level": "processed",
    "serving_sizes": {
      "100g": 100,
      "1 cup": 158
    }
  }
]
```

---

## Success Criteria

Module 1 is complete when:
- [ ] Can load nutrition data from CSV files
- [ ] Can load nutrition data from JSON files
- [ ] Can query foods by name (with alias matching)
- [ ] Returns all required nutrition features (GI, GL, macronutrients, processing level, serving conversions)
- [ ] Handles edge cases (missing foods, invalid serving sizes, missing data)
- [ ] Unit tests cover core functionality with >80% coverage
- [ ] Code follows clean architecture (separation of concerns)
- [ ] Documentation (docstrings) explains public API

---

## Next Steps After Module 1

- Module 2 will depend on Module 1's `get_nutrition_features()` method
- Consider adding a simple CLI or demo script to test Module 1 in isolation
- Document the API clearly for Module 2 integration

---

## Questions to Resolve

1. **Serving size conversions:** Should we use a standard conversion library or define our own? (Recommendation: Start simple with common conversions, expand later)

2. **Data source:** Will we use a public dataset or create a curated subset? (Recommendation: Start with a small curated dataset for testing, expand later)

3. **Name matching:** How fuzzy should matching be? Exact match only, or include partial matches? (Recommendation: Start with exact + aliases, add fuzzy matching if needed)

4. **Missing GI values:** How to handle foods without known GI? (Recommendation: Use a default value like 50, flag as "estimated")

---

## Implementation Order

1. Create directory structure (`src/module1/`, `unit_tests/module1/`)
2. Implement `FoodItem` class with tests
3. Implement `NutritionKnowledgeBase` class skeleton with tests
4. Implement data loading (CSV first, then JSON)
5. Implement feature extraction methods
6. Add error handling and edge cases
7. Create sample data files
8. Write comprehensive unit tests
9. Update README with setup/usage instructions
10. Code review against rubric
