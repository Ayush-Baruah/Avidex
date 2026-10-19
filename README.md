# Avidex

Avidex is a full-stack bird identification and compendium application. It began as a Flask/Jinja CRUD project for a DBMS course and has grown into a three-part system: a data pipeline that scrapes and enriches bird data, a web app for browsing and searching birds, and a computer vision pipeline that identifies birds from an uploaded photo.

Developed by Ayush Baruah and Joseph Eidel.

## What it does

- **Browse & search** — a searchable compendium of ~1,650 bird species, each with photos, calls, rarity, range, and description, backed by MySQL and indexed in Typesense for fast fuzzy search.
- **Track sightings** — log birds you've seen, with GPS location (via Leaflet) and a running point total.
- **Earn rewards** — birders accumulate points and unlock rewards based on sightings.
- **Identify a bird from a photo** — upload an image or paste an image URL, and a custom-trained CNN returns its top-5 best guesses with confidence scores.
- **Full CRUD admin interface** — Jinja-templated pages for managing every entity (birds, birders, nests, rewards, sightings, rarities, and their many-to-many relationships) directly against the database.

## Stack

| Layer | Tech |
|---|---|
| Frontend | React (Vite), react-router-dom |
| Backend | Flask (JSON API + server-rendered Jinja templates), flask-cors |
| Database | MySQL (`mysqlclient`/`MySQLdb`), stored procedures only — no raw CRUD SQL from the app layer |
| Search | Typesense (Docker), queried directly from the browser |
| Computer vision | PyTorch — a from-scratch CNN (`BirdCNN`) trained on scraped/downloaded bird photos |
| Scraping | Selenium + headless Chrome (birdsoftheworld.org), Wikimedia Commons API (images), Xeno-canto API v3 (calls) |
| AI enrichment | Gemini (`google-genai`) for structured parsing, Exa (`exa_py`) for verification/lookup of missing fields |
| Notifications | Discord webhooks — used as a durable log for long-running scripts (scrape/enrichment/image-pull progress, errors, resume points) |

## Project structure

```
app.py                       # Flask entrypoint: CRUD routes + JSON API
database/
  DDL.sql                    # Schema (tables, views)
  DML.sql                    # Reference SELECT/INSERT/UPDATE/DELETE statements
  PL.sql                     # Stored procedures (reset + all CUD operations)
  db_connector.py            # MySQLdb connection + query() helper
  load_birds.py              # Loads data/processed_birds.csv into Birds via pl_add_bird
  load_bird_photos.py        # Loads data/bird_urls.csv into BirdPhotos via pl_add_bird_photo
templates/                   # Jinja templates for the CRUD admin pages (one per entity)
static/style.css             # Styling for the Jinja-rendered pages
frontend/                    # React app (Vite)
  src/pages/                 # Home, About, Compendium (search/browse)
  src/components/            # NavBar, BirdCard
  src/typesense.js           # Browser-direct Typesense search client
scripts/
  scraper/bird_scraper.py    # Selenium scraper for bird overview text (birdsoftheworld.org)
  image_pull/
    image_pull.py            # Wikimedia Commons image search + filtering -> data/bird_urls.csv
    image_downloader.py      # Downloads photo URLs from the DB, content-hash dedupe
    Image_cleanup.py         # Removes corrupt/duplicate downloaded images
    image_resize.py          # Resizes images for training (shorter side 256px), resumable
    image_stats.py           # Per-class image count statistics
  ai_search_and_fill/
    ai_integration.py        # Gemini parsing + Exa verification/lookup pipeline
    ai_check.py              # Flags hallucinated/duplicated species in processed data
  identifier/
    model.py                 # BirdCNN (PyTorch nn.Module)
    selection.py              # class_to_idx mapping, stratified train/val split
    datasetClass.py           # BirdImageDataset (PyTorch Dataset)
    training.py                # Full training + validation loop, checkpointing
    identify_one_img.py        # Loads best_bird_cnn.pt + idx_to_class.json, runs inference
  typesense/index_birds.py   # (Re)indexes the Birds table into Typesense
  notifs/discord_message.py  # Shared Discord webhook sender used across long-running scripts
```

## Data pipeline (offline, one-time / as-needed)

Run roughly in this order to go from nothing to a trained identifier:

1. **`scripts/scraper/bird_scraper.py`** — scrapes overview text per species into `data/scraped_birds.csv`.
2. **`scripts/ai_search_and_fill/ai_integration.py`** — parses scraped text into structured bird fields (Gemini) and fills/verifies gaps (Exa), writing `data/processed_birds.csv`.
3. **`scripts/ai_search_and_fill/ai_check.py`** — flags any hallucinated or duplicated species before loading.
4. **`database/load_birds.py`** — loads `processed_birds.csv` into the `Birds` table.
5. **`scripts/image_pull/image_pull.py`** — searches Wikimedia Commons per bird, filters out non-photographic results, writes candidate photo URLs to `data/bird_urls.csv`.
6. **`database/load_bird_photos.py`** — loads `bird_urls.csv` into `BirdPhotos`.
7. **`scripts/image_pull/image_downloader.py`** — downloads every photo URL from the DB into `data/downloaded_bird_photos/`, deduped by content hash, resumable via `data/download_manifest.csv`.
8. **`scripts/image_pull/Image_cleanup.py`** — removes corrupt or duplicate downloaded images.
9. **`scripts/image_pull/image_resize.py`** — resizes everything to a 256px shorter side into `data/resized_images/` (what the CV pipeline actually trains on), resumable, tolerant of truncated files.
10. **`scripts/typesense/index_birds.py`** — (re)builds the Typesense search index from the current `Birds` table. Re-run after any data changes.

## Computer vision pipeline

- **`scripts/identifier/selection.py`** — builds the class index from `data/resized_images/` and a stratified 80/20 train/val split per species.
- **`scripts/identifier/model.py`** — `BirdCNN`: 4 conv blocks (3→32→64→128→256 channels, each Conv2d+BatchNorm2d+ReLU+MaxPool2d), followed by global average pooling, dropout, and a linear classifier head.
- **`scripts/identifier/training.py`** — trains with Adam + cross-entropy loss on an Apple Silicon GPU (`mps`) when available, tracks train/val loss and val accuracy per epoch, checkpoints the best-accuracy weights to `best_bird_cnn.pt`, and saves the class mapping to `idx_to_class.json`.
- **`scripts/identifier/identify_one_img.py`** — loads the saved model + mapping once, exposes `classify_image`, `classify_image_from_file`, and `classify_image_from_url` for top-k inference on a single image.

**Current baseline (Model A):** ~14.9% top-1 validation accuracy across 1,639 classes with ~7 training images/class on average (chance ≈ 0.06%). This is intentionally framed as an honest from-scratch baseline; a planned Model B (embedding/vector-database approach) is expected to outperform it by a wide margin.

## API (Flask)

- `GET /api/birds?limit=&offset=` — paginated bird data with photo URLs, for the React Compendium page.
- `POST /api/identify` — accepts either an uploaded image file (`multipart/form-data`, field `image`) or an `image_url` form field; returns the top-5 predicted species with confidence scores.
- Full CRUD routes under `/Avidex/<entity>/{create,update,delete}` for every entity, backing the Jinja admin templates.

## Running locally

**Backend**
```bash
pip install -r requirements-lock.txt
python app.py        # http://localhost:8001
```

**Frontend**
```bash
cd frontend
npm install
npm run dev           # http://localhost:5173
```

**Search**
```bash
docker compose up -d  # Typesense on http://localhost:8108
python -m scripts.typesense.index_birds
```

**Database** — MySQL running locally (currently `localhost:3306`, root). Run `database/DDL.sql` then `CALL pl_reset_avidex();` (defined in `database/PL.sql`) to create and seed the schema.

### Environment variables (`.env`, project root)

| Variable | Used by |
|---|---|
| `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | `database/db_connector.py` |
| `DISCORD_WEBHOOK` | `scripts/notifs/discord_message.py` |
| `WIKIMEDIA_CONTACT_EMAIL` | `scripts/image_pull/image_pull.py`, `image_downloader.py` |
| `GEMINI_KEY` | `scripts/ai_search_and_fill/ai_integration.py` |
| `EXA_KEY` | `scripts/ai_search_and_fill/ai_integration.py` |
| `TYPESENSE_HOST`, `TYPESENSE_PORT`, `TYPESENSE_ADMIN_API_KEY` | `scripts/typesense/index_birds.py` |

The frontend's Typesense client (`frontend/src/typesense.js`) uses a separate, hardcoded **search-only** key (read-only, safe to ship to the browser) — not the admin key above.

## Known limitations / roadmap

- MySQL connection is currently local-only (`localhost:3306`); not yet configured for a deployed environment.
- Typesense is queried directly from the browser, which assumes it's reachable from wherever the frontend is served — will need reworking for deployment.
- CV identifier currently returns raw species-folder names (e.g. `Bald_Eagle_photos`); not yet cross-referenced against the `Birds` table for a full enriched result (rarity, description, canonical photo).
- Dataset averages ~7 images/species; a planned extension of the Wikimedia pull (pagination + higher per-species limits) aims to raise this, bounded by what Commons actually has for each species — some species (particularly extinct ones) have few or no surviving photographs.
- Model B (embedding/vector-database-based identification) is planned as a stronger-performing counterpart to the current from-scratch CNN.
- Not yet deployed — next major step is getting the frontend, backend, database, and Typesense running on a real server rather than localhost.

## AI usage disclosure

Portions of this codebase were written with AI assistance (Claude, GitHub Copilot, ChatGPT/duck.ai). Per-file citations with the specific prompt used are included as comments throughout the codebase where applicable.
