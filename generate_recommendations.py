"""
Recommendation Engine - Batch Generation Script
"""
import csv, json, random
from collections import defaultdict

VARIANTS_FILE       = "variants.csv"
VARIANT_COLORS_FILE = "variant_colors.csv"
SHADE_PAIRS_FILE    = "shade_pairs_recommendation.csv"
FAMILY_PAIRS_FILE   = "family_pairs_recommendation.csv"
IMAGE_TAGS_FILE     = "application_image_tags.csv"
OUTPUT_FILE         = "recommendations.csv"

GLOBAL_CAP = 10

SHADE_TO_FAMILY = {
    "White": "White",
    "Light Grey": "Grey", "Medium Grey": "Grey", "Dark Grey": "Grey",
    "Black": "Black",
    "Ivory": "Beige", "Cream": "Beige", "Light Beige": "Beige", "Warm Beige": "Beige",
    "Tan": "Brown", "Warm Brown": "Brown", "Dark Brown": "Brown",
    "Aqua": "Blue", "Sky Blue": "Blue", "Blue": "Blue",
    "Navy Blue": "Blue", "Teal": "Blue", "Dark Teal": "Blue",
    "Light Green": "Green", "Green": "Green", "Dark Green": "Green",
    "Cream Yellow": "Yellow", "Yellow": "Yellow", "Mustard": "Yellow",
    "Orange": "Orange", "Burnt Orange": "Orange", "Peach": "Orange",
    "Red": "Red", "Dark Red": "Red",
    "Light Pink": "Pink", "Pink": "Pink", "Rose": "Pink",
    "Lavender": "Purple", "Purple": "Purple", "Dark Purple": "Purple",
    "Multicolor": "Multicolor",
}

FAMILY_TO_SHADES = defaultdict(list)
for _s, _f in SHADE_TO_FAMILY.items():
    FAMILY_TO_SHADES[_f].append(_s)

# Moroccan same-base-colour pairing: each shade only pairs with itself and its
# 1-2 closest neighbouring shades (e.g. White -> White, Light Beige, Light Grey —
# NOT Dark Grey or other far shades).
MOROCCAN_SHADE_NEIGHBORS = {
    "White":       ["White", "Light Beige", "Light Grey"],
    "Ivory":       ["Ivory", "Light Beige", "White"],
    "Cream":       ["Cream", "Light Beige", "Warm Beige"],
    "Light Beige": ["Light Beige", "White", "Ivory", "Cream"],
    "Warm Beige":  ["Warm Beige", "Cream", "Tan"],
    "Tan":         ["Tan", "Warm Beige", "Warm Brown"],
    "Warm Brown":  ["Warm Brown", "Tan", "Dark Brown"],
    "Dark Brown":  ["Dark Brown", "Warm Brown", "Black"],
    "Light Grey":  ["Light Grey", "White", "Medium Grey"],
    "Medium Grey": ["Medium Grey", "Light Grey", "Dark Grey"],
    "Dark Grey":   ["Dark Grey", "Medium Grey", "Black"],
    "Black":       ["Black", "Dark Grey", "Dark Brown"],
    "Aqua":        ["Aqua", "Sky Blue", "Teal"],
    "Sky Blue":    ["Sky Blue", "Aqua", "Blue"],
    "Blue":        ["Blue", "Sky Blue", "Navy Blue"],
    "Navy Blue":   ["Navy Blue", "Blue", "Dark Teal"],
    "Teal":        ["Teal", "Aqua", "Dark Teal"],
    "Dark Teal":   ["Dark Teal", "Teal", "Navy Blue"],
    "Light Green": ["Light Green", "Green", "Aqua"],
    "Green":       ["Green", "Light Green", "Dark Green"],
    "Dark Green":  ["Dark Green", "Green", "Dark Teal"],
    "Cream Yellow":["Cream Yellow", "Yellow", "Light Beige"],
    "Yellow":      ["Yellow", "Cream Yellow", "Mustard"],
    "Mustard":     ["Mustard", "Yellow", "Tan"],
    "Peach":       ["Peach", "Orange", "Light Pink"],
    "Orange":      ["Orange", "Peach", "Burnt Orange"],
    "Burnt Orange":["Burnt Orange", "Orange", "Dark Red"],
    "Red":         ["Red", "Dark Red", "Burnt Orange"],
    "Dark Red":    ["Dark Red", "Red", "Burnt Orange"],
    "Light Pink":  ["Light Pink", "Pink", "Peach"],
    "Pink":        ["Pink", "Light Pink", "Rose"],
    "Rose":        ["Rose", "Pink", "Lavender"],
    "Lavender":    ["Lavender", "Rose", "Purple"],
    "Purple":      ["Purple", "Lavender", "Dark Purple"],
    "Dark Purple": ["Dark Purple", "Purple", "Black"],
    "Multicolor":  ["Multicolor"],
}


def get_moroccan_shades(input_shade):
    """Return the input's own shade plus its 1-2 closest neighbouring shades."""
    return MOROCCAN_SHADE_NEIGHBORS.get(input_shade, [input_shade] if input_shade else [])

FAMILY_CAPS = {"Brown": 1, "Black": 1}
DEFAULT_FAMILY_CAP = 2

FAMILY_PAIR_TIERS = {
    frozenset(["Beige", "Grey"]): 10, frozenset(["Grey", "Brown"]): 10,
    frozenset(["Beige", "Brown"]): 10, frozenset(["Grey", "Green"]): 10,
    frozenset(["Beige", "Green"]): 10, frozenset(["White", "Grey"]): 9,
    frozenset(["White", "Green"]): 9, frozenset(["Blue", "White"]): 9,
    frozenset(["Blue", "Grey"]): 9, frozenset(["Beige", "Blue"]): 8,
    frozenset(["Brown", "Green"]): 8, frozenset(["Black", "Beige"]): 8,
    frozenset(["Black", "White"]): 0, frozenset(["Blue", "Brown"]): 8,
    frozenset(["Black", "Grey"]): 7, frozenset(["White", "Brown"]): 7,
    frozenset(["Beige", "White"]): 7,
    frozenset(["Green", "Black"]): 0, frozenset(["Brown", "Black"]): 0,
    frozenset(["Blue", "Black"]): 0, frozenset(["Grey", "Yellow"]): 0,
    frozenset(["Grey", "Orange"]): 0, frozenset(["Grey", "Red"]): 0,
    frozenset(["Brown", "Red"]): 0, frozenset(["Yellow", "Blue"]): 0,
    frozenset(["Orange", "Blue"]): 0, frozenset(["Purple", "Grey"]): 0,
    frozenset(["Purple", "Brown"]): 0,
}
DEFAULT_TIER_WEIGHT = 5

# Glossy finishes — tiles with these finishes are excluded from bathroom floor pools
GLOSSY_FINISHES = {
    "super high gloss", "high glossy", "high gloss", "glossy",
    "carving glossy", "carving high gloss", "carving high-gloss",
}

# ── Outdoor spaces ──────────────────────────────────────────────────────────────
# A tile is eligible for outdoor recommendations only if its application list
# contains at least one of these (case-insensitive substring match).
OUTDOOR_KEYWORDS = ("terrace", "parking", "balcony")

# Finishes that mark a tile as a "punch finish" tile (used on outdoor walls).
PUNCH_FINISHES = {"punch", "punch matte", "punch carving matte", "punch glossy"}

# Outdoor recommendation counts:
#   - a parking-floor input recommends wall tiles: 5 elevation + 5 punch
#   - an elevation / punch (wall) input recommends 8 parking (floor) tiles
OUTDOOR_ELEVATION_N = 5
OUTDOOR_PUNCH_N     = 5
OUTDOOR_PARKING_N   = 8

# Fraction of each outdoor slot drawn as same-base-colour picks; the remainder
# follows the normal complementary colour-pairing logic.
OUTDOOR_SAME_COLOR_FRAC = 0.4

SET_A_CATEGORIES       = {"decor", "tropical", "floral"}
# Wall/highlighter categories treated as wall inputs regardless of application_type
WALL_INPUT_CATEGORIES  = {"highlighter", "decor", "floral", "tropical",
                           "subway", "subway look", "mosaic", "geometric"}
KITCHEN_EXCLUDED_INPUT = {"terrazzo", "mosaic"}
BATHROOM_SPECIAL_SIZES = {"1200x600", "600x1200"}
SIZE_4x2               = {"1200x600", "600x1200"}
MAX_OVERLAP = 4

# Travertino series: preferred for bathroom base but capped to avoid over-exposure
TRAVERTINO_CAP = 20

# ── Pairing table ─────────────────────────────────────────────────────────────
# Structure: PAIRING_TABLE[input_group][room] = { placement_group: [(cat, count), ...] }
#   Bathroom placement groups: "floor", "base", "highlighter"
#   Kitchen  placement groups: "floor", "backsplash"
# The placement-group key IS the pool placement each category is drawn from, and it
# is also the bucket the recommendations are stored/displayed under (no guessing).
#
# "subway" entries are auto-split 50/50 between "subway" and "subway look".
# Compound category keys:
#   marble_endless      → combined marble + endless pools
#   base_mix            → combined plain + rustic + marble + terrazzo (bathroom base variety)
#   4x2_any             → 1200x600 glossy tiles (any non-SET_A category) for kitchen backsplash
#   4x2_plain           → 1200x600 glossy plain tiles for kitchen backsplash
#   4x2_marble_endless  → 1200x600 glossy marble/endless tiles for kitchen backsplash

PAIRING_TABLE = {
    # ── Floor tile inputs ─────────────────────────────────────────────────────
    # Bathroom = Highlighter + Base; Kitchen = Backsplash.
    "floor_marble": {
        "bathroom": {"highlighter": [("subway", 6), ("tropical", 2), ("floral", 1)],
                     "base":        [("plain", 4)]},
        "kitchen":  {"backsplash":  [("subway", 4), ("moroccan", 2), ("highlighter", 2), ("4x2_any", 2)]},
    },
    "floor_rustic": {
        "bathroom": {"highlighter": [("subway", 4), ("tropical", 2), ("floral", 2)],
                     "base":        [("plain", 4)]},
        "kitchen":  {"backsplash":  [("subway", 4), ("moroccan", 2), ("4x2_plain", 2), ("4x2_marble_endless", 2)]},
    },
    "floor_terrazzo": {
        "bathroom": {"highlighter": [("subway", 6), ("tropical", 1), ("floral", 1)],
                     "base":        [("plain", 4)]},
        "kitchen":  None,
    },
    "floor_wooden": {
        "bathroom": {"highlighter": [("subway", 4), ("tropical", 3), ("floral", 1)],
                     "base":        [("plain", 4)]},
        "kitchen":  {"backsplash":  [("subway", 6), ("highlighter", 2), ("4x2_marble_endless", 2)]},
    },
    "floor_monochrome": {
        # Bathroom: Highlighter = 6 subway (black/white/blue/green); Base = 5 plain and
        #           Floor = 5 plain, both beige/grey/white. Kitchen: Floor = 4 plain +
        #           4 marble/endless; Backsplash = 6 subway. For wall-type monochrome
        #           inputs the subway (highlighter/backsplash) group is stripped.
        "bathroom": {"highlighter": [("subway", 6)],
                     "base":        [("plain", 5)],
                     "floor":       [("plain", 5)]},
        "kitchen":  {"floor":       [("plain", 4), ("marble_endless", 4)],
                     "backsplash":  [("subway", 6)]},
    },
    "floor_other": {
        "bathroom": {"highlighter": [("subway", 4), ("tropical", 1), ("floral", 1), ("decor", 1)],
                     "base":        [("base_mix", 4)]},
        "kitchen":  {"backsplash":  [("subway", 4), ("moroccan", 2), ("highlighter", 2), ("4x2_any", 2)]},
    },
    # ── Wall / Highlighter inputs ─────────────────────────────────────────────
    # Bathroom = Floor + Base (+ Highlighter for moroccan); Kitchen = Floor (+ Backsplash for moroccan).
    "wall_set_a": {
        "bathroom": {"floor": [("plain", 3), ("rustic", 1), ("terrazzo", 1), ("wooden", 2)],
                     "base":  [("marble", 3), ("terrazzo", 3)]},
        "kitchen":  {"floor": [("marble", 3), ("plain", 3), ("endless", 3), ("rustic", 1)]},
    },
    "wall_moroccan": {
        # Same-colour pairing (top_shades = get_moroccan_shades in main).
        "bathroom": {"floor":       [("plain", 5)],
                     "base":        [("plain", 4), ("marble", 2)],
                     "highlighter": [("subway", 6)]},
        "kitchen":  {"floor":       [("marble_endless", 3), ("plain", 3), ("rustic", 2)],
                     "backsplash":  [("subway", 6)]},
    },
    "wall_geometric": {
        "bathroom": {"floor": [("plain", 5), ("rustic", 2)],
                     "base":  [("marble_endless", 4)]},
        "kitchen":  {"floor": [("plain", 4), ("marble_endless", 4), ("rustic", 2)]},
    },
    "wall_subway": {
        "bathroom": {"floor": [("plain", 3), ("terrazzo", 3), ("rustic", 2)],
                     "base":  [("marble_endless", 3), ("terrazzo", 3)]},
        "kitchen":  {"floor": [("marble_endless", 5), ("rustic", 2), ("plain", 3)]},
    },
    "wall_mosaic": {
        # Not in the spec table — kept on its own mapping; split plain/rustic -> Floor,
        # marble/terrazzo -> Base to mirror the other wall inputs.
        "bathroom": {"floor": [("plain", 3), ("rustic", 2)],
                     "base":  [("marble", 2), ("terrazzo", 3)]},
        "kitchen":  None,
    },
    "wall_other": {
        "bathroom": {"floor": [("plain", 3), ("terrazzo", 2), ("rustic", 2)],
                     "base":  [("marble", 3), ("terrazzo", 2)]},
        "kitchen":  {"floor": [("plain", 3), ("marble_endless", 5), ("rustic", 2)]},
    },
}

# Placement group → the pool placement to draw from. Group names already match
# placement names, so this is identity, but kept explicit for clarity.
BATHROOM_GROUPS = ("floor", "base", "highlighter")
KITCHEN_GROUPS  = ("floor", "backsplash")


# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_list_field(value):
    value = value.strip()
    if not value: return []
    if value.startswith("["):
        inner = value.strip("[]")
        parts = [p.strip().strip('"').strip("'") for p in inner.split('"') if p.strip().strip('"').strip("'")]
        return [p for p in parts if p]
    return [value]

def parse_size(size_str):
    try:
        parts = size_str.lower().replace(" ", "").split("x")
        return int(parts[0]), int(parts[1])
    except: return 0, 0

def has_room(app_list, room): return any(room.lower() in a.lower() for a in app_list)
def is_other_app(app_raw):    return app_raw.strip().lower() == "other"
def is_glossy(finish_list):   return any(f.lower() in GLOSSY_FINISHES for f in finish_list)
def is_punch_finish(finish_list): return any(f.lower() in PUNCH_FINISHES for f in finish_list)

def is_outdoor_eligible(v):
    """A tile may take part in outdoor recommendations only if its application
    list mentions Terrace, Parking, or Balcony."""
    return any(k in a.lower() for a in v["application_list"] for k in OUTDOOR_KEYWORDS)

def outdoor_input_type(v):
    """Classify an input tile for outdoor recommendation generation.
      "parking_floor" → an outdoor floor tile (is_parking); recommends wall tiles
                        (5 elevation + 5 punch).
      "wall"          → an elevation tile or a punch-finish tile; recommends 8
                        parking (floor) tiles.
    is_parking takes precedence: a tile flagged is_parking is always treated as a
    parking floor input even if it also has a punch finish.
    Returns None if the tile is not an outdoor input type."""
    if v.get("is_parking"):
        return "parking_floor"
    if v["category"] == "elevation" or is_punch_finish(v["finish"]):
        return "wall"
    return None

def get_input_group(category, application_type=""):
    cat = category.lower()
    app = application_type.lower()

    # Moroccan always treated as wall input (same-color pairing)
    if cat == "moroccan":
        return "wall_moroccan"

    # Monochrome is its own floor input group
    if cat == "monochrome":
        return "floor_monochrome"

    # Explicit wall/highlighter categories
    if cat in SET_A_CATEGORIES:
        return "wall_set_a"
    if cat in ("subway", "subway look"):
        return "wall_subway"
    if cat == "mosaic":
        return "wall_mosaic"
    if cat == "geometric":
        return "wall_geometric"
    if cat in WALL_INPUT_CATEGORIES:  # highlighter + anything else listed
        return "wall_other"

    # Floor-dominant categories — check application_type to confirm floor usage
    if cat in ("marble", "endless"):
        return "floor_marble" if app in ("floor", "both") else "wall_other"
    if cat == "rustic":
        return "floor_rustic" if app in ("floor", "both") else "wall_other"
    if cat == "wooden":
        return "floor_wooden"   # wooden look always treated as floor input
    if cat == "terrazzo":
        return "floor_terrazzo"

    return "floor_other"


def get_placement(rec_cat, room, input_group):
    """Determine template region/placement for a recommended tile."""
    cat = rec_cat.lower()
    is_wall_input = input_group.startswith("wall_")
    if room == "bathroom":
        if is_wall_input: return "floor"
        if cat in ("highlighter", "decor", "floral", "tropical"): return "highlighter"
        return "base"
    else:  # kitchen
        if input_group == "wall_moroccan":
            if cat in ("subway", "subway look"): return "backsplash"
            return "floor"
        if input_group == "floor_monochrome":
            if cat in ("plain", "marble", "endless", "marble_endless"): return "floor"
            return "backsplash"
        if is_wall_input: return "floor"
        return "backsplash"


# ── Data loading ───────────────────────────────────────────────────────────────

def load_data():
    print("Loading variants...")
    variants = {}
    vid_to_handle = {}
    with open(VARIANTS_FILE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            vid = row["variant_id"].strip().replace(",", "")
            h   = row["variant_handle"].strip()
            vid_to_handle[vid] = h
            if (row.get("is_active") or "").strip().upper() != "TRUE": continue
            variants[h] = {
                "handle":           h,
                "application_raw":  row["application"].strip(),
                "application_list": parse_list_field(row["application"].strip()),
                "finish":           parse_list_field(row["finish"]),
                "size":             row["size"].strip(),
                "category":         row["category"].strip().lower(),
                "application_type": row["application_type"].strip().lower(),
                "is_parking":       (row.get("is_parking") or "").strip().upper() == "TRUE",
            }

    print("Loading variant colors...")
    vcolors = {}
    with open(VARIANT_COLORS_FILE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            h = row["variant_handle"].strip()
            vcolors[h] = {
                "primary_shade":   row["primary_color_shade"].strip(),
                "primary_family":  row["primary_color_family"].strip(),
                "secondary_shade": row.get("secondary_color_shade", "").strip(),
                "tertiary_shade":  row.get("tertiary_color_shade", "").strip(),
            }

    print("Loading shade pairs...")
    raw_shade = defaultdict(list)
    with open(SHADE_PAIRS_FILE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            a, b = row["color_1"].strip(), row["color_2"].strip()
            s = float(row["recommendation_score"])
            raw_shade[a].append((b, s)); raw_shade[b].append((a, s))
    shade_pairs = {k: [x[0] for x in sorted(v, key=lambda x: x[1], reverse=True)]
                   for k, v in raw_shade.items()}

    print("Loading family pairs (with tier weighting)...")
    raw_family = defaultdict(list)
    with open(FAMILY_PAIRS_FILE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            a, b = row["family_1"].strip(), row["family_2"].strip()
            s = float(row["recommendation_score"])
            pair  = frozenset([a, b])
            tier  = FAMILY_PAIR_TIERS.get(pair, DEFAULT_TIER_WEIGHT)
            if tier == 0: continue
            combined = tier * 1000 + s
            raw_family[a].append((b, combined)); raw_family[b].append((a, combined))
    all_families = set(FAMILY_TO_SHADES.keys())
    for pair, tier in FAMILY_PAIR_TIERS.items():
        if tier == 0: continue
        fl = list(pair)
        if len(fl) == 2:
            a, b = fl[0], fl[1]
            if b not in {x[0] for x in raw_family[a]} and b in all_families:
                raw_family[a].append((b, tier * 1000))
                raw_family[b].append((a, tier * 1000))
    family_pairs = {k: [x[0] for x in sorted(v, key=lambda x: x[1], reverse=True)]
                    for k, v in raw_family.items()}

    print("Loading inspiration gallery co-occurrences...")
    image_variants = defaultdict(list)
    with open(IMAGE_TAGS_FILE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            img_id = row["image_id"].strip().replace(",", "").replace('"', "")
            var_id = row["variant_id"].strip().replace(",", "").replace('"', "")
            handle = vid_to_handle.get(var_id)
            if handle and handle in variants:
                image_variants[img_id].append(handle)
    raw_co = defaultdict(lambda: defaultdict(int))
    for img_id, handles in image_variants.items():
        if len(handles) >= 2:
            for h1 in handles:
                for h2 in handles:
                    if h1 != h2: raw_co[h1][h2] += 1
    co_occur = {h: [x[0] for x in sorted(pairs.items(), key=lambda x: x[1], reverse=True)]
                for h, pairs in raw_co.items()}

    print(f"  {len(variants)} active variants | {len(vcolors)} color records | "
          f"{len(shade_pairs)} shade pair entries | {len(family_pairs)} family pair entries | "
          f"{len(co_occur)} handles with gallery co-occurrence data")
    return variants, vcolors, shade_pairs, family_pairs, co_occur


# ── Pool building ──────────────────────────────────────────────────────────────

def passes_placement_constraint(v, placement, room):
    app_type = v["application_type"]
    cat      = v["category"]
    size_str = v["size"]
    finish   = v["finish"]


    if placement == "floor":
        if app_type not in ("floor", "both"): return False
    elif placement == "4x2_backsplash":
        # Must be glossy, 1200x600, wall or both
        if app_type not in ("wall", "both"): return False
        if size_str not in SIZE_4x2: return False
        if not is_glossy(finish): return False
    else:  # base, highlighter, backsplash
        if app_type not in ("wall", "both"): return False

    # Glossy is blocked only on the BATHROOM floor (slippery underfoot in a wet
    # area). Kitchen floor allows glossy, and base / highlighter / backsplash
    # (wall placements) allow glossy in both rooms.
    if room == "bathroom" and placement == "floor":
        if is_glossy(finish): return False

    # Bathroom: SET_A categories must be special sizes
    if room == "bathroom" and cat in SET_A_CATEGORIES:
        if size_str not in BATHROOM_SPECIAL_SIZES: return False

    # Kitchen backsplash (regular): max 1200mm per side (glossy and matte both allowed)
    if room == "kitchen" and placement == "backsplash":
        w, h = parse_size(size_str)
        if w > 1200 or h > 1200: return False

    # Bathroom plain-floor: strict rules. The application must explicitly include
    # Bathroom (a generic "other" application does NOT qualify here), the finish
    # must be non-glossy, and both dimensions must be 600mm (2x2 ft) or smaller.
    if room == "bathroom" and placement == "floor" and cat == "plain":
        if not has_room(v["application_list"], "Bathroom"): return False
        if is_glossy(finish): return False
        w, h = parse_size(size_str)
        if w > 600 or h > 600: return False

    # Highlighter category: strictly requires the actual room in application
    # (overrides any fallback logic — no Kitchen-for-Bathroom substitution here)
    if cat == "highlighter" and not is_other_app(v["application_raw"]):
        if room == "bathroom" and not has_room(v["application_list"], "Bathroom"):
            return False
        if room == "kitchen" and not has_room(v["application_list"], "Kitchen"):
            return False

    return True


def _make_pool(handles, vcolors, per_tile_caps=None):
    """Build shade/family index for a list of handles."""
    by_shade = defaultdict(list)
    by_family = defaultdict(list)
    handle_to_family = {}
    for h in handles:
        c = vcolors.get(h)
        if c:
            ps = c.get("primary_shade", "")
            if ps: by_shade[ps].append(h)
            pf = c.get("primary_family", "")
            if pf:
                by_family[pf].append(h)
                handle_to_family[h] = pf
            else:
                handle_to_family[h] = SHADE_TO_FAMILY.get(ps, "Unknown")
    return {
        "all": handles,
        "by_shade": dict(by_shade),
        "by_family": dict(by_family),
        "handle_to_family": handle_to_family,
        "glossy_set": set(),
        "per_tile_caps": per_tile_caps or {},
    }


def merge_pool_entries(*entries):
    """Merge multiple pool entries into one deduplicated combined pool."""
    all_handles = []; by_shade = defaultdict(list)
    by_family = defaultdict(list); handle_to_family = {}
    seen = set()
    for entry in entries:
        if not entry: continue
        for h in entry["all"]:
            if h not in seen:
                all_handles.append(h); seen.add(h)
        for shade, hs in entry["by_shade"].items():
            existing = set(by_shade[shade])
            by_shade[shade].extend(h for h in hs if h not in existing)
        for fam, hs in entry["by_family"].items():
            existing = set(by_family[fam])
            by_family[fam].extend(h for h in hs if h not in existing)
        handle_to_family.update(entry.get("handle_to_family", {}))
    # Merge per_tile_caps from all source entries
    merged_caps = {}
    for entry in entries:
        if not entry: continue
        merged_caps.update(entry.get("per_tile_caps", {}))
    return {
        "all": all_handles,
        "by_shade": dict(by_shade),
        "by_family": dict(by_family),
        "handle_to_family": handle_to_family,
        "glossy_set": set(),
        "per_tile_caps": merged_caps,
    }


def build_pools(variants, vcolors):
    print("Building candidate pools...")
    room_placements = [
        ("bathroom", "floor"), ("bathroom", "base"), ("bathroom", "highlighter"),
        ("kitchen", "floor"), ("kitchen", "backsplash"),
    ]

    pool_index = {}

    # ── Standard per-category pools ──────────────────────────────────────────
    all_cats = set(v["category"] for v in variants.values())
    for cat in all_cats:
        for room, placement in room_placements:
            handles = []
            for h, v in variants.items():
                if v["category"] != cat: continue
                # Moroccan tiles never go in floor pools
                if cat == "moroccan" and placement == "floor": continue
                # Rustic tiles never go in backsplash pools (rustic is a floor tile in kitchen)
                if cat == "rustic" and placement == "backsplash": continue
                app_raw  = v["application_raw"]
                app_list = v["application_list"]
                # Bathroom base: primary filter is Bathroom, fallback to Kitchen.
                # (Glossy wall tiles are fine for bathroom base — they just need
                #  some bathroom/kitchen relevance in their application.)
                # All other placements use the room's own application filter.
                if room == "bathroom" and placement == "base":
                    if not is_other_app(app_raw) and \
                       not has_room(app_list, "Bathroom") and \
                       not has_room(app_list, "Kitchen"):
                        continue
                else:
                    if not is_other_app(app_raw) and not has_room(app_list, room.capitalize()):
                        continue
                if not passes_placement_constraint(v, placement, room): continue
                handles.append(h)
            glossy_set = {h for h in handles if is_glossy(variants[h]["finish"])} \
                         if placement == "highlighter" else set()
            entry = _make_pool(handles, vcolors)
            entry["glossy_set"] = glossy_set
            pool_index[(cat, room, placement)] = entry

    # ── 4x2 backsplash pools (kitchen only) ──────────────────────────────────
    for pool_cat, allowed_cats in [
        ("4x2_any",           None),          # any non-SET_A category
        ("4x2_plain",         {"plain"}),
        ("4x2_marble_endless", {"marble", "endless"}),
    ]:
        handles = []
        for h, v in variants.items():
            cat = v["category"]
            if allowed_cats and cat not in allowed_cats: continue
            if not allowed_cats and cat in SET_A_CATEGORIES: continue
            app_raw  = v["application_raw"]
            app_list = v["application_list"]
            if not is_other_app(app_raw) and not has_room(app_list, "Kitchen"): continue
            if not passes_placement_constraint(v, "4x2_backsplash", "kitchen"): continue
            handles.append(h)
        pool_index[(pool_cat, "kitchen", "4x2_backsplash")] = _make_pool(handles, vcolors)

    # ── Travertino bathroom base pool (capped at TRAVERTINO_CAP per tile) ────
    trav_handles = []
    for h, v in variants.items():
        if v["category"] != "travertino": continue
        app_raw  = v["application_raw"]
        app_list = v["application_list"]
        other    = is_other_app(app_raw)
        if not other and not has_room(app_list, "Bathroom") and not has_room(app_list, "Kitchen"):
            continue
        if not passes_placement_constraint(v, "base", "bathroom"): continue
        trav_handles.append(h)
    trav_caps = {h: TRAVERTINO_CAP for h in trav_handles}
    pool_index[("travertino", "bathroom", "base")] = _make_pool(
        trav_handles, vcolors, per_tile_caps=trav_caps
    )
    print(f"  Travertino bathroom base pool: {len(trav_handles)} tiles (cap={TRAVERTINO_CAP} each)")

    print(f"  Pools built for {len(pool_index)} (category, room, placement) combinations")
    return pool_index


def resolve_pool(cat, room, placement, pool_index):
    """Return pool entry for cat at an explicit placement, handling compound
    categories. `placement` is the recommendation's placement group
    (floor / base / highlighter / backsplash)."""
    # 4x2 pools are always kitchen backsplash regardless of placement
    if cat in ("4x2_any", "4x2_plain", "4x2_marble_endless"):
        return pool_index.get((cat, "kitchen", "4x2_backsplash"))

    # Travertino is always bathroom base (only used in floor-input bathroom mixes)
    if cat == "travertino":
        return pool_index.get(("travertino", "bathroom", "base"))

    if cat == "marble_endless":
        return merge_pool_entries(
            pool_index.get(("marble",  room, placement)),
            pool_index.get(("endless", room, placement)),
        )
    if cat == "base_mix":   # plain or rustic or marble or terrazzo
        return merge_pool_entries(*[
            pool_index.get((c, room, placement))
            for c in ("plain", "rustic", "marble", "terrazzo")
        ])

    return pool_index.get((cat, room, placement))


# ── Color matching ─────────────────────────────────────────────────────────────

def get_top_shades(input_shade, input_family, shade_pairs, family_pairs,
                   secondary_shade="", tertiary_shade=""):
    shade_rank = {s: i for i, s in enumerate(shade_pairs.get(input_shade, []))}
    top_shades = list(shade_pairs.get(input_shade, []))
    seen = set(top_shades)
    for s in shade_pairs.get(secondary_shade, []):
        if s not in seen: top_shades.append(s); seen.add(s)
    for s in shade_pairs.get(tertiary_shade, []):
        if s not in seen: top_shades.append(s); seen.add(s)
    for paired_family in family_pairs.get(input_family, []):
        for shade in sorted(FAMILY_TO_SHADES.get(paired_family, []),
                            key=lambda s: shade_rank.get(s, 9999)):
            if shade not in seen: top_shades.append(shade); seen.add(shade)
    return top_shades


# ── Picking helpers ────────────────────────────────────────────────────────────

def pick_with_color_variety(pool_entry, count, top_shades, used, family_counts,
                            rng, global_freq, excluded_shade=""):
    """
    Pick `count` tiles from the pool with even global distribution.

    Sorting priority (ascending):
      1. global_freq  — tiles recommended least often are always preferred
      2. shade_rank   — among equal-frequency tiles, better colour matches win
      3. random jitter — breaks remaining ties fairly

    No GLOBAL_CAP: the freq-first sort naturally spreads load across all tiles
    without needing an artificial ceiling that causes spikes when relaxed.
    """
    by_shade       = pool_entry["by_shade"]
    all_handles    = pool_entry["all"]
    handle_to_fam  = pool_entry.get("handle_to_family", {})
    glossy_set     = pool_entry.get("glossy_set", set())
    per_tile_caps  = pool_entry.get("per_tile_caps", {})
    picked         = []
    excluded_hs    = set(by_shade.get(excluded_shade, [])) if excluded_shade else set()

    def try_pick(h, relax_family=False):
        if h in used or h in excluded_hs: return False
        # Per-tile cap (e.g. travertino capped at 20)
        tile_cap = per_tile_caps.get(h)
        if tile_cap is not None and global_freq.get(h, 0) >= tile_cap: return False
        fam = handle_to_fam.get(h, "Unknown")
        cap = FAMILY_CAPS.get(fam, DEFAULT_FAMILY_CAP)
        if not relax_family and family_counts.get(fam, 0) >= cap: return False
        picked.append(h); used.add(h)
        family_counts[fam] = family_counts.get(fam, 0) + 1
        global_freq[h]     = global_freq.get(h, 0) + 1
        return True

    # Build shade-rank lookup (lower = better colour match for this input)
    shade_rank_of = {}
    for rank, shade in enumerate(top_shades):
        for h in by_shade.get(shade, []):
            if h not in shade_rank_of:
                shade_rank_of[h] = rank
    NO_MATCH_RANK = len(top_shades)

    # Sort key: (global_freq, shade_rank, random_jitter)
    #
    # global_freq first  → tiles recommended least often are always preferred,
    #                       ensuring every tile in the pool gets used evenly.
    # shade_rank second  → among tiles at equal frequency, better colour matches
    #                       are preferred (colour relevance within fairness).
    # pre-shuffle        → randomises remaining ties so no tile is systematically
    #                       favoured by list order.
    candidates = [h for h in all_handles if h not in used and h not in excluded_hs]
    rng.shuffle(candidates)
    candidates.sort(key=lambda h: (
        global_freq.get(h, 0),
        shade_rank_of.get(h, NO_MATCH_RANK),
    ))

    # Pass 1: respect family diversity cap
    for h in candidates:
        if len(picked) >= count: break
        try_pick(h, relax_family=False)

    # Pass 2: relax family cap if still short
    if len(picked) < count:
        for h in candidates:
            if len(picked) >= count: break
            try_pick(h, relax_family=True)

    return picked


def restrict_pool_to_shades(pool_entry, shades):
    """Return a copy of pool_entry containing only tiles whose shade is in
    `shades`. Returns None if no tiles match."""
    if not pool_entry: return None
    shade_set = set(shades)
    by_shade = {s: hs for s, hs in pool_entry["by_shade"].items() if s in shade_set}
    allowed = set()
    for hs in by_shade.values():
        allowed.update(hs)
    if not allowed:
        return None
    new_entry = dict(pool_entry)
    new_entry["all"] = [h for h in pool_entry["all"] if h in allowed]
    new_entry["by_shade"] = by_shade
    new_entry["handle_to_family"] = {
        h: f for h, f in pool_entry.get("handle_to_family", {}).items() if h in allowed
    }
    return new_entry


def pick_for_category(pool_entry, count, cat_shades, used, family_counts, rng,
                       global_freq, input_shade="", strict_shades=None):
    """Pick `count` tiles. If `strict_shades` is given, tiles whose colour
    shade is in that set are tried first (hard colour filter); only if that
    pool can't supply enough does it fall back to the full pool for the
    remainder (so moroccan inputs never recommend wildly different colours
    like Black/Brown for a Grey-base tile unless absolutely necessary)."""
    picked = []
    if strict_shades:
        restricted = restrict_pool_to_shades(pool_entry, strict_shades)
        if restricted and restricted["all"]:
            picked.extend(pick_with_color_variety(
                restricted, count, cat_shades, used, family_counts, rng,
                global_freq, input_shade))
            remaining = count - len(picked)
            if remaining > 0:
                # Still short on colour-correct tiles -- relax per-tile usage
                # caps within the colour-correct pool itself before resorting
                # to off-colour tiles from the full pool.
                relaxed = dict(restricted)
                relaxed["per_tile_caps"] = {}
                picked.extend(pick_with_color_variety(
                    relaxed, remaining, cat_shades, used, family_counts, rng,
                    global_freq, input_shade))
    remaining = count - len(picked)
    if remaining > 0:
        picked.extend(pick_with_color_variety(
            pool_entry, remaining, cat_shades, used, family_counts, rng,
            global_freq, input_shade))
    return picked


def pick_gallery(pool_entry, count, co_handles, used, family_counts, global_freq,
                 excluded_shade="", strict_shades=None):
    handle_to_fam = pool_entry.get("handle_to_family", {})
    pool_set      = set(pool_entry["all"])
    excluded_hs   = set(pool_entry["by_shade"].get(excluded_shade, [])) if excluded_shade else set()
    allowed_hs    = None
    if strict_shades:
        allowed_hs = set()
        for s in strict_shades:
            allowed_hs.update(pool_entry["by_shade"].get(s, []))
        if not allowed_hs:
            allowed_hs = None  # nothing matches -- don't over-restrict, fall through
    picked = []
    for h in co_handles:
        if len(picked) >= count: break
        if h not in pool_set or h in used or h in excluded_hs: continue
        if allowed_hs is not None and h not in allowed_hs: continue
        fam = handle_to_fam.get(h, "Unknown")
        cap = FAMILY_CAPS.get(fam, DEFAULT_FAMILY_CAP)
        if family_counts.get(fam, 0) >= cap: continue
        picked.append(h); used.add(h)
        family_counts[fam] = family_counts.get(fam, 0) + 1
        global_freq[h]     = global_freq.get(h, 0) + 1
    return picked


# ── Eligible rooms ─────────────────────────────────────────────────────────────

def eligible_rooms(v):
    cat      = v["category"]
    app_raw  = v["application_raw"]
    app_list = v["application_list"]
    other    = is_other_app(app_raw)
    glossy   = is_glossy(v["finish"])

    # Glossy disqualifies a tile from the bathroom ONLY when it is a floor-type
    # input — a glossy floor tile is unsuitable as a bathroom floor. Glossy WALL
    # inputs (subway, moroccan, geometric, mosaic, highlighter, …) still get
    # bathroom recs: they sit on the wall, and the floor/base tiles paired with
    # them are forced non-glossy by the placement rules anyway.
    is_wall = get_input_group(cat, v["application_type"]).startswith("wall_")
    glossy_blocks_bathroom = glossy and not is_wall

    # Highlighter input tiles must have Kitchen in application to get any recommendations
    if cat == "highlighter" and not other and not has_room(app_list, "Kitchen"):
        return set()

    if cat in KITCHEN_EXCLUDED_INPUT:
        # Terrazzo / mosaic → bathroom only
        if glossy_blocks_bathroom: return set()
        if other or has_room(app_list, "Bathroom"): return {"bathroom"}
        return set()

    rooms = set()
    if not glossy_blocks_bathroom:
        if other or has_room(app_list, "Bathroom"): rooms.add("bathroom")
    if other or has_room(app_list, "Kitchen"): rooms.add("kitchen")
    return rooms


# ── Room generation ────────────────────────────────────────────────────────────

# Monochrome: subway/highlighter picks follow this exact shade-family split
# (Black/White/Blue/Green only), and plain picks (bathroom Floor + Base, kitchen
# Floor) must be White or Grey only — the Beige family is excluded entirely.
MONO_SUBWAY_DIST   = [("White", 2), ("Black", 2), ("Blue", 1), ("Green", 1)]
MONO_PLAIN_FAMILIES = ["White", "Grey"]


def pick_from_families(pool_entry, count, families, used, family_counts, rng,
                       global_freq, excluded_shades=None):
    """Pick up to `count` tiles whose primary colour family is in `families`.
    Tiles whose primary shade is in `excluded_shades` are skipped."""
    handle_to_fam = pool_entry.get("handle_to_family", {})
    all_handles   = pool_entry["all"]
    families_set  = set(families)
    excluded_hs   = set()
    if excluded_shades:
        for s in excluded_shades:
            excluded_hs.update(pool_entry["by_shade"].get(s, []))
    candidates = [h for h in all_handles
                  if h not in used and h not in excluded_hs
                  and handle_to_fam.get(h) in families_set]
    rng.shuffle(candidates)
    candidates.sort(key=lambda h: global_freq.get(h, 0))
    picked = []
    for h in candidates:
        if len(picked) >= count: break
        picked.append(h); used.add(h)
        fam = handle_to_fam.get(h, "Unknown")
        family_counts[fam] = family_counts.get(fam, 0) + 1
        global_freq[h]     = global_freq.get(h, 0) + 1
    return picked


def _pick_subway_slot(count, room, placement, top_shades, input_shade, co_handles,
                      used, rng, global_freq, pool_index, strict_shades):
    """50/50 subway vs subway-look picks for one slot. Returns a list of handles."""
    family_counts = {}
    picked = []
    look_count   = count // 2
    actual_count = count - look_count
    for sub_cat, n in (("subway look", look_count), ("subway", actual_count)):
        if n <= 0: continue
        entry = resolve_pool(sub_cat, room, placement, pool_index)
        if not entry or not entry["all"]: continue
        cat_shades = _maybe_navy_front(top_shades, input_shade, "subway")
        gallery = pick_gallery(entry, n, co_handles, used, family_counts,
                               global_freq, input_shade, strict_shades)
        picked.extend(gallery)
        remaining = n - len(gallery)
        if remaining > 0:
            picked.extend(pick_for_category(
                entry, remaining, cat_shades, used,
                family_counts, rng, global_freq, input_shade, strict_shades))
    return picked


def generate_monochrome_room(input_handle, room, room_mix, pool_index, global_freq):
    """Monochrome inputs, grouped output. plain picks = White/Beige/Grey only;
    subway picks follow the fixed Black/White/Blue/Green split AND are 50/50
    subway vs subway-look. Returns {group: [handles]}."""
    rng  = random.Random(abs(hash(input_handle + room + "_mono")))
    used = {input_handle}
    out  = {}
    for group, mix in room_mix.items():
        placement = group
        recs = []
        for (cat, count) in mix:
            family_counts = {}
            if cat == "subway":
                sw = resolve_pool("subway", room, placement, pool_index)
                sl = resolve_pool("subway look", room, placement, pool_index)
                merged = merge_pool_entries(sw, sl)
                if not merged["all"]: continue
                fams = []
                for fam, fcount in MONO_SUBWAY_DIST:
                    fams.extend([fam] * fcount)
                for i, fam in enumerate(fams):
                    primary, secondary = (sw, sl) if i % 2 == 0 else (sl, sw)
                    got = []
                    if primary and primary["all"]:
                        got = pick_from_families(primary, 1, [fam], used, family_counts, rng, global_freq)
                    if not got and secondary and secondary["all"]:
                        got = pick_from_families(secondary, 1, [fam], used, family_counts, rng, global_freq)
                    if not got:
                        got = pick_from_families(merged, 1, [fam], used, family_counts, rng, global_freq)
                    recs.extend(got)
            else:
                pe = resolve_pool(cat, room, placement, pool_index)
                if not pe or not pe["all"]: continue
                recs.extend(pick_from_families(
                    pe, count, MONO_PLAIN_FAMILIES, used, family_counts, rng, global_freq))
        out[group] = recs
    return out


def generate_room(input_handle, input_group, room, room_mix, top_shades,
                  pool_index, co_occur, global_freq, input_shade=""):
    """Generate grouped recommendations for one room. `room_mix` is
    {placement_group: [(cat, count), ...]}. Returns {placement_group: [handles]}."""
    if input_group == "floor_monochrome":
        return generate_monochrome_room(input_handle, room, room_mix, pool_index, global_freq)

    rng        = random.Random(abs(hash(input_handle + room)))
    used       = {input_handle}
    co_handles = co_occur.get(input_handle, [])

    # Moroccan: hard-filter colour to the input's same-base-colour shade list.
    strict_shades = top_shades if input_group == "wall_moroccan" else None

    out = {}
    for group, mix in room_mix.items():
        placement    = group
        recs         = []
        group_target = sum(n for (_, n) in mix)
        for (cat, count) in mix:
            # Fresh family_counts per slot so one category's picks don't block
            # another category's family budget.
            family_counts = {}
            if cat == "subway":
                recs.extend(_pick_subway_slot(
                    count, room, placement, top_shades, input_shade, co_handles,
                    used, rng, global_freq, pool_index, strict_shades))
                continue

            pool_entry = resolve_pool(cat, room, placement, pool_index)
            if not pool_entry or not pool_entry["all"]: continue
            cat_shades = _maybe_navy_front(top_shades, input_shade, cat)
            gallery    = pick_gallery(pool_entry, count, co_handles, used,
                                      family_counts, global_freq, input_shade, strict_shades)
            recs.extend(gallery)
            remaining = count - len(gallery)
            if remaining > 0:
                recs.extend(pick_for_category(
                    pool_entry, remaining, cat_shades, used,
                    family_counts, rng, global_freq, input_shade, strict_shades))

        # ── Backfill this group to its target from the group's own categories ──
        shortfall = group_target - len(recs)
        if shortfall > 0:
            fc = {}
            for (cat, _) in mix:
                if shortfall <= 0: break
                sub_cats = ("subway look", "subway") if cat == "subway" else (cat,)
                for sc in sub_cats:
                    if shortfall <= 0: break
                    pe = resolve_pool(sc, room, placement, pool_index)
                    if pe and pe["all"]:
                        extra = pick_for_category(
                            pe, shortfall, top_shades, used,
                            fc, rng, global_freq, input_shade, strict_shades)
                        recs.extend(extra); shortfall -= len(extra)
        out[group] = recs

    # ── White-input Navy Blue subway guarantee (skip moroccan) ────────────────
    # Apply within whichever group carries the subway slot (highlighter for
    # bathroom, backsplash for kitchen).
    if input_shade == "White" and input_group != "wall_moroccan":
        for group, mix in room_mix.items():
            if not any(c == "subway" for c, _ in mix): continue
            recs = out.get(group, [])
            if not recs: continue
            done = False
            for sub_cat in ("subway", "subway look"):
                subway_pool = pool_index.get((sub_cat, room, group))
                if not subway_pool: continue
                navy_pool = set(subway_pool["by_shade"].get("Navy Blue", []))
                if any(h in navy_pool for h in recs): done = True; break
                cands = sorted(
                    [h for h in navy_pool if h not in set(recs) and h != input_handle],
                    key=lambda h: global_freq.get(h, 0))
                if cands:
                    navy_pick  = cands[0]
                    subway_all = set(subway_pool["all"])
                    swap_idx = next(
                        (i for i in range(len(recs)-1, -1, -1) if recs[i] not in subway_all),
                        len(recs) - 1)
                    global_freq[navy_pick] = global_freq.get(navy_pick, 0) + 1
                    recs[swap_idx] = navy_pick
                    done = True; break
            if done: break

    return out


def _maybe_navy_front(top_shades, input_shade, cat):
    """For White input + subway slot, push Navy Blue to front of shade list."""
    if input_shade == "White" and cat == "subway" and "Navy Blue" in top_shades:
        shades = list(top_shades)
        shades.remove("Navy Blue")
        shades.insert(0, "Navy Blue")
        return shades
    return top_shades


# ── Overlap enforcement ────────────────────────────────────────────────────────

def enforce_overlap(bath_groups, kit_groups, input_handle, input_group,
                    top_shades, pool_index, global_freq):
    """Cap how many tiles appear in BOTH rooms at MAX_OVERLAP. Excess overlapping
    tiles are removed from their kitchen group and that group is backfilled with
    non-overlapping tiles. bath_groups / kit_groups are {group: [handles]}."""
    bath_all = set(h for hs in bath_groups.values() for h in hs)
    kit_flat = [(g, h) for g, hs in kit_groups.items() for h in hs]
    overlap  = [(g, h) for (g, h) in kit_flat if h in bath_all]
    excess   = overlap[MAX_OVERLAP:]
    if not excess:
        return bath_groups, kit_groups

    excess_handles = set(h for (_, h) in excess)
    forbidden = bath_all | {input_handle} | set(h for (_, h) in kit_flat)
    kit_mix = PAIRING_TABLE[input_group].get("kitchen") or {}

    for g in list(kit_groups.keys()):
        n_removed = sum(1 for h in kit_groups[g] if h in excess_handles)
        if n_removed == 0:
            continue
        kit_groups[g] = [h for h in kit_groups[g] if h not in excess_handles]
        shortfall = n_removed
        mix = kit_mix.get(g, [])
        for relax_global in (False, True):
            if shortfall <= 0: break
            for (cat, _) in mix:
                if shortfall <= 0: break
                cats = ("subway look", "subway") if cat == "subway" else (cat,)
                for sc in cats:
                    if shortfall <= 0: break
                    pe = resolve_pool(sc, "kitchen", g, pool_index)
                    if not pe: continue
                    for h in pe["all"]:
                        if shortfall <= 0: break
                        if h not in forbidden and (relax_global or global_freq.get(h, 0) < GLOBAL_CAP):
                            kit_groups[g].append(h); forbidden.add(h)
                            global_freq[h] = global_freq.get(h, 0) + 1
                            shortfall -= 1
    return bath_groups, kit_groups


# ── Outdoor pools & generation ──────────────────────────────────────────────────

def build_outdoor_pools(variants, vcolors):
    """Build the three outdoor candidate pools (outdoor-eligible tiles only):
      elevation → elevation-category tiles  (wall recs)
      punch     → punch-finish tiles        (wall recs)
      parking   → is_parking tiles          (floor recs)
    is_parking takes precedence: a parking tile is placed only in the parking
    (floor) pool and is kept out of the elevation/punch wall pools, even if it
    also carries a punch finish."""
    print("Building outdoor candidate pools...")
    elevation, punch, parking = [], [], []
    for h, v in variants.items():
        if not is_outdoor_eligible(v):
            continue
        if v.get("is_parking"):
            parking.append(h)
            continue
        if v["category"] == "elevation":
            elevation.append(h)
        if is_punch_finish(v["finish"]):
            punch.append(h)
    pools = {
        "elevation": _make_pool(elevation, vcolors),
        "punch":     _make_pool(punch, vcolors),
        "parking":   _make_pool(parking, vcolors),
    }
    print(f"  Outdoor pools: elevation={len(elevation)}  punch={len(punch)}  parking={len(parking)}")
    return pools


def generate_outdoor(input_handle, in_type, top_shades, same_shades,
                     outdoor_pools, outdoor_freq):
    """Generate the combined outdoor recommendation list for one input tile.

    parking_floor input → 5 elevation + 5 punch (wall tiles)
    wall input          → 8 parking (floor tiles)

    Within each slot, ~40% of picks are same-base-colour (restricted to the
    input's own shade neighbourhood, like the moroccan rule) and the remaining
    ~60% follow the normal complementary colour-pairing list (top_shades).
    All picks share one `used` set so the same tile is never recommended twice,
    and `outdoor_freq` spreads usage evenly — independent of the bathroom/kitchen
    frequency counter so indoor recommendations are never perturbed."""
    rng  = random.Random(abs(hash(input_handle + "_outdoor")))
    used = {input_handle}

    if in_type == "parking_floor":
        slots = [("elevation", OUTDOOR_ELEVATION_N), ("punch", OUTDOOR_PUNCH_N)]
    else:  # "wall"
        slots = [("parking", OUTDOOR_PARKING_N)]

    recs = []
    for cat, count in slots:
        pool = outdoor_pools.get(cat)
        if not pool or not pool["all"]:
            continue
        family_counts = {}
        before  = len(recs)
        same_n  = round(OUTDOOR_SAME_COLOR_FRAC * count)
        # Same-base-colour portion (hard-restricted to the input's shade neighbourhood)
        if same_n > 0 and same_shades:
            recs.extend(pick_for_category(
                pool, same_n, same_shades, used, family_counts, rng,
                outdoor_freq, "", same_shades))
        # Complementary colour-pairing portion (fills the rest of the slot)
        remaining = count - (len(recs) - before)
        if remaining > 0:
            recs.extend(pick_for_category(
                pool, remaining, top_shades, used, family_counts, rng,
                outdoor_freq, ""))
    return recs


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    variants, vcolors, shade_pairs, family_pairs, co_occur = load_data()
    pool_index = build_pools(variants, vcolors)
    print("Generating recommendations...")
    global_freq = {}
    # results keyed by handle so the outdoor pass can augment indoor records.
    results_map = {}; processed = 0

    # ── Pass 1: bathroom / kitchen (unchanged logic, shared global_freq) ──────
    for handle, v in variants.items():
        rooms = eligible_rooms(v)
        # Elevation is an outdoor-only category — it never gets bathroom/kitchen
        # recommendations (its outdoor recs are produced in pass 2).
        if v["category"] == "elevation":
            rooms = set()
        if not rooms: continue

        input_group     = get_input_group(v["category"], v["application_type"])
        c               = vcolors.get(handle)
        input_shade     = c["primary_shade"]   if c else ""
        input_family    = c["primary_family"]  if c else ""
        secondary_shade = c["secondary_shade"] if c else ""
        tertiary_shade  = c["tertiary_shade"]  if c else ""

        # Moroccan: same-base-colour pairing — input's own shade plus other
        # shades from the same colour family (White/Beige/Grey are treated as
        # one neutral group). Don't exclude the input's own shade from picks.
        if input_group == "wall_moroccan":
            top_shades = get_moroccan_shades(input_shade)
            excl_shade = ""
        else:
            top_shades = get_top_shades(input_shade, input_family, shade_pairs, family_pairs,
                                        secondary_shade, tertiary_shade)
            excl_shade = input_shade

        mix_bath = PAIRING_TABLE[input_group].get("bathroom")
        mix_kit  = PAIRING_TABLE[input_group].get("kitchen")

        # Wall-only moroccan/monochrome inputs: drop the subway groups
        # (bathroom highlighter + kitchen backsplash) since they can't go on a wall.
        if input_group in ("wall_moroccan", "floor_monochrome") and v["application_type"] == "wall":
            def _strip_subway(room_mix):
                if not room_mix: return room_mix
                out = {}
                for g, lst in room_mix.items():
                    lst2 = [(c, n) for (c, n) in lst if c != "subway"]
                    if lst2: out[g] = lst2
                return out
            mix_bath = _strip_subway(mix_bath)
            mix_kit  = _strip_subway(mix_kit)

        bath_recs = {}; kit_recs = {}
        if "bathroom" in rooms and mix_bath:
            bath_recs = generate_room(handle, input_group, "bathroom", mix_bath,
                                       top_shades, pool_index, co_occur,
                                       global_freq, excl_shade)
        if "kitchen" in rooms and mix_kit:
            kit_recs = generate_room(handle, input_group, "kitchen", mix_kit,
                                      top_shades, pool_index, co_occur,
                                      global_freq, excl_shade)

        bath_has = any(bath_recs.get(g) for g in bath_recs)
        kit_has  = any(kit_recs.get(g) for g in kit_recs)
        if bath_has and kit_has:
            bath_recs, kit_recs = enforce_overlap(
                bath_recs, kit_recs, handle, input_group,
                top_shades, pool_index, global_freq)

        results_map[handle] = {
            "input_variant_handle": handle,
            "input_category":       v["category"],
            "rooms":                set(rooms),   # finalised into a string later
            "bathroom_floor":       json.dumps(bath_recs.get("floor", [])),
            "bathroom_base":        json.dumps(bath_recs.get("base", [])),
            "bathroom_highlighter": json.dumps(bath_recs.get("highlighter", [])),
            "kitchen_floor":        json.dumps(kit_recs.get("floor", [])),
            "kitchen_backsplash":   json.dumps(kit_recs.get("backsplash", [])),
            "outdoor":              json.dumps([]),
        }
        processed += 1
        if processed % 2000 == 0:
            print(f"  {processed} / {len(variants)} done...")

    unique_tiles = len(global_freq)
    total_slots  = sum(global_freq.values())
    over_cap     = sum(1 for v in global_freq.values() if v > GLOBAL_CAP)
    print(f"\nDiversity stats: {unique_tiles} unique tiles used | {total_slots} total slots | "
          f"{over_cap} tiles exceeded cap (relaxed)")

    # ── Pass 2: outdoor spaces (own frequency counter — never touches indoor) ──
    print("Generating outdoor recommendations...")
    outdoor_pools = build_outdoor_pools(variants, vcolors)
    outdoor_freq  = {}
    outdoor_count = 0
    for handle, v in variants.items():
        in_type = outdoor_input_type(v)
        if not in_type or not is_outdoor_eligible(v):
            continue
        c               = vcolors.get(handle)
        input_shade     = c["primary_shade"]   if c else ""
        input_family    = c["primary_family"]  if c else ""
        secondary_shade = c["secondary_shade"] if c else ""
        tertiary_shade  = c["tertiary_shade"]  if c else ""
        top_shades  = get_top_shades(input_shade, input_family, shade_pairs, family_pairs,
                                     secondary_shade, tertiary_shade)
        same_shades = get_moroccan_shades(input_shade)

        out_list = generate_outdoor(handle, in_type, top_shades, same_shades,
                                    outdoor_pools, outdoor_freq)
        if not out_list:
            continue

        row = results_map.get(handle)
        if row is None:
            row = {
                "input_variant_handle": handle,
                "input_category":       v["category"],
                "rooms":                set(),
                "bathroom_floor":       json.dumps([]),
                "bathroom_base":        json.dumps([]),
                "bathroom_highlighter": json.dumps([]),
                "kitchen_floor":        json.dumps([]),
                "kitchen_backsplash":   json.dumps([]),
                "outdoor":              json.dumps([]),
            }
            results_map[handle] = row
        row["rooms"].add("outdoor")
        row["outdoor"] = json.dumps(out_list)
        outdoor_count += 1
    print(f"  Outdoor recommendations generated for {outdoor_count} tiles")

    # ── Finalise records in variants order; turn the rooms set into a string ──
    results = []
    for handle in variants:
        row = results_map.get(handle)
        if not row:
            continue
        row["eligible_rooms"] = ",".join(sorted(row.pop("rooms")))
        results.append(row)
    skipped = len(variants) - len(results)

    print(f"\nWriting {len(results)} records to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "input_variant_handle", "input_category", "eligible_rooms",
            "bathroom_floor", "bathroom_base", "bathroom_highlighter",
            "kitchen_floor", "kitchen_backsplash", "outdoor"])
        writer.writeheader(); writer.writerows(results)
    print(f"Done.  Processed: {processed}  |  Skipped: {skipped}")


if __name__ == "__main__":
    main()
