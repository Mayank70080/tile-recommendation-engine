# Tile Recommendation Engine

A FastAPI service that returns bathroom, kitchen, and outdoor tile recommendations for a given tile variant, based on color affinity and category-pairing logic. Recommendations are precomputed into a CSV and served at runtime.

## What's in here

| File | Purpose |
|------|---------|
| `api.py` | FastAPI app — serves recommendations and variant data from the CSVs. |
| `frontend.html` | Simple browser tester UI (served at `/`). |
| `generate_recommendations.py` | Batch script that builds `recommendations.csv` from the source data. |
| `recommendations.csv` | Precomputed recommendations consumed by the API. |
| `variants.csv` | Tile variant catalog (handle, product name, category, size, image). |
| `variant_colors.csv` | Per-variant color/shade data. |
| `shade_pairs_recommendation.csv`, `family_pairs_recommendation.csv` | Pairing rules used by the generator. |
| `application_image_tags.csv` | Room/application tags used by the generator. |
| `requirements.txt`, `Procfile`, `.python-version` | Runtime + deployment config. |

The API only reads `recommendations.csv`, `variants.csv`, and `variant_colors.csv`. The other CSVs and `generate_recommendations.py` are only needed to regenerate recommendations.

## Run locally

Requires Python 3.12.

```bash
pip install -r requirements.txt
uvicorn api:app --reload
```

Then open http://localhost:8000 for the tester UI, or http://localhost:8000/docs for the interactive API docs.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Browser tester UI. |
| `GET` | `/health` | Health check; returns `records_loaded`. |
| `GET` | `/variant/{variant_handle}` | Details for a single variant. |
| `GET` | `/variants/search?q=...&limit=20` | Search variants by handle or product name. |
| `GET` | `/recommendations/{variant_handle}?room=&limit=20` | Recommendations for a variant. `room` optionally filters to `bathroom`, `kitchen`, or `outdoor`. |
| `GET` | `/recommendations/batch?handles=a,b,c&limit=20` | Recommendations for multiple handles (max 50). |

Example:

```bash
curl http://localhost:8000/recommendations/tl-xxxxx?room=bathroom&limit=10
```

## Regenerating recommendations

When the source data changes, rebuild `recommendations.csv`:

```bash
python generate_recommendations.py
```

Then restart the API (or redeploy) so it loads the new file.

## Deployment (Render)

Deployed as a web service on Render from this repo:

- **Build:** `pip install -r requirements.txt`
- **Start:** `uvicorn api:app --host 0.0.0.0 --port $PORT` (from `Procfile`)
- **Python version:** pinned to 3.12 via `.python-version`

Pushing to the connected branch triggers an automatic redeploy. The free tier spins down after inactivity, so the first request after idle can take ~50s.
