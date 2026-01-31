# Module 1: Nutrition Knowledge Base & Feature Extraction - Implementation Plan

## Module Overview

**Topic:** Knowledge Representation, Knowledge Bases  
**Checkpoint Due:** Checkpoint 1 (Feb 11)  
**Dependencies:** None (foundational module)

## Specification Summary

### Inputs
- Food name (string) - e.g., "white rice", "apple"
- Optional serving size (string, default: "100g") - e.g., "1 cup", "150g"

**Note:** The nutrition database CSV file is created by developers and loaded automatically when the knowledge base is initialized. Clients only query by food name.

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
- Module 4 will use this data to find suitable food swaps (may need to iterate/search through all foods)

---

## Architecture & Design

### 1. Knowledge Representation

**CSV File as Knowledge Base:**
- The CSV file itself represents the knowledge (structured nutrition data)
- Located in `src/module1/nutrition_data.csv` or `data/nutrition_data.csv`
- Columns: `name`, `glycemic_index`, `carbohydrates`, `fiber`, `protein`, `fat`, `processing_level`, `serving_size_grams` (for standard serving)

**In-Memory Knowledge Base (Dict):**
- Load CSV once at initialization into a dictionary
- Structure: `{food_name: {nutrition_data_dict}}`
- Fast O(1) lookups by food name

**Example Dict Structure:**
```python
{
    "white rice": {
        "glycemic_index": 73.0,
        "carbohydrates": 28.0,  # per 100g
        "fiber": 0.4,
        "protein": 2.7,
        "fat": 0.3,
        "processing_level": "processed",
        "serving_size_grams": 158  # for "1 cup"
    },
    "apple": {
        "glycemic_index": 36.0,
        "carbohydrates": 14.0,
        "fiber": 2.4,
        "protein": 0.3,
        "fat": 0.2,
        "processing_level": "whole",
        "serving_size_grams": 182  # for "1 medium apple"
    }
}
```

### 2. Knowledge Base Implementation

**Approach:**
- Create a simple `NutritionKnowledgeBase` class that:
  - Loads CSV file into a dict on initialization
  - Provides lookup method by food name
  - Calculates derived values (glycemic load) on demand
  - Handles name normalization (case-insensitive, strip whitespace)

**Key Methods:**
- `__init__(csv_file: str = None)` - Initialize and load CSV into dict (default: `nutrition_data.csv`)
- `get_nutrition_features(food_name: str, serving_size: str = "100g") -> dict` - Main client-facing method
- `list_all_foods() -> List[str]` - Return list of all food names (for Module 4 search functionality)
- `get_all_foods() -> dict` - Return copy of all food data (for Module 4 to search for swaps)
- `_load_csv(filepath: str) -> dict` - Private method to load CSV into dict
- `_normalize_name(name: str) -> str` - Private helper for name normalization
- `_calculate_glycemic_load(gi: float, carbs_per_serving: float) -> float` - Private helper for GL calculation
- `_convert_serving_size(serving_str: str, base_grams: float) -> float` - Private helper for serving conversions

**Note for Module 4 Integration:**
The dict-based approach makes it easy for Module 4 to search for food swaps. Module 4 can:
- Use `list_all_foods()` to get all available foods
- Use `get_all_foods()` to iterate through foods and compare nutrition profiles
- Use `get_nutrition_features()` to query specific foods
This provides efficient search capabilities while maintaining the simple dict structure.

### 3. File Structure

```
src/
├── module1/
│   ├── __init__.py
│   ├── knowledge_base.py          # NutritionKnowledgeBase class
│   └── nutrition_data.csv         # Knowledge base CSV file
└── ...

unit_tests/
├── module1/
│   ├── __init__.py
│   ├── test_knowledge_base.py
│   └── test_nutrition_data.csv    # Test data file
└── ...
```

---

## Implementation Steps

### Phase 1: Create CSV Knowledge Base
1. **Create `nutrition_data.csv`** (`src/module1/nutrition_data.csv`)
   - Define CSV structure with columns: `name`, `glycemic_index`, `carbohydrates`, `fiber`, `protein`, `fat`, `processing_level`, `serving_size_grams`
   - Add 10-15 common foods for testing
   - Include example serving sizes (e.g., "1 cup" = 158g for rice)

### Phase 2: Core Knowledge Base Class
2. **Create `NutritionKnowledgeBase` class** (`src/module1/knowledge_base.py`)
   - Implement `__init__(csv_file: str = None)` that loads CSV into dict
   - Implement `_load_csv(filepath: str) -> dict` private method
     - Use Python's `csv` module (no external dependencies)
     - Read CSV and convert to dict structure
     - Normalize food names (lowercase, strip whitespace) as keys
     - Convert numeric columns to floats
   - Store dict as instance variable `self._data`

### Phase 3: Feature Extraction API
3. **Implement main query method**
   - `get_nutrition_features(food_name: str, serving_size: str = "100g") -> dict`
   - Look up food in dict (normalize name first)
   - Handle serving size conversion
   - Calculate glycemic load for specified serving
   - Return structured dict with all required features

4. **Implement helper methods**
   - `_normalize_name(name: str) -> str` - Lowercase and strip whitespace
   - `_calculate_glycemic_load(gi: float, carbs_per_serving: float) -> float` - GL = (GI × carbs) / 100
   - `_convert_serving_size(serving_str: str, base_grams: float) -> float` - Parse serving size string and convert to grams
     - Handle formats like "100g", "1 cup", "150g", etc.
     - Use serving_size_grams from CSV as base
   - `list_all_foods() -> List[str]` - Return list of all food names (for Module 4)
   - `get_all_foods() -> dict` - Return copy of all food data (for Module 4 to search for swaps)

### Phase 4: Error Handling & Edge Cases
5. **Handle missing foods**
   - Raise `FoodNotFoundError` with helpful message
   - Optionally suggest similar food names (if time permits)

6. **Handle invalid serving sizes**
   - Validate serving size format
   - Provide clear error messages
   - Default to "100g" if serving size not recognized

7. **Handle missing data**
   - Validate required fields when loading CSV
   - Use defaults for optional fields (e.g., GI = 50 if missing)
   - Document assumptions

---

## Testing Strategy

### Unit Tests

**`test_knowledge_base.py`:**
- Test initialization with default CSV file
- Test initialization with custom CSV file path
- Test `get_nutrition_features()` with exact food name matches
- Test `get_nutrition_features()` with case variations ("White Rice" vs "white rice")
- Test `get_nutrition_features()` with whitespace variations (" white rice " vs "white rice")
- Test serving size conversions (100g, 1 cup, custom sizes)
- Test glycemic load calculation correctness
- Test error handling for missing foods
- Test error handling for invalid serving sizes
- Test that all required output fields are present
- Test data types of returned values (floats, strings, dicts)
- Test `list_all_foods()` returns correct list of food names
- Test `get_all_foods()` returns copy of all food data (for Module 4)

### Test Data
- Create `test_nutrition_data.csv` in `unit_tests/module1/` with 5-10 test foods
- Include edge cases:
  - Foods with different processing levels
  - Various serving sizes
  - Foods with missing optional data (if applicable)

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

**CSV Format:**
```csv
name,glycemic_index,carbohydrates,fiber,protein,fat,processing_level,serving_size_grams
white rice,73,28.0,0.4,2.7,0.3,processed,158
apple,36,14.0,2.4,0.3,0.2,whole,182
```

**Notes:**
- All macronutrient values are per 100g
- `serving_size_grams` represents a standard serving (e.g., 1 cup of rice = 158g, 1 medium apple = 182g)
- `processing_level` values: "whole", "minimally_processed", "processed", "ultra_processed"

---

## Success Criteria

Module 1 is complete when:
- [ ] CSV file created with nutrition data (10-15 foods minimum)
- [ ] Can load CSV into dict on initialization
- [ ] Can query foods by name (case-insensitive, whitespace-tolerant)
- [ ] Returns all required nutrition features (GI, GL, macronutrients, processing level, serving conversions)
- [ ] Correctly calculates glycemic load for specified serving sizes
- [ ] Handles edge cases (missing foods, invalid serving sizes, missing data)
- [ ] Unit tests cover core functionality with >80% coverage
- [ ] Code is clean and well-documented (docstrings)
- [ ] No external dependencies beyond Python standard library

---

## Next Steps After Module 1

- Module 2 will depend on Module 1's `get_nutrition_features()` method
- Module 4 will use `list_all_foods()` and `get_all_foods()` to search for food swaps
- Consider adding a simple CLI or demo script to test Module 1 in isolation
- Document the API clearly for Module 2 and Module 4 integration

---

## Questions to Resolve

1. **Serving size conversions:** How to handle different serving size formats? (Recommendation: Start with simple parsing - "100g", "1 cup", numeric grams. Can expand later)

2. **Data source:** Will we use a public dataset or create a curated subset? (Recommendation: Start with a small curated dataset of 10-15 common foods for testing, expand later)

3. **Name matching:** How strict should matching be? (Recommendation: Case-insensitive, whitespace-tolerant exact match. Can add fuzzy matching later if needed)

4. **Missing GI values:** How to handle foods without known GI? (Recommendation: Use a default value like 50, or require GI in CSV - document decision)

---

## Implementation Order

1. Create `nutrition_data.csv` with sample foods (10-15 items)
2. Implement `NutritionKnowledgeBase` class skeleton
3. Implement `_load_csv()` method to read CSV into dict
4. Implement `get_nutrition_features()` method
5. Implement helper methods (`_normalize_name`, `_calculate_glycemic_load`, `_convert_serving_size`)
6. Add error handling (missing foods, invalid serving sizes)
7. Write unit tests with test CSV file
8. Test edge cases and fix bugs
9. Add docstrings and documentation
10. Code review against rubric
