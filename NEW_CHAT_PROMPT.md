# Context Prompt — Tile Recommendation Engine (Material Depot)

You are picking up work on an existing tile recommendation engine. Read all the context
below carefully. It reflects the **current, working state** of the code (already tested and
in use). After this context I will give you the actual task in my next message.

---

## 1. What the project is

A recommendation engine for Material Depot tiles. Given an input tile (a "variant"), it
generates lists of complementary tiles to show on the product page, split by room
(bathroom / kitchen) and by placement within the room (floor / base wall / highlighter /
backsplash). Pairings are driven by a category pairing table and by color-matching logic.

## 2. Architecture / pipeline

```
variants.csv ─┐
variant_colors.csv ─┤
shade_pairs_recommendation.csv ─┼─► generate_recommendations.py ─► recommendations.csv
family_pairs_recommendation.csv ─┤                                        │
application_image_tags.csv ─┘                                             ▼
                                                       api.py (FastAPI) ─► frontend.html
```

- **`generate_recommendations.py`** — batch script. Loads the CSVs, builds candidate
  pools, generates grouped recommendations for every active variant, writes
  `recommendations.csv`. Run locally by the user: `python generate_recommendations.py`
  (~2.5–3 min for ~14,505 active variants; too slow to fully run in a sandbox).
- **`api.py`** — FastAPI app (`python -m uvicorn api:app --reload`). Serves
  `frontend.html` at `/`, plus `/variant/{handle}`, `/variants/search`,
  `/recommendations/{handle}`, `/recommendations/batch`. It caches the CSV with
  `@lru_cache`, so **after regenerating you must fully restart uvicorn** (a --reload code
  restart is not enough — it must re-read the CSV on a fresh process start).
- **`frontend.html`** — single-file tester + product widget. Reads the grouped API
  response and renders one sub-tab per non-empty placement group.

## 3. `recommendations.csv` format (8 columns)

```
input_variant_handle, input_category, eligible_rooms,
bathroom_floor, bathroom_base, bathroom_highlighter,
kitchen_floor, kitchen_backsplash
```

Each of the five recommendation columns is a JSON list of variant handles. (The old
`bathroom_recommendations` / `kitchen_recommendations` flat columns and the
`*_count` columns no longer exist.)

## 4. Input groups — `get_input_group(category, application_type)`

Every input tile is mapped to one input group:

- `moroccan` → `wall_moroccan`
- `monochrome` → `floor_monochrome`
- `decor` / `tropical` / `floral` (Set A) → `wall_set_a`
- `subway` / `subway look` → `wall_subway`
- `mosaic` → `wall_mosaic`
- `geometric` → `wall_geometric`
- other wall/highlighter categories (incl. `highlighter`) → `wall_other`
- `marble` / `endless` → `floor_marble` if application_type is floor/both, else `wall_other`
- `rustic` → `floor_rustic` if floor/both, else `wall_other`
- `wooden` → `floor_wooden`
- `terrazzo` → `floor_terrazzo`
- everything else → `floor_other`

## 5. The pairing table — `PAIRING_TABLE`

Structure: `PAIRING_TABLE[input_group][room] = { placement_group: [(category, count), ...] }`.
The placement-group key **is** the pool placement each category is drawn from, and is also
the bucket the recs are stored/displayed under (no guessing).

- Bathroom placement groups: `floor`, `base`, `highlighter`
- Kitchen placement groups: `floor`, `backsplash`

Current contents:

```
floor_marble:    bathroom {highlighter:[subway6,tropical2,floral1], base:[plain4]}
                 kitchen  {backsplash:[subway4,moroccan2,highlighter2,4x2_any2]}
floor_rustic:    bathroom {highlighter:[subway4,tropical2,floral2], base:[plain4]}
                 kitchen  {backsplash:[subway4,moroccan2,4x2_plain2,4x2_marble_endless2]}
floor_terrazzo:  bathroom {highlighter:[subway6,tropical1,floral1], base:[plain4]}
                 kitchen  None
floor_wooden:    bathroom {highlighter:[subway4,tropical3,floral1], base:[plain4]}
                 kitchen  {backsplash:[subway6,highlighter2,4x2_marble_endless2]}
floor_monochrome:bathroom {highlighter:[subway6], base:[plain5], floor:[plain5]}
                 kitchen  {floor:[plain4,marble_endless4], backsplash:[subway6]}
floor_other:     bathroom {highlighter:[subway4,tropical1,floral1,decor1], base:[base_mix4]}
                 kitchen  {backsplash:[subway4,moroccan2,highlighter2,4x2_any2]}
wall_set_a:      bathroom {floor:[plain3,rustic1,terrazzo1,wooden2], base:[marble3,terrazzo3]}
                 kitchen  {floor:[marble3,plain3,endless3,rustic1]}
wall_moroccan:   bathroom {floor:[plain5], base:[plain4,marble2], highlighter:[subway6]}
                 kitchen  {floor:[marble_endless3,plain3,rustic2], backsplash:[subway6]}
wall_geometric:  bathroom {floor:[plain5,rustic2], base:[marble_endless4]}
                 kitchen  {floor:[plain4,marble_endless4,rustic2]}
wall_subway:     bathroom {floor:[plain3,terrazzo3,rustic2], base:[marble_endless3,terrazzo3]}
                 kitchen  {floor:[marble_endless5,rustic2,plain3]}
wall_mosaic:     bathroom {floor:[plain3,rustic2], base:[marble2,terrazzo3]}
                 kitchen  None
wall_other:      bathroom {floor:[plain3,terrazzo2,rustic2], base:[marble3,terrazzo2]}
                 kitchen  {floor:[plain3,marble_endless5,rustic2]}
```

Compound category keys handled by `resolve_pool(cat, room, placement, pool_index)`:
- `marble_endless` → merged marble + endless pools at that placement
- `base_mix` → merged plain + rustic + marble + terrazzo at that placement
- `4x2_any` / `4x2_plain` / `4x2_marble_endless` → glossy 1200×600 kitchen-backsplash pools
- `travertino` → bathroom base pool (capped per tile)
- `subway` → auto-split 50/50 between `subway` and `subway look` (see rules)

## 6. Generation rules (all currently implemented and verified)

**Color matching (non-moroccan, non-monochrome):**
- `get_top_shades()` builds the preferred-shade list **shade-first** (from
  `shade_pairs` for the input's primary/secondary/tertiary shades) **then family-wise**
  (from tier-weighted `family_pairs`).
- **Max 2 recommendations per color family per category slot** (`DEFAULT_FAMILY_CAP = 2`;
  Brown and Black capped at 1). NOTE: the cap is enforced **per category slot, not per
  whole room** (deliberate choice, so rare-family tiles don't get pre-exhausted).
- The input's own shade is excluded from its non-moroccan recs.

**Moroccan (`wall_moroccan`):** same-color pairing. Recs are hard-filtered to the input
shade's own neighbourhood via `MOROCCAN_SHADE_NEIGHBORS` (input shade + 1–3 closest
neighbours, e.g. White → White/Light Beige/Light Grey). The White→Navy-Blue subway
guarantee is **skipped** for moroccan.

**Monochrome (`floor_monochrome`):** ignores normal color pairing.
- Plain picks (bathroom Floor + Base, kitchen Floor — incl. `marble_endless`) come from
  the **White and Grey families ONLY** (`MONO_PLAIN_FAMILIES = ["White","Grey"]`; the
  entire Beige family is excluded).
- Subway picks follow `MONO_SUBWAY_DIST = White2, Black2, Blue1, Green1` (6 tiles), and
  are also 50/50 subway vs subway-look.

**Subway 50/50:** any `("subway", n)` slot yields n/2 `subway` + n/2 `subway look`
(counts are kept even for this reason).

**Glossy rules:**
- A recommended tile is rejected at **floor placement in the BATHROOM only**
  (slippery underfoot). Kitchen floor allows glossy; base/highlighter/backsplash allow
  glossy in both rooms.
- In `eligible_rooms()`: glossy disqualifies a tile from the bathroom **only when it is a
  floor-type input**. Glossy **wall** inputs (subway, moroccan, geometric, mosaic,
  highlighter, …) still get bathroom recs if their application lists Bathroom.

**Bathroom plain-floor strict rule** (in `passes_placement_constraint`): a plain tile in
the bathroom floor pool must (a) list **Bathroom** in its application (generic "other"
does NOT qualify), (b) be **non-glossy**, (c) have **both dimensions ≤ 600mm**.

**Wall-type moroccan/monochrome:** if `application_type == "wall"`, the subway groups
(bathroom `highlighter`, kitchen `backsplash`) are dropped — a wall tile can't go on a
wall as a highlighter/backsplash here — leaving Floor + Base populated.

**Cross-room overlap:** `enforce_overlap()` caps tiles appearing in both rooms at
`MAX_OVERLAP = 4`; excess overlapping tiles are removed from their kitchen group and that
group is backfilled with non-overlapping tiles.

## 7. API response shape

`GET /recommendations/{handle}?limit=20` returns:
```json
{
  "input_variant_handle": "...",
  "input_category": "...",
  "eligible_rooms": ["bathroom","kitchen"],
  "bathroom": {"floor": [...], "base": [...], "highlighter": [...]},
  "kitchen":  {"floor": [...], "backsplash": [...]}
}
```
`limit` (default/max 20) is applied **per group**. The batch endpoint mirrors this shape.

## 8. Frontend

`frontend.html` reads the grouped object straight from the API. `GROUP_DEFS` defines the
display order/labels: bathroom = Floor, Base, Highlighter; kitchen = Floor, Backsplash.
It renders one sub-tab per non-empty group — no category/application_type guessing.

## 9. Key files & important operational notes

- Files live in the project folder alongside this prompt: `generate_recommendations.py`,
  `api.py`, `frontend.html`, the 5 input CSVs, `recommendations.csv`, and
  `analyze_coverage.py` (a coverage report: counts variants generating no recs / never
  recommended; run after regenerating).
- **Sandbox caveat:** a connected sandbox/mount can serve a stale copy of recently-edited
  files. Treat the editor's view of files as ground truth, and validate logic with small
  self-contained harnesses rather than trusting the mount.
- After ANY change to `generate_recommendations.py`: the user must re-run it locally and
  fully restart uvicorn before the change is visible (CSV is lru_cached).

---

## Next steps

The above is context only. **I will describe the actual task — adding a new tile category
to this engine — in my next message.** Do not start changing anything yet; wait for that
task description, then ask any clarifying questions before implementing.
