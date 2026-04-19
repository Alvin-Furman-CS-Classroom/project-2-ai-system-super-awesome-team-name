#!/usr/bin/env python3
"""
Build nutrition_data.csv from nutrition_data_legacy.csv using NAMING_CONVENTIONS.md.

Outputs **one row per canonical food**: all legacy lines that map to the same
canonical name are merged (median for numeric fields, mode for processing_level).
Row count is typically ~1100 (not 2000); this matches “one apple”, one acorn squash,
no separate lines per boil/steam/pickle prep unless canonicalize keeps a distinct form.

Also writes canonical_checklist_slice.csv and prints duplicate diagnostics.
"""

from __future__ import annotations

import csv
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

LEGACY_NAME = "nutrition_data_legacy.csv"
OUT_NAME = "nutrition_data.csv"
SLICE_NAME = "canonical_checklist_slice.csv"

# Whole-word tokens removed anywhere in the name (category noise).
_CATEGORY_TOKENS = (
    "cruciferous",
    "leafy green",
    "root vegetable",
)

# Suffix prep tokens removed from the end only.
_PREP_SUFFIXES = (
    "al dente",
    "overcooked",
    "pan-seared",
    "boiled",
    "steamed",
    "roasted",
    "sauteed",
    "grilled",
    "baked",
    "braised",
    "poached",
    "smoked",
    "stewed",
    "chilled",
    "pureed",
    "cooked",
    "sliced",
    "crispy",
    "stale",
    "fresh",
    "homemade",
    "plain",
    "salted",
    "frozen",
    "pickled",
)

_APPLE_CULTIVAR = re.compile(
    r"^(granny smith|fuji|gala|honeycrisp|golden delicious|red delicious|pink lady|mcintosh|green)\s+apple\b",
    re.I,
)

_ORANGE_PREFIX = re.compile(r"^valencia\s+orange\b", re.I)
_GRAPE_PREFIX = re.compile(r"^(black|green|red|white|purple|concord)\s+grape\b", re.I)
_ORANGE_VARIETY_PREFIX = re.compile(r"^(navel|blood|mandarin|clementine|tangerine)\s+orange\b", re.I)
_MELON_VARIETY_PREFIX = re.compile(r"^(cantaloupe|honeydew|crenshaw)\s+melon\b", re.I)
_TOMATO_VARIETY_PREFIX = re.compile(r"^(roma|cherry|beefsteak|heirloom|plum)\s+tomato\b", re.I)
_ONION_VARIETY_PREFIX = re.compile(r"^(red|white|yellow|sweet|shallot|leek|scallion)\s+onion\b", re.I)
_BELL_PEPPER_PREFIX = re.compile(r"^bell\s+(red|green|yellow|orange)\s+pepper\b", re.I)

_FLOAT_FIELDS = (
    "glycemic_index",
    "carbohydrates",
    "fiber",
    "protein",
    "fat",
    "serving_size_grams",
)

# Canonical produce names that should always be marked as whole.
_FORCE_WHOLE_CANONICAL = frozenset(
    {
        "tomato",
        "onion",
        "bell pepper",
        "apple",
        "grape",
        "orange",
        "melon",
        "watermelon",
    }
)

# ~95 universal / demo-friendly names — rows pulled from curated output by exact or best match.
CHECKLIST_SLICE: Tuple[str, ...] = (
    "apple",
    "banana",
    "orange",
    "grape",
    "raisin",
    "strawberry",
    "blueberry",
    "watermelon",
    "lettuce",
    "tomato",
    "cucumber",
    "carrot",
    "broccoli",
    "spinach",
    "onion",
    "bell pepper",
    "potato",
    "sweet potato",
    "white rice",
    "brown rice",
    "pasta",
    "oatmeal",
    "bread",
    "tortilla",
    "quinoa",
    "black beans",
    "chickpea",
    "lentils",
    "chicken breast",
    "ground beef",
    "salmon",
    "egg",
    "tofu",
    "milk",
    "yogurt",
    "cheddar cheese",
    "butter",
    "olive oil",
    "peanut butter",
    "almond",
    "walnut",
    "honey",
    "sugar",
    "cabbage",
    "cauliflower",
    "mushroom",
    "zucchini",
    "rice",
    "corn",
    "peas",
    "green beans",
    "asparagus",
    "kale",
    "avocado",
    "pineapple",
    "mango",
    "pear",
    "cherry",
    "lime",
    "lemon",
    "coffee",
    "tea",
    "orange juice",
    "soda",
    "beer",
    "wine",
    "potato chips",
    "ice cream",
    "chocolate",
    "cookie",
    "pizza",
    "burger",
    "soup",
    "oat",
    "bagel",
    "croissant",
    "pancake",
    "waffle",
    "cereal",
    "mayonnaise",
    "ketchup",
    "mustard",
    "vinegar",
    "soy sauce",
    "hot sauce",
    "cottage cheese",
    "cream cheese",
    "mozzarella",
    "turkey",
    "pork",
    "bacon",
    "ham",
    "shrimp",
    "tuna",
    "beans",
)


def _norm_ws(s: str) -> str:
    return " ".join(s.lower().strip().split())


def _strip_prep_suffixes(name: str) -> str:
    n = name
    changed = True
    while changed:
        changed = False
        for p in sorted(_PREP_SUFFIXES, key=len, reverse=True):
            suf = " " + p
            if n.endswith(suf):
                n = n[: -len(suf)].strip()
                changed = True
                break
    return n


def _strip_categories(name: str) -> str:
    n = name
    for tok in _CATEGORY_TOKENS:
        n = n.replace(tok, " ")
    return " ".join(n.split())


def _fix_berry_bean(name: str) -> str:
    n = name
    n = re.sub(r"\b(\w+berry)\s+berry\b", r"\1", n, flags=re.I)
    n = re.sub(r"\bchickpea\s+bean\b", "chickpea", n, flags=re.I)
    n = re.sub(r"\bgarbanzo\s+bean\b", "garbanzo", n, flags=re.I)
    return " ".join(n.split())


def _apple_cultivar(name: str) -> str:
    return _APPLE_CULTIVAR.sub("apple", name, count=1).strip()


def _orange_valencia(name: str) -> str:
    return _ORANGE_PREFIX.sub("orange", name, count=1).strip()


def _fruit_variety_to_canonical(name: str) -> str:
    n = name
    n = _GRAPE_PREFIX.sub("grape", n, count=1)
    n = _ORANGE_VARIETY_PREFIX.sub("orange", n, count=1)
    n = _MELON_VARIETY_PREFIX.sub("melon", n, count=1)
    # Keep watermelon distinct from other melons.
    n = re.sub(r"^watermelon\s+melon\b", "watermelon", n, flags=re.I)
    # Canonicalize common tomato varieties, but keep "sun-dried tomato" separate.
    if "tomato" in n and "sun-dried" in n:
        # Covers cases like "cherry tomato sun-dried" and "heirloom tomato sun-dried".
        n = re.sub(r"^.*\btomato\b.*sun-dried.*$", "sun-dried tomato", n, flags=re.I)
    else:
        n = _TOMATO_VARIETY_PREFIX.sub("tomato", n, count=1)

    # Canonicalize onion varieties (you asked for one `onion` row).
    n = _ONION_VARIETY_PREFIX.sub("onion", n, count=1)

    # Canonicalize bell pepper color variants into `bell pepper`.
    n = _BELL_PEPPER_PREFIX.sub("bell pepper", n, count=1)
    return n.strip()


def _normalize_user_requested_generalizations(name: str) -> str:
    n = name

    # Keep product distinctions the user still wants.
    if n.startswith("coffee ice cream"):
        return n

    # Coffee: collapse regular/decaf + hot/iced, but KEEP add-ins.
    # Desired outputs include: coffee, coffee with milk, coffee with cream, coffee with sugar.
    if "coffee" in n:
        if "with cream" in n:
            return "coffee with cream"
        if "with milk" in n:
            return "coffee with milk"
        if "with sugar" in n:
            return "coffee with sugar"
        return "coffee"

    # Soup: do not differentiate canned vs not canned.
    n = re.sub(r"\bsoup\s+canned\b", "soup", n, flags=re.I)

    # Spring roll: do not differentiate fried vs fresh.
    if "spring roll" in n:
        n = re.sub(r"\s+(fried|fresh)\b", "", n, flags=re.I)
        n = " ".join(n.split())

    # Tortilla chips: do not differentiate fried/baked/plain/salted.
    if n.startswith("tortilla chips"):
        return "tortilla chips"

    # Egg: keep cooking method, but collapse egg type labels.
    # e.g. whole egg -> egg, white egg -> egg, boiled egg -> boiled egg.
    if re.match(r"^(whole|white|yolk)\s+egg\b", n):
        return "egg"
    if n in ("egg", "boiled egg", "fried egg", "scrambled egg"):
        return n

    # Potato: canonicalize to potato / potato fried / potato mashed.
    # Keep sweet potato distinct. Keep potato chips as separate snack class.
    if "potato" in n and "sweet potato" not in n and "potato chips" not in n and "potato salad" not in n:
        if "mashed" in n:
            return "potato mashed"
        if "fried" in n:
            return "potato fried"
        return "potato"

    return n


def canonicalize(raw: str) -> str:
    n = _norm_ws(raw)
    n = _strip_categories(n)
    n = _apple_cultivar(n)
    n = _orange_valencia(n)
    n = _fruit_variety_to_canonical(n)
    n = _normalize_user_requested_generalizations(n)
    n = _fix_berry_bean(n)
    n = _strip_prep_suffixes(n)
    return " ".join(n.split())


def _merge_group(name: str, group: List[Dict[str, str]]) -> Dict[str, str]:
    def fvals(key: str) -> List[float]:
        vals = []
        for r in group:
            v = r.get(key)
            if v is not None and str(v).strip() != "":
                vals.append(float(v))
        return vals

    row: Dict[str, str] = {"name": name}
    for k in _FLOAT_FIELDS:
        nums = fvals(k)
        row[k] = str(round(statistics.median(nums), 6)) if nums else ""

    levels = [r.get("processing_level", "") for r in group if r.get("processing_level")]
    row["processing_level"] = Counter(levels).most_common(1)[0][0] if levels else ""
    if name in _FORCE_WHOLE_CANONICAL:
        row["processing_level"] = "whole"
    return row


def build_merged_rows_only(legacy_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    buckets: Dict[str, List[Dict[str, str]]] = {}
    for row in legacy_rows:
        key = canonicalize(row["name"])
        if not key:
            key = _norm_ws(row["name"])
        buckets.setdefault(key, []).append(row)

    return [_merge_group(canon, buckets[canon]) for canon in sorted(buckets.keys())]


def write_csv(path: Path, rows: Sequence[Dict[str, str]]) -> None:
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
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def duplicate_report(rows: Sequence[Dict[str, str]]) -> Tuple[int, List[Tuple[str, int]]]:
    names = [r["name"] for r in rows]
    c = Counter(names)
    dups = [(n, k) for n, k in c.items() if k > 1]
    return len(dups), sorted(dups, key=lambda x: -x[1])


def _checklist_match_score(want: str, key: str) -> int:
    if key == want:
        return 100
    if key.startswith(want + " "):
        return 85
    if key.endswith(" " + want):
        return 85
    if want in key.split():
        return 70
    if want in key:
        return 25
    return 0


def build_checklist_slice(by_name: Dict[str, Dict[str, str]]) -> List[Dict[str, str]]:
    slice_rows: List[Dict[str, str]] = []
    for want in CHECKLIST_SLICE:
        if want in by_name:
            slice_rows.append(dict(by_name[want]))
            continue
        ranked = sorted(
            by_name.keys(),
            key=lambda k: (-_checklist_match_score(want, k), len(k)),
        )
        best = ranked[0] if ranked and _checklist_match_score(want, ranked[0]) >= 70 else None
        if best:
            row = dict(by_name[best])
            row["name"] = want
            slice_rows.append(row)
        else:
            slice_rows.append(
                {
                    "name": want,
                    "glycemic_index": "",
                    "carbohydrates": "",
                    "fiber": "",
                    "protein": "",
                    "fat": "",
                    "processing_level": "",
                    "serving_size_grams": "",
                }
            )
    return slice_rows


def main() -> None:
    base = Path(__file__).resolve().parent
    legacy_path = base / LEGACY_NAME
    if not legacy_path.is_file():
        raise SystemExit(f"Missing {legacy_path}")

    with legacy_path.open(encoding="utf-8") as f:
        legacy_rows = list(csv.DictReader(f))

    merged = build_merged_rows_only(legacy_rows)
    by_name = {r["name"]: r for r in merged}

    write_csv(base / OUT_NAME, merged)
    write_csv(base / SLICE_NAME, build_checklist_slice(by_name))

    ndup, dup_list = duplicate_report(merged)
    print(f"Legacy rows: {len(legacy_rows)}")
    print(f"Curated rows (merged only): {len(merged)}")
    print(f"Duplicate names in output: {ndup}")
    if dup_list:
        for n, k in dup_list[:20]:
            print(f"  {k}x  {n}")
    print(f"Wrote {base / OUT_NAME}")
    print(f"Wrote {base / SLICE_NAME} ({len(CHECKLIST_SLICE)} checklist foods)")


if __name__ == "__main__":
    main()
