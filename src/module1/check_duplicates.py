#!/usr/bin/env python3
"""Check for duplicate food names in nutrition_data.csv"""
import csv
from collections import Counter

with open('nutrition_data.csv', 'r') as f:
    rows = list(csv.DictReader(f))

names = [r['name'] for r in rows]
counts = Counter(names)
dups = {n: c for n, c in counts.items() if c > 1}

print(f"Total rows: {len(rows)}")
print(f"Unique names: {len(counts)}")
print(f"Names that appear more than once: {len(dups)}")
print(f"Rows that are duplicates (by name): {sum(c for c in counts.values() if c > 1)}")
print("\nTop 20 most repeated names:")
for name, count in sorted(dups.items(), key=lambda x: -x[1])[:20]:
    print(f"  {count:2d}x  {name}")
