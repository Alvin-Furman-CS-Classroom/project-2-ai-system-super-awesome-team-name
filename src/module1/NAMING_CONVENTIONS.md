# Knowledge base food naming (CSV `name` column)

Conventions for `nutrition_data.csv` when curating or extending the hybrid knowledge base.

## Lowercase

- Use **lowercase only** in the `name` field (e.g. `white rice`, not `White Rice`).
- Module 1 normalizes lookups to lowercase; matching the CSV keeps diffs and reviews predictable.

## Default preparation: cooked when raw is not normal

- For foods that are **not normally eaten raw** in everyday use, assume the **cooked (or otherwise ready-to-eat) form** and **do not** put `cooked` in the name.
- **Examples:** `white rice`, `brown rice`, `pasta`, `black beans`, `oatmeal`, `ground beef` — not `white rice cooked`, `pasta cooked`, etc.
- For foods **commonly eaten both raw and cooked** with very different nutrition, you may use **two rows** only if you need both behaviors (e.g. `potato` vs `potato chips`); otherwise one canonical row is enough.

## Dried vs fresh (and similar): keep separate rows

- When **dried / dehydrated / canned-in-syrup** versions differ materially from **fresh** for carbs and glycemic impact, use **separate `name` values** (e.g. `grape` vs `raisin`, `plum` vs `prune`).
- Apply the same idea where it matters for your advisor (e.g. fresh fruit vs dried fruit, not every minor prep adjective).

## Varieties: generalize

- **Do not** list separate rows per cultivar, brand, or minor variant when they are the same food type for advice (e.g. one `apple`, not `granny smith apple`, `fuji apple`, …).
- Merge redundant prep variants into one canonical name where they do not change the glycemic story (see “cooked” rule above).
- The curation script also strips **`pickled`** as a trailing prep token when rebuilding `nutrition_data.csv`, so items like acorn squash prepared different ways collapse to **one** `acorn squash` row (median nutrition). Keep separate rows when the product is materially different (e.g. `grape` vs `raisin`).

## Quick reference

| Rule | Do | Don’t |
|------|-----|--------|
| Casing | `chicken breast` | `Chicken Breast` |
| Normal prep | `quinoa` | `quinoa cooked` |
| Dried vs fresh | `grape`, `raisin` | one row for both |
| Varieties | `apple` | `honeycrisp apple`, `gala apple` |
