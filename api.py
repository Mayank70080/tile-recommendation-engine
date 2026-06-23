"""
Recommendation Engine - FastAPI Endpoint
=========================================
Start:  uvicorn api:app --reload
Endpoint: GET /recommendations/{variant_handle}

Response:
{
  "input_variant_handle": "tl-xxxxx",
  "input_category": "moroccan",
  "eligible_rooms": ["bathroom", "kitchen"],
  "bathroom": ["handle1", "handle2", ...],   // up to 10
  "kitchen":  ["handle1", "handle2", ...]    // up to 10
}
"""

import csv
import json
import os
from functools import lru_cache
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────────────────────
RECOMMENDATIONS_FILE = os.getenv("RECOMMENDATIONS_FILE", "recommendations.csv")
VARIANTS_FILE        = os.getenv("VARIANTS_FILE",        "variants.csv")
VARIANT_COLORS_FILE  = os.getenv("VARIANT_COLORS_FILE",  "variant_colors.csv")

app = FastAPI(
    title="Tile Recommendation Engine",
    description="Returns up to 10 bathroom and 10 kitchen tile recommendations for a given variant handle.",
    version="1.0.0",
)

# Allow all origins for development; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── Response models ───────────────────────────────────────────────────────────

class RecommendationResponse(BaseModel):
    input_variant_handle: str
    input_category: str
    eligible_rooms: list[str]
    # Grouped by placement:
    #   bathroom -> {floor, base, highlighter}
    #   kitchen  -> {floor, backsplash}
    #   outdoor  -> {outdoor}  (single combined group)
    bathroom: dict[str, list[str]]
    kitchen: dict[str, list[str]]
    outdoor: dict[str, list[str]]


class ErrorResponse(BaseModel):
    detail: str

class VariantDetail(BaseModel):
    handle:           str
    product_name:     str
    category:         str
    size:             str
    application_type: str
    image_url:        str
    primary_shade:    str
    primary_hex:      str


# ── Data loading (cached at startup) ─────────────────────────────────────────

@lru_cache(maxsize=1)
def load_variants_data() -> dict:
    """Load variants + colors into a single dict keyed by handle."""
    colors = {}
    if os.path.exists(VARIANT_COLORS_FILE):
        with open(VARIANT_COLORS_FILE, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                colors[row["variant_handle"].strip()] = {
                    "image_url":     row["image_url"].strip(),
                    "primary_shade": row["primary_color_shade"].strip(),
                    "primary_hex":   row["primary_hex"].strip(),
                }

    data = {}
    if os.path.exists(VARIANTS_FILE):
        with open(VARIANTS_FILE, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["is_active"].strip().upper() != "TRUE":
                    continue
                h = row["variant_handle"].strip()
                c = colors.get(h, {})
                data[h] = {
                    "handle":           h,
                    "product_name":     row["product_name"].strip(),
                    "category":         row["category"].strip(),
                    "size":             row["size"].strip(),
                    "application_type": row["application_type"].strip(),
                    "image_url":        c.get("image_url", ""),
                    "primary_shade":    c.get("primary_shade", ""),
                    "primary_hex":      c.get("primary_hex", ""),
                }
    return data


@lru_cache(maxsize=1)
def load_recommendations() -> dict:
    """Load recommendations.csv into a dict keyed by input_variant_handle."""
    if not os.path.exists(RECOMMENDATIONS_FILE):
        raise FileNotFoundError(
            f"Recommendations file not found: {RECOMMENDATIONS_FILE}\n"
            "Run generate_recommendations.py first."
        )
    def _load(row, col):
        val = row.get(col)
        return json.loads(val) if val else []

    data = {}
    with open(RECOMMENDATIONS_FILE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            handle = row["input_variant_handle"].strip()
            data[handle] = {
                "input_category": row["input_category"].strip(),
                "eligible_rooms": [r for r in row["eligible_rooms"].split(",") if r],
                "bathroom": {
                    "floor":       _load(row, "bathroom_floor"),
                    "base":        _load(row, "bathroom_base"),
                    "highlighter": _load(row, "bathroom_highlighter"),
                },
                "kitchen": {
                    "floor":      _load(row, "kitchen_floor"),
                    "backsplash": _load(row, "kitchen_backsplash"),
                },
                "outdoor": {
                    "outdoor": _load(row, "outdoor"),
                },
            }
    return data


# ── Routes ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup_event():
    """Pre-load all data on startup."""
    try:
        recs = load_recommendations()
        print(f"Loaded {len(recs)} recommendation records.")
    except FileNotFoundError as e:
        print(f"WARNING: {e}")
    variants = load_variants_data()
    print(f"Loaded {len(variants)} variant records.")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_frontend():
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend.html")
    if os.path.exists(frontend_path):
        with open(frontend_path, encoding="utf-8") as f:
            return f.read()
    return "<h2>frontend.html not found</h2>"


@app.get("/health")
def health():
    """Health check."""
    try:
        recs = load_recommendations()
        return {"status": "ok", "records_loaded": len(recs)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get(
    "/variant/{variant_handle}",
    response_model=VariantDetail,
    responses={404: {"model": ErrorResponse}},
    summary="Get details for a single variant",
)
def get_variant(variant_handle: str):
    variants = load_variants_data()
    if variant_handle not in variants:
        raise HTTPException(status_code=404, detail=f"Variant not found: '{variant_handle}'")
    return variants[variant_handle]


@app.get(
    "/variants/search",
    summary="Search variants by handle or product name",
)
def search_variants(
    q: str = Query(..., description="Search query (handle or product name)"),
    limit: int = Query(default=20, ge=1, le=100),
):
    variants = load_variants_data()
    q_lower  = q.lower().strip()
    results  = []
    for h, v in variants.items():
        if q_lower in h.lower() or q_lower in v["product_name"].lower():
            results.append({
                "handle":       h,
                "product_name": v["product_name"],
                "category":     v["category"],
                "size":         v["size"],
                "image_url":    v["image_url"],
            })
        if len(results) >= limit:
            break
    return {"results": results, "total": len(results)}


@app.get(
    "/recommendations/{variant_handle}",
    response_model=RecommendationResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get tile recommendations for a variant",
)
def get_recommendations(
    variant_handle: str,
    room: Optional[str] = Query(
        default=None,
        description="Filter by room: 'bathroom' or 'kitchen'. Omit for both.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=20,
        description="Max number of recommendations to return per room (1–20). "
                    "Moroccan/monochrome inputs use up to ~17 across Floor/Base/Highlighter.",
    ),
):
    """
    Returns up to 10 bathroom and/or kitchen tile recommendations
    for the given variant handle, based on color affinity and
    category pairing logic.

    - **variant_handle**: The unique handle of the input tile variant
    - **room**: Optional filter — `bathroom` or `kitchen`
    - **limit**: Cap results per room (default: 10)
    """
    recs = load_recommendations()

    if variant_handle not in recs:
        raise HTTPException(
            status_code=404,
            detail=f"No recommendations found for variant handle: '{variant_handle}'. "
                   "The tile may not be active, may not be eligible for bathroom or kitchen, "
                   "or recommendations have not been generated yet.",
        )

    entry = recs[variant_handle]

    bathroom = {g: lst[:limit] for g, lst in entry["bathroom"].items()}
    kitchen  = {g: lst[:limit] for g, lst in entry["kitchen"].items()}
    outdoor  = {g: lst[:limit] for g, lst in entry.get("outdoor", {}).items()}

    # Apply room filter if specified
    if room:
        room_lower = room.strip().lower()
        if room_lower not in ("bathroom", "kitchen", "outdoor"):
            raise HTTPException(
                status_code=400,
                detail="Invalid room filter. Use 'bathroom', 'kitchen', or 'outdoor'.",
            )
        if room_lower != "bathroom":
            bathroom = {g: [] for g in bathroom}
        if room_lower != "kitchen":
            kitchen = {g: [] for g in kitchen}
        if room_lower != "outdoor":
            outdoor = {g: [] for g in outdoor}

    return RecommendationResponse(
        input_variant_handle=variant_handle,
        input_category=entry["input_category"],
        eligible_rooms=entry["eligible_rooms"],
        bathroom=bathroom,
        kitchen=kitchen,
        outdoor=outdoor,
    )


@app.get(
    "/recommendations/batch",
    summary="Get recommendations for multiple variant handles",
)
def get_recommendations_batch(
    handles: str = Query(
        ...,
        description="Comma-separated list of variant handles (max 50).",
    ),
    limit: int = Query(default=20, ge=1, le=20),
):
    """
    Batch endpoint — returns recommendations for up to 50 variant handles in one call.
    Handles not found are listed under 'not_found'.
    """
    handle_list = [h.strip() for h in handles.split(",") if h.strip()]
    if len(handle_list) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 handles per batch request.")

    recs = load_recommendations()
    results = {}
    not_found = []

    for handle in handle_list:
        if handle not in recs:
            not_found.append(handle)
            continue
        entry = recs[handle]
        results[handle] = {
            "input_category": entry["input_category"],
            "eligible_rooms": entry["eligible_rooms"],
            "bathroom": {g: lst[:limit] for g, lst in entry["bathroom"].items()},
            "kitchen":  {g: lst[:limit] for g, lst in entry["kitchen"].items()},
            "outdoor":  {g: lst[:limit] for g, lst in entry.get("outdoor", {}).items()},
        }

    return {"results": results, "not_found": not_found}
