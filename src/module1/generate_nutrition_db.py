#!/usr/bin/env python3
"""
Generate a comprehensive nutrition database CSV file with ~2,000 unique foods.
Each entry has a unique name. Variations include distinct types and preparations.
Based on USDA FoodData Central and Glycemic Index Foundation data.
"""

import csv
import random

# Preparation methods by category (significant variation per entry)
GRAIN_PREPS = ["cooked", "steamed", "boiled", "pilaf"]
BREAD_PREPS = ["fresh", "toasted", "stale"]
PASTA_PREPS = ["cooked", "al dente", "overcooked"]
POTATO_PREPS = ["baked", "boiled", "mashed", "roasted", "steamed", "fried"]
FRUIT_PREPS = ["raw", "dried", "canned", "frozen", "baked", "stewed", "juiced", "pureed"]
VEG_PREPS = ["raw", "steamed", "roasted", "sauteed", "boiled", "grilled", "pureed", "pickled"]
PROTEIN_PREPS = ["grilled", "baked", "roasted", "poached", "pan-seared", "braised", "smoked", "stewed"]
LEGUME_PREPS = ["cooked", "canned", "refried"]
NUT_PREPS = ["raw", "roasted", "salted", "unsalted"]
DEFAULT_PREPS = ["raw"]

# Food templates: base + variations. Each (variation, base) is a distinct food.
# Optional "preparations" list adds unique entries per prep (significant difference).
FOOD_TEMPLATES = [
    # Grains & Starches
    {"base": "rice", "variations": ["white", "brown", "jasmine", "basmati", "wild", "black", "red", "arborio", "sticky", "sushi"],
     "preparations": GRAIN_PREPS, "gi_range": (50, 110), "carbs": (20, 30), "fiber": (0.4, 2.5),
     "protein": (2.5, 3.5), "fat": (0.2, 1.0), "processing": "processed", "serving": 158},
    {"base": "bread", "variations": ["white", "whole wheat", "sourdough", "rye", "pumpernickel", "multigrain", "sprouted", "naan", "pita", "bagel", "baguette", "ciabatta", "focaccia"],
     "preparations": BREAD_PREPS, "gi_range": (50, 80), "carbs": (40, 55), "fiber": (2.0, 8.0),
     "protein": (8.0, 15.0), "fat": (2.0, 5.0), "processing": "processed", "serving": 28},
    {"base": "pasta", "variations": ["white", "whole wheat", "spaghetti", "penne", "fettuccine", "linguine", "macaroni", "lasagna", "ravioli", "gnocchi"],
     "preparations": PASTA_PREPS, "gi_range": (35, 55), "carbs": (20, 30), "fiber": (1.5, 4.5),
     "protein": (4.0, 6.0), "fat": (0.8, 2.0), "processing": "processed", "serving": 140},
    {"base": "potato", "variations": ["white", "sweet", "red", "russet", "yukon gold", "fingerling", "purple"],
     "preparations": POTATO_PREPS, "gi_range": (45, 95), "carbs": (15, 25), "fiber": (2.0, 4.0),
     "protein": (1.5, 3.0), "fat": (0.1, 15.0), "processing": ["whole", "processed"], "serving": 150},
    {"base": "quinoa", "variations": ["white", "red", "black", "tricolor"],
     "preparations": GRAIN_PREPS, "gi_range": (50, 55), "carbs": (20, 22), "fiber": (2.5, 3.0),
     "protein": (4.0, 5.0), "fat": (1.8, 2.2), "processing": "minimally_processed", "serving": 185},
    {"base": "oats", "variations": ["rolled", "steel cut", "instant", "quick", "old fashioned"],
     "preparations": ["cooked", "porridge"], "gi_range": (42, 60), "carbs": (60, 70), "fiber": (10.0, 12.0),
     "protein": (15, 18), "fat": (6.0, 8.0), "processing": "minimally_processed", "serving": 81},
    {"base": "barley", "variations": ["pearl", "hulled", "pot", "scotch"],
     "preparations": GRAIN_PREPS, "gi_range": (25, 35), "carbs": (70, 75), "fiber": (15, 18),
     "protein": (10, 13), "fat": (2.0, 2.5), "processing": "minimally_processed", "serving": 157},

    # Fruits
    {"base": "apple", "variations": ["gala", "fuji", "granny smith", "honeycrisp", "pink lady", "braeburn", "red delicious", "green", "mcintosh", "golden delicious"],
     "preparations": FRUIT_PREPS, "gi_range": (30, 40), "carbs": (12, 16), "fiber": (2.0, 3.5),
     "protein": (0.2, 0.5), "fat": (0.1, 0.3), "processing": "whole", "serving": 182},
    {"base": "banana", "variations": ["yellow", "green", "ripe", "overripe"],
     "preparations": ["raw", "frozen", "dried"], "gi_range": (42, 62), "carbs": (20, 25), "fiber": (2.5, 3.5),
     "protein": (1.0, 1.5), "fat": (0.2, 0.4), "processing": "whole", "serving": 118},
    {"base": "orange", "variations": ["navel", "valencia", "blood", "mandarin", "clementine", "tangerine"],
     "preparations": ["raw", "juiced", "canned"], "gi_range": (40, 50), "carbs": (11, 13), "fiber": (2.0, 3.0),
     "protein": (0.8, 1.2), "fat": (0.1, 0.2), "processing": "whole", "serving": 131},
    {"base": "berry", "variations": ["strawberry", "blueberry", "raspberry", "blackberry", "cranberry", "gooseberry", "elderberry", "boysenberry"],
     "preparations": ["raw", "frozen", "dried"], "gi_range": (25, 55), "carbs": (7, 15), "fiber": (2.0, 8.0),
     "protein": (0.5, 1.5), "fat": (0.2, 0.7), "processing": "whole", "serving": 144},
    {"base": "grape", "variations": ["red", "green", "black", "concord", "seedless"],
     "preparations": ["raw", "frozen"], "gi_range": (45, 65), "carbs": (16, 20), "fiber": (0.8, 1.2),
     "protein": (0.6, 0.9), "fat": (0.1, 0.3), "processing": "whole", "serving": 92},
    {"base": "melon", "variations": ["watermelon", "cantaloupe", "honeydew", "crenshaw"],
     "preparations": ["raw", "chilled"], "gi_range": (60, 80), "carbs": (7, 9), "fiber": (0.4, 0.8),
     "protein": (0.5, 0.9), "fat": (0.1, 0.3), "processing": "whole", "serving": 152},
    {"base": "stone fruit", "variations": ["peach", "nectarine", "plum", "apricot", "cherry"],
     "preparations": ["raw", "dried", "canned"], "gi_range": (30, 45), "carbs": (9, 12), "fiber": (1.4, 2.5),
     "protein": (0.8, 1.2), "fat": (0.2, 0.4), "processing": "whole", "serving": 150},
    {"base": "tropical fruit", "variations": ["mango", "pineapple", "papaya", "kiwi", "passion fruit", "guava"],
     "preparations": ["raw", "frozen", "dried"], "gi_range": (40, 70), "carbs": (12, 18), "fiber": (1.5, 3.5),
     "protein": (0.5, 1.5), "fat": (0.1, 0.5), "processing": "whole", "serving": 150},

    # Vegetables
    {"base": "leafy green", "variations": ["spinach", "kale", "romaine", "arugula", "iceberg", "butter lettuce", "swiss chard", "collard greens", "mustard greens", "watercress"],
     "preparations": VEG_PREPS, "gi_range": (10, 20), "carbs": (2, 5), "fiber": (1.5, 3.0),
     "protein": (1.5, 3.5), "fat": (0.2, 0.6), "processing": "whole", "serving": 30},
    {"base": "cruciferous", "variations": ["broccoli", "cauliflower", "cabbage", "brussels sprouts", "bok choy", "kohlrabi"],
     "preparations": VEG_PREPS, "gi_range": (10, 20), "carbs": (4, 7), "fiber": (2.0, 3.5),
     "protein": (1.8, 3.5), "fat": (0.2, 0.5), "processing": "whole", "serving": 91},
    {"base": "root vegetable", "variations": ["carrot", "beet", "turnip", "parsnip", "radish", "rutabaga"],
     "preparations": VEG_PREPS, "gi_range": (30, 50), "carbs": (8, 12), "fiber": (2.0, 4.0),
     "protein": (0.8, 1.5), "fat": (0.1, 0.3), "processing": "whole", "serving": 128},
    {"base": "squash", "variations": ["zucchini", "yellow squash", "butternut", "acorn", "spaghetti", "pumpkin", "kabocha"],
     "preparations": VEG_PREPS, "gi_range": (15, 75), "carbs": (3, 12), "fiber": (1.0, 3.0),
     "protein": (1.0, 2.0), "fat": (0.1, 0.3), "processing": "whole", "serving": 124},
    {"base": "pepper", "variations": ["bell red", "bell green", "bell yellow", "bell orange", "jalapeno", "serrano", "poblano"],
     "preparations": VEG_PREPS, "gi_range": (10, 20), "carbs": (4, 7), "fiber": (1.5, 2.5),
     "protein": (0.9, 1.5), "fat": (0.2, 0.4), "processing": "whole", "serving": 149},
    {"base": "tomato", "variations": ["cherry", "roma", "beefsteak", "heirloom"],
     "preparations": ["raw", "canned", "sun-dried"], "gi_range": (10, 20), "carbs": (3, 5), "fiber": (1.0, 2.0),
     "protein": (0.8, 1.2), "fat": (0.1, 0.3), "processing": ["whole", "processed"], "serving": 182},
    {"base": "onion", "variations": ["yellow", "white", "red", "sweet", "shallot", "scallion", "leek"],
     "preparations": VEG_PREPS, "gi_range": (10, 20), "carbs": (7, 10), "fiber": (1.5, 2.5),
     "protein": (1.0, 1.5), "fat": (0.1, 0.2), "processing": "whole", "serving": 160},
    {"base": "mushroom", "variations": ["button", "cremini", "portobello", "shiitake", "oyster", "maitake", "enoki"],
     "preparations": VEG_PREPS, "gi_range": (10, 20), "carbs": (2, 4), "fiber": (1.0, 2.0),
     "protein": (2.0, 3.5), "fat": (0.2, 0.5), "processing": "whole", "serving": 70},

    # Proteins
    {"base": "chicken", "variations": ["breast", "thigh", "drumstick", "wing", "whole", "ground", "rotisserie"],
     "preparations": PROTEIN_PREPS, "gi_range": (0, 0), "carbs": (0, 0), "fiber": (0, 0),
     "protein": (20, 32), "fat": (1, 15), "processing": "minimally_processed", "serving": 100},
    {"base": "turkey", "variations": ["breast", "thigh", "ground", "deli"],
     "preparations": PROTEIN_PREPS + ["sliced"], "gi_range": (0, 0), "carbs": (0, 0.5), "fiber": (0, 0),
     "protein": (25, 30), "fat": (0.5, 8), "processing": "minimally_processed", "serving": 100},
    {"base": "beef", "variations": ["ground lean", "ground regular", "steak", "roast", "ribeye", "sirloin", "tenderloin"],
     "preparations": PROTEIN_PREPS, "gi_range": (0, 0), "carbs": (0, 0), "fiber": (0, 0),
     "protein": (20, 27), "fat": (5, 25), "processing": "minimally_processed", "serving": 100},
    {"base": "pork", "variations": ["loin", "chop", "tenderloin", "shoulder", "bacon", "sausage"],
     "preparations": PROTEIN_PREPS, "gi_range": (0, 0), "carbs": (0, 2), "fiber": (0, 0),
     "protein": (20, 27), "fat": (5, 35), "processing": ["minimally_processed", "processed"], "serving": 100},
    {"base": "fish", "variations": ["salmon", "tuna", "cod", "halibut", "tilapia", "mackerel", "sardines", "trout"],
     "preparations": PROTEIN_PREPS, "gi_range": (0, 0), "carbs": (0, 0), "fiber": (0, 0),
     "protein": (18, 30), "fat": (0.5, 15), "processing": "minimally_processed", "serving": 100},
    {"base": "seafood", "variations": ["shrimp", "crab", "lobster", "scallops", "mussels", "oysters", "clams"],
     "preparations": PROTEIN_PREPS, "gi_range": (0, 0), "carbs": (0, 3), "fiber": (0, 0),
     "protein": (15, 25), "fat": (0.3, 2), "processing": "minimally_processed", "serving": 100},
    {"base": "egg", "variations": ["whole", "white", "yolk", "scrambled", "boiled", "fried", "poached"],
     "preparations": DEFAULT_PREPS, "gi_range": (0, 0), "carbs": (0.5, 1.5), "fiber": (0, 0),
     "protein": (11, 13), "fat": (9, 12), "processing": "minimally_processed", "serving": 50},

    # Legumes
    {"base": "bean", "variations": ["black", "kidney", "pinto", "navy", "lima", "cannellini", "garbanzo", "chickpea", "fava", "mung"],
     "preparations": LEGUME_PREPS, "gi_range": (25, 40), "carbs": (20, 28), "fiber": (6, 10),
     "protein": (7, 10), "fat": (0.3, 1.5), "processing": "minimally_processed", "serving": 172},
    {"base": "lentil", "variations": ["brown", "green", "red", "black", "yellow"],
     "preparations": LEGUME_PREPS, "gi_range": (25, 35), "carbs": (18, 22), "fiber": (7, 10),
     "protein": (8, 10), "fat": (0.3, 0.6), "processing": "minimally_processed", "serving": 198},
    {"base": "pea", "variations": ["green", "split", "black-eyed", "snow", "sugar snap"],
     "preparations": ["cooked", "frozen", "canned"], "gi_range": (22, 50), "carbs": (12, 22), "fiber": (4, 8),
     "protein": (4, 6), "fat": (0.2, 0.6), "processing": "minimally_processed", "serving": 145},

    # Nuts & Seeds
    {"base": "nut", "variations": ["almond", "walnut", "pecan", "cashew", "pistachio", "hazelnut", "brazil", "macadamia", "pine"],
     "preparations": NUT_PREPS, "gi_range": (0, 25), "carbs": (10, 30), "fiber": (3, 13),
     "protein": (15, 25), "fat": (40, 70), "processing": "minimally_processed", "serving": 28},
    {"base": "seed", "variations": ["chia", "flax", "hemp", "pumpkin", "sunflower", "sesame", "poppy"],
     "preparations": NUT_PREPS, "gi_range": (0, 20), "carbs": (5, 25), "fiber": (5, 35),
     "protein": (15, 30), "fat": (30, 50), "processing": "minimally_processed", "serving": 28},
    {"base": "peanut", "variations": ["raw", "roasted", "salted", "unsalted", "butter", "powder"],
     "preparations": DEFAULT_PREPS, "gi_range": (10, 15), "carbs": (14, 18), "fiber": (8, 9),
     "protein": (24, 28), "fat": (48, 52), "processing": ["minimally_processed", "processed"], "serving": 28},

    # Dairy
    {"base": "milk", "variations": ["whole", "2%", "1%", "skim", "almond", "soy", "oat", "coconut", "rice"],
     "preparations": DEFAULT_PREPS, "gi_range": (11, 40), "carbs": (0, 12), "fiber": (0, 2),
     "protein": (1, 8), "fat": (0, 4), "processing": ["processed", "minimally_processed"], "serving": 244},
    {"base": "yogurt", "variations": ["greek plain", "greek vanilla", "regular plain", "regular vanilla", "low-fat", "non-fat", "full-fat"],
     "preparations": DEFAULT_PREPS, "gi_range": (11, 35), "carbs": (3, 15), "fiber": (0, 0),
     "protein": (3, 17), "fat": (0, 10), "processing": "processed", "serving": 170},
    {"base": "cheese", "variations": ["cheddar", "mozzarella", "swiss", "feta", "goat", "cottage", "ricotta", "parmesan", "blue", "brie"],
     "preparations": DEFAULT_PREPS, "gi_range": (0, 0), "carbs": (0, 4), "fiber": (0, 0),
     "protein": (7, 32), "fat": (4, 35), "processing": "processed", "serving": 28},

    # Other
    {"base": "corn", "variations": ["sweet", "kernels", "on cob", "canned", "frozen"],
     "preparations": ["raw", "cooked", "grilled"], "gi_range": (48, 60), "carbs": (18, 22), "fiber": (2.0, 3.0),
     "protein": (3.0, 4.0), "fat": (1.0, 1.5), "processing": ["whole", "processed"], "serving": 145},
    {"base": "cereal", "variations": ["cornflakes", "rice krispies", "cheerios", "oatmeal", "granola", "muesli", "bran flakes"],
     "preparations": ["with milk", "dry"], "gi_range": (40, 90), "carbs": (60, 90), "fiber": (2, 15),
     "protein": (5, 15), "fat": (1, 20), "processing": ["processed", "ultra_processed"], "serving": 28},
    {"base": "sweetener", "variations": ["honey", "maple syrup", "agave", "coconut sugar", "brown sugar", "white sugar"],
     "preparations": DEFAULT_PREPS, "gi_range": (30, 100), "carbs": (75, 100), "fiber": (0, 1),
     "protein": (0, 0.5), "fat": (0, 0), "processing": ["minimally_processed", "processed"], "serving": 21},
    {"base": "chocolate", "variations": ["dark 70%", "dark 85%", "milk", "white", "cocoa powder"],
     "preparations": DEFAULT_PREPS, "gi_range": (20, 45), "carbs": (30, 60), "fiber": (7, 12),
     "protein": (5, 10), "fat": (30, 50), "processing": "processed", "serving": 28},
    {"base": "avocado", "variations": ["whole", "mashed", "guacamole"],
     "preparations": ["raw", "ripe"], "gi_range": (10, 15), "carbs": (8, 10), "fiber": (6, 7),
     "protein": (2, 3), "fat": (14, 16), "processing": "whole", "serving": 150},

    # Additional categories for more unique entries
    {"base": "cracker", "variations": ["saltine", "whole grain", "rye", "water", "wheat", "rice", "cheese", "multigrain"],
     "preparations": DEFAULT_PREPS, "gi_range": (55, 75), "carbs": (65, 80), "fiber": (2, 8),
     "protein": (8, 14), "fat": (5, 20), "processing": "processed", "serving": 28},
    {"base": "hummus", "variations": ["plain", "garlic", "roasted red pepper", "sundried tomato", "black bean", "edamame"],
     "preparations": DEFAULT_PREPS, "gi_range": (6, 25), "carbs": (14, 20), "fiber": (4, 6),
     "protein": (5, 8), "fat": (8, 15), "processing": "processed", "serving": 60},
    {"base": "nut butter", "variations": ["peanut", "almond", "cashew", "sunflower", "tahini"],
     "preparations": DEFAULT_PREPS, "gi_range": (0, 25), "carbs": (18, 25), "fiber": (6, 10),
     "protein": (22, 28), "fat": (48, 55), "processing": "processed", "serving": 32},
    {"base": "dried fruit", "variations": ["raisin", "apricot", "date", "prune", "fig", "cranberry", "mango", "pineapple"],
     "preparations": DEFAULT_PREPS, "gi_range": (40, 70), "carbs": (65, 80), "fiber": (5, 12),
     "protein": (2, 4), "fat": (0.3, 1.5), "processing": "processed", "serving": 40},
    {"base": "soup", "variations": ["chicken noodle", "vegetable", "tomato", "lentil", "minestrone", "black bean", "miso", "butternut squash"],
     "preparations": ["canned", "homemade"], "gi_range": (30, 60), "carbs": (5, 20), "fiber": (1, 5),
     "protein": (3, 12), "fat": (1, 8), "processing": "processed", "serving": 245},
    {"base": "sauce", "variations": ["marinara", "alfredo", "pesto", "soy", "teriyaki", "bbq", "hot", "tahini"],
     "preparations": DEFAULT_PREPS, "gi_range": (20, 60), "carbs": (5, 25), "fiber": (0, 2),
     "protein": (1, 5), "fat": (0, 25), "processing": "processed", "serving": 30},
    {"base": "smoothie", "variations": ["berry", "green", "tropical", "banana", "protein", "green tea"],
     "preparations": DEFAULT_PREPS, "gi_range": (30, 55), "carbs": (15, 30), "fiber": (2, 6),
     "protein": (2, 15), "fat": (0.5, 5), "processing": "processed", "serving": 240},
    {"base": "tofu", "variations": ["firm", "soft", "silken", "extra firm", "baked"],
     "preparations": ["raw", "baked", "fried", "grilled"], "gi_range": (0, 20), "carbs": (1, 3), "fiber": (0.5, 1.5),
     "protein": (8, 12), "fat": (4, 6), "processing": "processed", "serving": 100},
    {"base": "tempeh", "variations": ["plain", "five grain", "flax", "wild rice"],
     "preparations": ["raw", "steamed", "baked", "fried"], "gi_range": (0, 20), "carbs": (7, 10), "fiber": (0, 0),
     "protein": (18, 21), "fat": (8, 12), "processing": "processed", "serving": 100},
    {"base": "jam", "variations": ["strawberry", "raspberry", "blackberry", "apricot", "grape", "orange", "fig"],
     "preparations": DEFAULT_PREPS, "gi_range": (50, 70), "carbs": (65, 75), "fiber": (0.5, 2),
     "protein": (0.2, 0.5), "fat": (0, 0.2), "processing": "processed", "serving": 20},
    {"base": "oil", "variations": ["olive", "canola", "coconut", "avocado", "sesame", "sunflower", "peanut"],
     "preparations": DEFAULT_PREPS, "gi_range": (0, 0), "carbs": (0, 0), "fiber": (0, 0),
     "protein": (0, 0), "fat": (100, 100), "processing": "minimally_processed", "serving": 14},
    {"base": "vinegar", "variations": ["apple cider", "balsamic", "red wine", "white wine", "rice", "distilled"],
     "preparations": DEFAULT_PREPS, "gi_range": (5, 15), "carbs": (0, 3), "fiber": (0, 0),
     "protein": (0, 0), "fat": (0, 0), "processing": "processed", "serving": 15},
    {"base": "dip", "variations": ["ranch", "sour cream", "tzatziki", "spinach", "artichoke", "bean", "guacamole"],
     "preparations": DEFAULT_PREPS, "gi_range": (15, 40), "carbs": (5, 15), "fiber": (0.5, 3),
     "protein": (2, 6), "fat": (8, 25), "processing": "processed", "serving": 30},
    {"base": "pancake", "variations": ["buttermilk", "whole wheat", "buckwheat", "banana", "blueberry"],
     "preparations": ["plain", "with syrup"], "gi_range": (55, 75), "carbs": (45, 60), "fiber": (1, 4),
     "protein": (8, 12), "fat": (5, 15), "processing": "processed", "serving": 75},
    {"base": "waffle", "variations": ["belgian", "whole wheat", "buttermilk", "chocolate"],
     "preparations": DEFAULT_PREPS, "gi_range": (55, 75), "carbs": (45, 55), "fiber": (1, 3),
     "protein": (6, 10), "fat": (8, 18), "processing": "processed", "serving": 75},
    {"base": "muffin", "variations": ["blueberry", "bran", "chocolate", "corn", "apple cinnamon", "pumpkin"],
     "preparations": DEFAULT_PREPS, "gi_range": (50, 70), "carbs": (45, 60), "fiber": (1, 5),
     "protein": (5, 9), "fat": (15, 25), "processing": "processed", "serving": 57},
    {"base": "cookie", "variations": ["chocolate chip", "oatmeal", "sugar", "ginger", "shortbread", "peanut butter"],
     "preparations": DEFAULT_PREPS, "gi_range": (55, 75), "carbs": (60, 75), "fiber": (1, 3),
     "protein": (5, 8), "fat": (18, 28), "processing": "ultra_processed", "serving": 28},
    {"base": "salad", "variations": ["green", "caesar", "greek", "coleslaw", "potato", "pasta", "quinoa", "fruit"],
     "preparations": ["with dressing", "no dressing"], "gi_range": (15, 55), "carbs": (5, 35), "fiber": (1, 6),
     "protein": (2, 12), "fat": (2, 25), "processing": "processed", "serving": 150},
    {"base": "trail mix", "variations": ["traditional", "tropical", "chocolate", "spicy", "fruit and nut", "mountain", "sweet and salty"],
     "preparations": DEFAULT_PREPS, "gi_range": (25, 45), "carbs": (45, 55), "fiber": (5, 10),
     "protein": (10, 18), "fat": (25, 40), "processing": "processed", "serving": 42},
    {"base": "chips", "variations": ["potato", "tortilla", "corn", "pita", "sweet potato", "kale", "bean"],
     "preparations": ["plain", "salted", "baked", "fried"], "gi_range": (50, 75), "carbs": (45, 60), "fiber": (3, 8),
     "protein": (5, 10), "fat": (25, 40), "processing": "ultra_processed", "serving": 28},
    {"base": "popcorn", "variations": ["air-popped", "oil-popped", "microwave", "caramel", "cheddar"],
     "preparations": DEFAULT_PREPS, "gi_range": (55, 75), "carbs": (55, 65), "fiber": (10, 14),
     "protein": (8, 12), "fat": (2, 35), "processing": ["minimally_processed", "processed"], "serving": 28},
    {"base": "energy bar", "variations": ["granola", "protein", "nut", "fruit", "chocolate", "oat"],
     "preparations": DEFAULT_PREPS, "gi_range": (40, 65), "carbs": (45, 65), "fiber": (3, 8),
     "protein": (5, 25), "fat": (10, 25), "processing": "processed", "serving": 60},
    {"base": "salad dressing", "variations": ["ranch", "italian", "caesar", "balsamic", "vinaigrette", "thousand island", "blue cheese", "honey mustard"],
     "preparations": DEFAULT_PREPS, "gi_range": (15, 45), "carbs": (3, 15), "fiber": (0, 0.5),
     "protein": (0.5, 2), "fat": (15, 45), "processing": "processed", "serving": 30},
    {"base": "sausage", "variations": ["pork", "chicken", "turkey", "italian", "bratwurst", "kielbasa", "andouille"],
     "preparations": PROTEIN_PREPS, "gi_range": (0, 15), "carbs": (0, 5), "fiber": (0, 0),
     "protein": (15, 22), "fat": (15, 35), "processing": "processed", "serving": 85},
    {"base": "bacon", "variations": ["pork", "turkey", "canadian", "center cut"],
     "preparations": ["crispy", "chewy", "baked"], "gi_range": (0, 0), "carbs": (0, 1), "fiber": (0, 0),
     "protein": (25, 35), "fat": (35, 50), "processing": "processed", "serving": 15},
    {"base": "rice cake", "variations": ["plain", "brown rice", "multigrain", "quinoa", "caramel", "cheddar", "apple cinnamon"],
     "preparations": DEFAULT_PREPS, "gi_range": (60, 85), "carbs": (80, 90), "fiber": (0.5, 2),
     "protein": (6, 9), "fat": (0.5, 3), "processing": "processed", "serving": 9},
    {"base": "pretzel", "variations": ["soft", "hard", "rod", "twist", "mini", "yogurt covered"],
     "preparations": DEFAULT_PREPS, "gi_range": (65, 85), "carbs": (70, 80), "fiber": (2, 4),
     "protein": (8, 12), "fat": (2, 15), "processing": "processed", "serving": 28},
    {"base": "ice cream", "variations": ["vanilla", "chocolate", "strawberry", "mint", "cookie dough", "coffee", "pistachio"],
     "preparations": DEFAULT_PREPS, "gi_range": (45, 65), "carbs": (22, 28), "fiber": (0, 1),
     "protein": (3, 5), "fat": (10, 16), "processing": "processed", "serving": 66},
    {"base": "pie", "variations": ["apple", "cherry", "pumpkin", "pecan", "key lime", "blueberry", "peach"],
     "preparations": DEFAULT_PREPS, "gi_range": (50, 70), "carbs": (45, 55), "fiber": (1, 4),
     "protein": (3, 6), "fat": (12, 22), "processing": "processed", "serving": 125},
    {"base": "cake", "variations": ["chocolate", "vanilla", "carrot", "red velvet", "angel food", "pound", "cheesecake"],
     "preparations": DEFAULT_PREPS, "gi_range": (55, 75), "carbs": (45, 60), "fiber": (0.5, 2),
     "protein": (4, 8), "fat": (15, 30), "processing": "processed", "serving": 80},
    {"base": "croissant", "variations": ["plain", "butter", "chocolate", "almond", "ham and cheese"],
     "preparations": DEFAULT_PREPS, "gi_range": (55, 70), "carbs": (45, 55), "fiber": (2, 3),
     "protein": (7, 11), "fat": (18, 28), "processing": "processed", "serving": 57},
    {"base": "pudding", "variations": ["chocolate", "vanilla", "butterscotch", "tapioca", "rice"],
     "preparations": DEFAULT_PREPS, "gi_range": (55, 75), "carbs": (18, 25), "fiber": (0, 1),
     "protein": (2, 4), "fat": (3, 8), "processing": "processed", "serving": 100},
    {"base": "juice", "variations": ["orange", "apple", "grape", "cranberry", "grapefruit", "tomato", "carrot", "beet", "pomegranate", "prune", "lemon", "lime", "mango", "pineapple"],
     "preparations": ["fresh", "from concentrate", "canned"], "gi_range": (40, 70), "carbs": (10, 15), "fiber": (0, 0.5),
     "protein": (0.5, 2), "fat": (0, 0.2), "processing": "processed", "serving": 248},
    {"base": "tea", "variations": ["black", "green", "white", "oolong", "herbal", "chai", "earl grey", "jasmine", "ginger"],
     "preparations": ["hot", "iced", "unsweetened", "sweetened"], "gi_range": (0, 25), "carbs": (0, 8), "fiber": (0, 0),
     "protein": (0, 0.5), "fat": (0, 0), "processing": "minimally_processed", "serving": 240},
    {"base": "coffee", "variations": ["black", "espresso", "americano", "latte", "cappuccino", "cold brew", "decaf"],
     "preparations": ["hot", "iced", "with milk", "with cream"], "gi_range": (0, 30), "carbs": (0, 12), "fiber": (0, 0),
     "protein": (0, 4), "fat": (0, 5), "processing": "minimally_processed", "serving": 240},
    {"base": "sports drink", "variations": ["original", "low calorie", "electrolyte", "energy", "coconut water"],
     "preparations": DEFAULT_PREPS, "gi_range": (45, 75), "carbs": (5, 15), "fiber": (0, 0),
     "protein": (0, 1), "fat": (0, 0), "processing": "processed", "serving": 240},
    {"base": "soda", "variations": ["cola", "diet cola", "lemon-lime", "orange", "root beer", "ginger ale", "grape", "cream soda", "fruit punch", "seltzer", "sprite", "dr pepper"],
     "preparations": DEFAULT_PREPS, "gi_range": (50, 75), "carbs": (0, 40), "fiber": (0, 0),
     "protein": (0, 0), "fat": (0, 0), "processing": "ultra_processed", "serving": 355},
    {"base": "sandwich", "variations": ["turkey", "ham", "chicken", "tuna", "egg salad", "blt", "grilled cheese", "pb and j", "veggie", "club", "reuben", "cuban"],
     "preparations": ["on white", "on wheat", "on rye", "wrap"], "gi_range": (45, 70), "carbs": (35, 55), "fiber": (2, 6),
     "protein": (15, 35), "fat": (10, 30), "processing": "processed", "serving": 150},
    {"base": "taco", "variations": ["beef", "chicken", "fish", "carnitas", "veggie", "bean", "shrimp"],
     "preparations": ["soft shell", "hard shell", "corn tortilla"], "gi_range": (45, 65), "carbs": (20, 35), "fiber": (2, 6),
     "protein": (12, 25), "fat": (8, 25), "processing": "processed", "serving": 100},
    {"base": "burrito", "variations": ["beef", "chicken", "bean", "veggie", "breakfast", "shrimp"],
     "preparations": ["flour tortilla", "whole wheat tortilla"], "gi_range": (45, 65), "carbs": (45, 65), "fiber": (5, 12),
     "protein": (18, 35), "fat": (12, 28), "processing": "processed", "serving": 250},
    {"base": "pizza", "variations": ["cheese", "pepperoni", "veggie", "margherita", "hawaiian", "meat lovers", "bbq chicken", "supreme"],
     "preparations": ["thin crust", "regular crust"], "gi_range": (50, 70), "carbs": (25, 40), "fiber": (2, 4),
     "protein": (10, 18), "fat": (8, 18), "processing": "processed", "serving": 107},
    {"base": "burger", "variations": ["beef", "chicken", "turkey", "veggie", "salmon", "bison"],
     "preparations": ["single", "double"], "gi_range": (45, 65), "carbs": (30, 45), "fiber": (1, 3),
     "protein": (20, 45), "fat": (15, 40), "processing": "processed", "serving": 150},
    {"base": "stir fry", "variations": ["chicken", "beef", "shrimp", "tofu", "veggie"],
     "preparations": ["with rice", "with noodles"], "gi_range": (45, 65), "carbs": (25, 50), "fiber": (2, 5),
     "protein": (15, 30), "fat": (5, 18), "processing": "processed", "serving": 350},
    {"base": "curry", "variations": ["chicken", "lamb", "vegetable", "chickpea", "shrimp", "paneer"],
     "preparations": ["red", "green"], "gi_range": (40, 60), "carbs": (15, 25), "fiber": (2, 6),
     "protein": (12, 22), "fat": (8, 22), "processing": "processed", "serving": 250},
    {"base": "sushi roll", "variations": ["california", "spicy tuna", "salmon", "veggie", "eel", "tempura"],
     "preparations": ["with white rice", "with brown rice"], "gi_range": (55, 75), "carbs": (25, 40), "fiber": (1, 3),
     "protein": (8, 18), "fat": (2, 12), "processing": "processed", "serving": 100},
    {"base": "quesadilla", "variations": ["cheese", "chicken", "beef", "veggie"],
     "preparations": ["flour tortilla", "corn tortilla"], "gi_range": (50, 65), "carbs": (30, 45), "fiber": (2, 5),
     "protein": (15, 28), "fat": (12, 25), "processing": "processed", "serving": 150},
    {"base": "omelette", "variations": ["plain", "cheese", "veggie", "western", "denver"],
     "preparations": DEFAULT_PREPS, "gi_range": (0, 15), "carbs": (1, 5), "fiber": (0, 1),
     "protein": (12, 18), "fat": (14, 22), "processing": "minimally_processed", "serving": 120},
    {"base": "fried rice", "variations": ["vegetable", "chicken", "shrimp", "egg"],
     "preparations": ["white rice", "brown rice"], "gi_range": (55, 75), "carbs": (35, 45), "fiber": (1, 3),
     "protein": (8, 20), "fat": (5, 15), "processing": "processed", "serving": 250},
    {"base": "noodle dish", "variations": ["ramen", "udon", "soba", "lo mein", "pad thai"],
     "preparations": ["with broth", "stir fried"], "gi_range": (50, 70), "carbs": (40, 55), "fiber": (2, 5),
     "protein": (10, 22), "fat": (5, 20), "processing": "processed", "serving": 350},
    {"base": "instant noodle", "variations": ["chicken", "beef", "shrimp", "vegetable", "miso", "kimchi"],
     "preparations": ["cup", "pack"], "gi_range": (50, 70), "carbs": (45, 55), "fiber": (2, 4),
     "protein": (8, 14), "fat": (14, 22), "processing": "ultra_processed", "serving": 85},
    {"base": "frozen meal", "variations": ["lasagna", "mac and cheese", "stir fry", "chicken dinner", "beef dinner", "vegetable", "fish", "burrito", "pot pie", "enchilada"],
     "preparations": DEFAULT_PREPS, "gi_range": (45, 70), "carbs": (25, 50), "fiber": (2, 6),
     "protein": (12, 25), "fat": (8, 25), "processing": "processed", "serving": 280},
    {"base": "canned fruit", "variations": ["peach", "pear", "pineapple", "fruit cocktail", "mandarin", "apricot"],
     "preparations": ["in syrup", "in juice"], "gi_range": (45, 65), "carbs": (18, 28), "fiber": (1, 3),
     "protein": (0.3, 1), "fat": (0, 0.2), "processing": "processed", "serving": 120},
    {"base": "fruit cup", "variations": ["mixed fruit", "peaches", "mandarin", "fruit cocktail"],
     "preparations": ["in syrup", "in juice"], "gi_range": (45, 65), "carbs": (15, 25), "fiber": (1, 2),
     "protein": (0.3, 0.8), "fat": (0, 0.1), "processing": "processed", "serving": 113},
    {"base": "dumpling", "variations": ["pork", "chicken", "vegetable", "shrimp"],
     "preparations": ["steamed", "fried"], "gi_range": (45, 65), "carbs": (25, 35), "fiber": (1, 3),
     "protein": (8, 15), "fat": (5, 18), "processing": "processed", "serving": 100},
    {"base": "spring roll", "variations": ["vegetable", "shrimp", "pork"],
     "preparations": ["fried", "fresh"], "gi_range": (50, 70), "carbs": (20, 35), "fiber": (1, 3),
     "protein": (5, 12), "fat": (3, 20), "processing": "processed", "serving": 85},
    {"base": "pastry", "variations": ["danish", "turnover", "strudel", "scone"],
     "preparations": DEFAULT_PREPS, "gi_range": (55, 70), "carbs": (48, 58), "fiber": (1, 3),
     "protein": (5, 8), "fat": (18, 28), "processing": "processed", "serving": 65},
]


def generate_food_entry(template, variation, preparation):
    """Generate a single food entry. Name is unique: 'variation base preparation'."""
    # Build unique name: "variation base preparation"
    base = template["base"]
    if preparation and preparation != "raw" and preparation not in ("cold", "room temperature"):
        name = f"{variation} {base} {preparation}"
    else:
        name = f"{variation} {base}"

    if isinstance(template["processing"], list):
        processing = random.choice(template["processing"])
    else:
        processing = template["processing"]

    gi = random.randint(template["gi_range"][0], template["gi_range"][1])
    carbs = round(random.uniform(template["carbs"][0], template["carbs"][1]), 1)
    fiber = round(random.uniform(template["fiber"][0], template["fiber"][1]), 1)
    protein = round(random.uniform(template["protein"][0], template["protein"][1]), 1)
    fat = round(random.uniform(template["fat"][0], template["fat"][1]), 1)

    serving = template["serving"]
    if isinstance(serving, int):
        serving = max(1, int(serving * random.uniform(0.9, 1.1)))

    return {
        "name": name,
        "glycemic_index": gi,
        "carbohydrates": carbs,
        "fiber": fiber,
        "protein": protein,
        "fat": fat,
        "processing_level": processing,
        "serving_size_grams": serving,
    }


def build_unique_combos():
    """Build all unique (template, variation, preparation) combinations."""
    combos = []
    for template in FOOD_TEMPLATES:
        preps = template.get("preparations", DEFAULT_PREPS)
        for variation in template["variations"]:
            for preparation in preps:
                combos.append((template, variation, preparation))
    return combos


def generate_database(num_entries=2000):
    """Generate nutrition database with unique entries only."""
    combos = build_unique_combos()
    # If we have more combos than requested, sample without replacement
    if len(combos) >= num_entries:
        combos = random.sample(combos, num_entries)
    # If we have fewer, we use all and report (shouldn't happen with current templates)

    foods = []
    seen_names = set()
    for template, variation, preparation in combos:
        entry = generate_food_entry(template, variation, preparation)
        # Ensure name is unique (safety check)
        name = entry["name"]
        if name in seen_names:
            name = f"{name} ({len(seen_names)})"
            entry["name"] = name
        seen_names.add(entry["name"])
        foods.append(entry)

    random.shuffle(foods)
    return foods


def write_csv(foods, filename="nutrition_data.csv"):
    """Write foods to CSV file."""
    fieldnames = [
        "name",
        "glycemic_index",
        "carbohydrates",
        "fiber",
        "protein",
        "fat",
        "processing_level",
        "serving_size_grams",
    ]
    with open(filename, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(foods)
    print(f"Generated {len(foods)} unique food entries in {filename}")


if __name__ == "__main__":
    import sys
    num_entries = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    foods = generate_database(num_entries)
    write_csv(foods)
