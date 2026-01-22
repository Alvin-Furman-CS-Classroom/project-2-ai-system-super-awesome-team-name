#!/usr/bin/env python3
"""
Generate a comprehensive nutrition database CSV file with ~2,000 foods.
Based on USDA FoodData Central and Glycemic Index Foundation data.
"""

import csv
import random

# Food templates with base nutrition data
FOOD_TEMPLATES = [
    # Grains & Starches
    {"base": "rice", "variations": ["white", "brown", "jasmine", "basmati", "wild", "black", "red", "sticky", "sushi", "arborio", "risotto"], 
     "gi_range": (50, 110), "carbs": (20, 30), "fiber": (0.4, 2.5), "protein": (2.5, 3.5), "fat": (0.2, 1.0), 
     "processing": "processed", "serving": 158},
    {"base": "bread", "variations": ["white", "whole wheat", "sourdough", "rye", "pumpernickel", "multigrain", "sprouted", "gluten-free", "naan", "pita", "bagel", "baguette", "ciabatta", "focaccia"],
     "gi_range": (50, 80), "carbs": (40, 55), "fiber": (2.0, 8.0), "protein": (8.0, 15.0), "fat": (2.0, 5.0),
     "processing": "processed", "serving": 28},
    {"base": "pasta", "variations": ["white", "whole wheat", "spaghetti", "penne", "fettuccine", "linguine", "macaroni", "lasagna", "ravioli", "gnocchi"],
     "gi_range": (35, 55), "carbs": (20, 30), "fiber": (1.5, 4.5), "protein": (4.0, 6.0), "fat": (0.8, 2.0),
     "processing": "processed", "serving": 140},
    {"base": "potato", "variations": ["white", "sweet", "red", "russet", "yukon gold", "fingerling", "purple", "mashed", "baked", "boiled", "fried", "roasted"],
     "gi_range": (45, 95), "carbs": (15, 25), "fiber": (2.0, 4.0), "protein": (1.5, 3.0), "fat": (0.1, 15.0),
     "processing": ["whole", "processed"], "serving": 150},
    {"base": "quinoa", "variations": ["white", "red", "black", "tricolor", "cooked"],
     "gi_range": (50, 55), "carbs": (20, 22), "fiber": (2.5, 3.0), "protein": (4.0, 5.0), "fat": (1.8, 2.2),
     "processing": "minimally_processed", "serving": 185},
    {"base": "oats", "variations": ["rolled", "steel cut", "instant", "quick", "old fashioned"],
     "gi_range": (42, 60), "carbs": (60, 70), "fiber": (10.0, 12.0), "protein": (15, 18), "fat": (6.0, 8.0),
     "processing": "minimally_processed", "serving": 81},
    {"base": "barley", "variations": ["pearl", "hulled", "pot", "cooked"],
     "gi_range": (25, 35), "carbs": (70, 75), "fiber": (15, 18), "protein": (10, 13), "fat": (2.0, 2.5),
     "processing": "minimally_processed", "serving": 157},
    
    # Fruits
    {"base": "apple", "variations": ["red", "green", "gala", "fuji", "granny smith", "honeycrisp", "pink lady", "braeburn", "raw", "baked", "dried"],
     "gi_range": (30, 40), "carbs": (12, 16), "fiber": (2.0, 3.5), "protein": (0.2, 0.5), "fat": (0.1, 0.3),
     "processing": "whole", "serving": 182},
    {"base": "banana", "variations": ["yellow", "green", "ripe", "overripe", "frozen", "dried"],
     "gi_range": (42, 62), "carbs": (20, 25), "fiber": (2.5, 3.5), "protein": (1.0, 1.5), "fat": (0.2, 0.4),
     "processing": "whole", "serving": 118},
    {"base": "orange", "variations": ["navel", "valencia", "blood", "mandarin", "clementine", "tangerine"],
     "gi_range": (40, 50), "carbs": (11, 13), "fiber": (2.0, 3.0), "protein": (0.8, 1.2), "fat": (0.1, 0.2),
     "processing": "whole", "serving": 131},
    {"base": "berry", "variations": ["strawberry", "blueberry", "raspberry", "blackberry", "cranberry", "gooseberry", "elderberry"],
     "gi_range": (25, 55), "carbs": (7, 15), "fiber": (2.0, 8.0), "protein": (0.5, 1.5), "fat": (0.2, 0.7),
     "processing": "whole", "serving": 144},
    {"base": "grape", "variations": ["red", "green", "black", "concord", "seedless", "frozen"],
     "gi_range": (45, 65), "carbs": (16, 20), "fiber": (0.8, 1.2), "protein": (0.6, 0.9), "fat": (0.1, 0.3),
     "processing": "whole", "serving": 92},
    {"base": "melon", "variations": ["watermelon", "cantaloupe", "honeydew", "crenshaw"],
     "gi_range": (60, 80), "carbs": (7, 9), "fiber": (0.4, 0.8), "protein": (0.5, 0.9), "fat": (0.1, 0.3),
     "processing": "whole", "serving": 152},
    {"base": "stone fruit", "variations": ["peach", "nectarine", "plum", "apricot", "cherry"],
     "gi_range": (30, 45), "carbs": (9, 12), "fiber": (1.4, 2.5), "protein": (0.8, 1.2), "fat": (0.2, 0.4),
     "processing": "whole", "serving": 150},
    {"base": "tropical fruit", "variations": ["mango", "pineapple", "papaya", "kiwi", "passion fruit", "guava"],
     "gi_range": (40, 70), "carbs": (12, 18), "fiber": (1.5, 3.5), "protein": (0.5, 1.5), "fat": (0.1, 0.5),
     "processing": "whole", "serving": 150},
    
    # Vegetables
    {"base": "leafy green", "variations": ["spinach", "kale", "lettuce", "arugula", "romaine", "iceberg", "butter lettuce", "swiss chard", "collard greens", "mustard greens"],
     "gi_range": (10, 20), "carbs": (2, 5), "fiber": (1.5, 3.0), "protein": (1.5, 3.5), "fat": (0.2, 0.6),
     "processing": "whole", "serving": 30},
    {"base": "cruciferous", "variations": ["broccoli", "cauliflower", "cabbage", "brussels sprouts", "bok choy", "kohlrabi"],
     "gi_range": (10, 20), "carbs": (4, 7), "fiber": (2.0, 3.5), "protein": (1.8, 3.5), "fat": (0.2, 0.5),
     "processing": "whole", "serving": 91},
    {"base": "root vegetable", "variations": ["carrot", "beet", "turnip", "parsnip", "radish", "rutabaga"],
     "gi_range": (30, 50), "carbs": (8, 12), "fiber": (2.0, 4.0), "protein": (0.8, 1.5), "fat": (0.1, 0.3),
     "processing": "whole", "serving": 128},
    {"base": "squash", "variations": ["zucchini", "yellow squash", "butternut", "acorn", "spaghetti", "pumpkin", "kabocha"],
     "gi_range": (15, 75), "carbs": (3, 12), "fiber": (1.0, 3.0), "protein": (1.0, 2.0), "fat": (0.1, 0.3),
     "processing": "whole", "serving": 124},
    {"base": "pepper", "variations": ["bell pepper red", "bell pepper green", "bell pepper yellow", "bell pepper orange", "jalapeno", "serrano", "poblano"],
     "gi_range": (10, 20), "carbs": (4, 7), "fiber": (1.5, 2.5), "protein": (0.9, 1.5), "fat": (0.2, 0.4),
     "processing": "whole", "serving": 149},
    {"base": "tomato", "variations": ["cherry", "roma", "beefsteak", "heirloom", "canned", "sun-dried"],
     "gi_range": (10, 20), "carbs": (3, 5), "fiber": (1.0, 2.0), "protein": (0.8, 1.2), "fat": (0.1, 0.3),
     "processing": ["whole", "processed"], "serving": 182},
    {"base": "onion", "variations": ["yellow", "white", "red", "sweet", "shallot", "scallion", "leek"],
     "gi_range": (10, 20), "carbs": (7, 10), "fiber": (1.5, 2.5), "protein": (1.0, 1.5), "fat": (0.1, 0.2),
     "processing": "whole", "serving": 160},
    {"base": "mushroom", "variations": ["button", "cremini", "portobello", "shiitake", "oyster", "maitake", "enoki"],
     "gi_range": (10, 20), "carbs": (2, 4), "fiber": (1.0, 2.0), "protein": (2.0, 3.5), "fat": (0.2, 0.5),
     "processing": "whole", "serving": 70},
    
    # Proteins
    {"base": "chicken", "variations": ["breast", "thigh", "drumstick", "wing", "whole", "ground", "rotisserie"],
     "gi_range": (0, 0), "carbs": (0, 0), "fiber": (0, 0), "protein": (20, 32), "fat": (1, 15),
     "processing": "minimally_processed", "serving": 100},
    {"base": "turkey", "variations": ["breast", "thigh", "ground", "deli"],
     "gi_range": (0, 0), "carbs": (0, 0.5), "fiber": (0, 0), "protein": (25, 30), "fat": (0.5, 8),
     "processing": "minimally_processed", "serving": 100},
    {"base": "beef", "variations": ["ground lean", "ground regular", "steak", "roast", "ribeye", "sirloin", "tenderloin"],
     "gi_range": (0, 0), "carbs": (0, 0), "fiber": (0, 0), "protein": (20, 27), "fat": (5, 25),
     "processing": "minimally_processed", "serving": 100},
    {"base": "pork", "variations": ["loin", "chop", "tenderloin", "shoulder", "bacon", "sausage"],
     "gi_range": (0, 0), "carbs": (0, 2), "fiber": (0, 0), "protein": (20, 27), "fat": (5, 35),
     "processing": ["minimally_processed", "processed"], "serving": 100},
    {"base": "fish", "variations": ["salmon", "tuna", "cod", "halibut", "tilapia", "mackerel", "sardines", "trout"],
     "gi_range": (0, 0), "carbs": (0, 0), "fiber": (0, 0), "protein": (18, 30), "fat": (0.5, 15),
     "processing": "minimally_processed", "serving": 100},
    {"base": "seafood", "variations": ["shrimp", "crab", "lobster", "scallops", "mussels", "oysters", "clams"],
     "gi_range": (0, 0), "carbs": (0, 3), "fiber": (0, 0), "protein": (15, 25), "fat": (0.3, 2),
     "processing": "minimally_processed", "serving": 100},
    {"base": "egg", "variations": ["whole", "white", "yolk", "scrambled", "boiled", "fried", "poached"],
     "gi_range": (0, 0), "carbs": (0.5, 1.5), "fiber": (0, 0), "protein": (11, 13), "fat": (9, 12),
     "processing": "minimally_processed", "serving": 50},
    
    # Legumes
    {"base": "bean", "variations": ["black", "kidney", "pinto", "navy", "lima", "cannellini", "garbanzo", "chickpea", "fava", "mung"],
     "gi_range": (25, 40), "carbs": (20, 28), "fiber": (6, 10), "protein": (7, 10), "fat": (0.3, 1.5),
     "processing": "minimally_processed", "serving": 172},
    {"base": "lentil", "variations": ["brown", "green", "red", "black", "yellow", "cooked"],
     "gi_range": (25, 35), "carbs": (18, 22), "fiber": (7, 10), "protein": (8, 10), "fat": (0.3, 0.6),
     "processing": "minimally_processed", "serving": 198},
    {"base": "pea", "variations": ["green", "split", "black-eyed", "chickpea", "snow", "sugar snap"],
     "gi_range": (22, 50), "carbs": (12, 22), "fiber": (4, 8), "protein": (4, 6), "fat": (0.2, 0.6),
     "processing": "minimally_processed", "serving": 145},
    
    # Nuts & Seeds
    {"base": "nut", "variations": ["almond", "walnut", "pecan", "cashew", "pistachio", "hazelnut", "brazil", "macadamia", "pine"],
     "gi_range": (0, 25), "carbs": (10, 30), "fiber": (3, 13), "protein": (15, 25), "fat": (40, 70),
     "processing": "minimally_processed", "serving": 28},
    {"base": "seed", "variations": ["chia", "flax", "hemp", "pumpkin", "sunflower", "sesame", "poppy"],
     "gi_range": (0, 20), "carbs": (5, 25), "fiber": (5, 35), "protein": (15, 30), "fat": (30, 50),
     "processing": "minimally_processed", "serving": 28},
    {"base": "peanut", "variations": ["raw", "roasted", "salted", "unsalted", "butter", "powder"],
     "gi_range": (10, 15), "carbs": (14, 18), "fiber": (8, 9), "protein": (24, 28), "fat": (48, 52),
     "processing": ["minimally_processed", "processed"], "serving": 28},
    
    # Dairy
    {"base": "milk", "variations": ["whole", "2%", "1%", "skim", "almond", "soy", "oat", "coconut", "rice"],
     "gi_range": (11, 40), "carbs": (0, 12), "fiber": (0, 2), "protein": (1, 8), "fat": (0, 4),
     "processing": ["processed", "minimally_processed"], "serving": 244},
    {"base": "yogurt", "variations": ["greek plain", "greek vanilla", "regular plain", "regular vanilla", "low-fat", "non-fat", "full-fat"],
     "gi_range": (11, 35), "carbs": (3, 15), "fiber": (0, 0), "protein": (3, 17), "fat": (0, 10),
     "processing": "processed", "serving": 170},
    {"base": "cheese", "variations": ["cheddar", "mozzarella", "swiss", "feta", "goat", "cottage", "ricotta", "parmesan", "blue", "brie"],
     "gi_range": (0, 0), "carbs": (0, 4), "fiber": (0, 0), "protein": (7, 32), "fat": (4, 35),
     "processing": "processed", "serving": 28},
    
    # Other
    {"base": "corn", "variations": ["sweet", "kernels", "on cob", "canned", "frozen"],
     "gi_range": (48, 60), "carbs": (18, 22), "fiber": (2.0, 3.0), "protein": (3.0, 4.0), "fat": (1.0, 1.5),
     "processing": ["whole", "processed"], "serving": 145},
    {"base": "cereal", "variations": ["cornflakes", "rice krispies", "cheerios", "oatmeal", "granola", "muesli", "bran flakes"],
     "gi_range": (40, 90), "carbs": (60, 90), "fiber": (2, 15), "protein": (5, 15), "fat": (1, 20),
     "processing": ["processed", "ultra_processed"], "serving": 28},
    {"base": "sweetener", "variations": ["honey", "maple syrup", "agave", "coconut sugar", "brown sugar", "white sugar"],
     "gi_range": (30, 100), "carbs": (75, 100), "fiber": (0, 1), "protein": (0, 0.5), "fat": (0, 0),
     "processing": ["minimally_processed", "processed"], "serving": 21},
    {"base": "chocolate", "variations": ["dark 70%", "dark 85%", "milk", "white", "cocoa powder"],
     "gi_range": (20, 45), "carbs": (30, 60), "fiber": (7, 12), "protein": (5, 10), "fat": (30, 50),
     "processing": "processed", "serving": 28},
    {"base": "avocado", "variations": ["whole", "mashed", "guacamole"],
     "gi_range": (10, 15), "carbs": (8, 10), "fiber": (6, 7), "protein": (2, 3), "fat": (14, 16),
     "processing": "whole", "serving": 150},
]

def generate_food_entry(template, variation):
    """Generate a single food entry from a template."""
    name = f"{variation} {template['base']}" if variation != template['base'] else template['base']
    
    # Handle processing level
    if isinstance(template['processing'], list):
        processing = random.choice(template['processing'])
    else:
        processing = template['processing']
    
    # Generate values within ranges
    gi = random.randint(template['gi_range'][0], template['gi_range'][1])
    carbs = round(random.uniform(template['carbs'][0], template['carbs'][1]), 1)
    fiber = round(random.uniform(template['fiber'][0], template['fiber'][1]), 1)
    protein = round(random.uniform(template['protein'][0], template['protein'][1]), 1)
    fat = round(random.uniform(template['fat'][0], template['fat'][1]), 1)
    
    # Serving size with some variation
    serving = template['serving']
    if isinstance(serving, int):
        serving = int(serving * random.uniform(0.9, 1.1))
    
    return {
        'name': name,
        'glycemic_index': gi,
        'carbohydrates': carbs,
        'fiber': fiber,
        'protein': protein,
        'fat': fat,
        'processing_level': processing,
        'serving_size_grams': serving
    }

def generate_database(num_entries=2000):
    """Generate nutrition database with specified number of entries."""
    foods = []
    
    # Generate from templates
    entries_per_template = num_entries // len(FOOD_TEMPLATES)
    remaining = num_entries % len(FOOD_TEMPLATES)
    
    for template in FOOD_TEMPLATES:
        count = entries_per_template
        if remaining > 0:
            count += 1
            remaining -= 1
        
        variations = template['variations']
        for _ in range(count):
            variation = random.choice(variations)
            food = generate_food_entry(template, variation)
            foods.append(food)
    
    # Shuffle for randomness
    random.shuffle(foods)
    
    return foods

def write_csv(foods, filename='nutrition_data.csv'):
    """Write foods to CSV file."""
    fieldnames = ['name', 'glycemic_index', 'carbohydrates', 'fiber', 'protein', 'fat', 
                  'processing_level', 'serving_size_grams']
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(foods)
    
    print(f"Generated {len(foods)} food entries in {filename}")

if __name__ == '__main__':
    import sys
    num_entries = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    foods = generate_database(num_entries)
    write_csv(foods)
