import os
import requests
import time
from pathlib import Path
from dotenv import load_dotenv
import csv
import re

# Loading .env
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

# Wikimedia asks that every request identify the calling app + a contact
# method. This isn't an API key -- it's a courtesy header they can use to
# reach you if your traffic causes problems, and they may rate-limit or
# block requests that don't include one.
CONTACT_EMAIL = os.getenv("WIKIMEDIA_CONTACT_EMAIL")

if not CONTACT_EMAIL:
    raise RuntimeError(
        "WIKIMEDIA_CONTACT_EMAIL is missing from the .env file. "
        "Wikimedia's API etiquette requires a contact identifier in the User-Agent."
    )

HEADERS = {
    "User-Agent": f"Avidex/0.92 (contact: {CONTACT_EMAIL})"
}

COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"









def _search_commons_images(query, limit=10, max_results=100):
    all_pages = []
    continue_token = None

    while len(all_pages) < max_results:
        remaining = max_results - len(all_pages)
        batch_limit = min(remaining, 50)

        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": batch_limit,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime",
            "format": "json",
        }

        if continue_token:
            params.update(continue_token)

        response = _fetch_with_retry(params=params,max_attempts=5)
        response.raise_for_status()
        data = response.json()

        if "query" not in data:
            break

        pages = list(data["query"]["pages"].values())
        all_pages.extend(pages)

        if "continue" in data:
            continue_token = data["continue"]
            # Pace every paginated follow-up request. This runs far more
            # often now than before, since one bird can trigger several
            # requests instead of just one.
            time.sleep(0.5)
        else:
            break

    return all_pages









def order_bird_photo_options(options):
    preferred = []
    options_copy = options.copy()

    for option in options:
        artist = option.get("artist") or ""

        if "inaturalist" in artist:
            preferred.append(option)
            options_copy.remove(option)

    preferred.extend(options_copy)
    return preferred




def _fetch_with_retry(params, max_attempts=4):
    """
    Makes one Commons API request, retrying with exponentially increasing
    waits if Commons responds with a rate-limit or server error. Raises
    the underlying error only after max_attempts is exhausted, so a bird
    that genuinely can't be reached still surfaces as a real failure
    rather than silently vanishing.
    """
    for attempt in range(1, max_attempts + 1):
        response = requests.get(COMMONS_API_URL, params=params, headers=HEADERS, timeout=10)

        # 429 = rate limited. 5xx = Commons-side server error, often transient.
        if response.status_code == 429 or response.status_code >= 500:
            if attempt == max_attempts:
                response.raise_for_status()  # out of retries -- let it fail loudly

            wait_time = 2 ** attempt  # 2s, 4s, 8s, 16s
            print(f"Rate limited/server error (status {response.status_code}), "
                  f"retrying in {wait_time}s (attempt {attempt}/{max_attempts})")
            time.sleep(wait_time)
            continue

        response.raise_for_status()  # raises for other error codes (4xx client errors)
        return response

    # Unreachable in practice, but keeps the function's contract clear.
    raise RuntimeError("Exceeded retry attempts without a definitive response")




def classify_description(description):
    """
    Classifies a Commons ImageDescription into a rough category based on
    caption patterns, to catch cases the OCR-junk filter and category
    filter both miss:

    - "synonym_note": scientific plate captions noting an old/current
      name pairing (e.g. "« X » = Y (Common Name)"). Common on
      illustration plates that aren't tagged with an "illustration"
      category, or where the plate itself is the search hit rather than
      a labeled scan.
    - "specimen": egg photos, museum/collection specimens -- real photos,
      but not useful for a live-bird CV dataset.
    - "photo": no red flags found. Not a guarantee it's a good photo,
      just that it didn't match a known bad pattern.

    Returns one of "synonym_note", "specimen", "photo".
    """
    if not description:
        return "photo"  # nothing to judge by -- don't discard on absence of info

    text = description.lower()

    

    # Guillemets (« ») and an "=" between two names are near-exclusive to
    # synonymy notes in plate captions ("old name = current name"). Real
    # photo captions essentially never use either.
    has_guillemets = "«" in description or "»" in description
    has_equals_between_italics = bool(re.search(r"</i>\s*=\s*<i>", description, re.IGNORECASE))

    if has_guillemets or has_equals_between_italics:
        return "synonym_note"

    # Egg photos and museum/collection specimens are real photographs,
    # but not photos of a live bird -- not useful for the CV task.
    specimen_keywords = [
        "egg of", "eggs of", "nest of",
    ]

    if any(keyword in text for keyword in specimen_keywords):
        return "specimen"

    return "photo"









def get_bird_photo_options(species, common_name=None, max_results=100):
    options = []

    for query in filter(None,[species,common_name]):
        pages = _search_commons_images(query,max_results=max_results)

        for page in pages:
            imageinfo = page.get("imageinfo")

            if not imageinfo:
                continue

            info = imageinfo[0]

            # Belt-and-suspenders check: only accept files whose MIME type
            # actually starts with "image/" -- catches anything the
            # filetype:image search filter let through by mistake
            mime = info.get("mime", "")
            if not mime.startswith("image/"):
                continue

            metadata = info.get("extmetadata", {})

            raw_description = metadata.get("ImageDescription", {}).get("value")

            # Discard OCR noise instead of storing it -- keeps identifyingMarks/description
            # from getting polluted with unreadable scan artifacts
            description_class = classify_description(raw_description)
            if description_class != "photo":
                continue

            options.append({
                "url": info.get("url"),
                "license": metadata.get("LicenseShortName", {}).get("value"),
                "artist": metadata.get("Artist", {}).get("value"),
                "description": raw_description,
                "categories": metadata.get("Categories", ()).get("value"),
            })

    if not options:
        return None

    options = order_bird_photo_options(options)
    
    return options









def write_bird_photo_urls(bird_urls_path="data/bird_urls.csv", processed_path="data/processed_birds.csv",max_results=100):
    with (open(bird_urls_path, "w",encoding="utf-8",newline="") as urls_file, open(processed_path, "r", encoding="utf-8",newline="") as read_file):
        reader = csv.reader(read_file)
        writer = csv.writer(urls_file)

        # Skip header rows -- otherwise the header itself gets compared
        # against bird data and flagged as "Hallucinated".
        next(reader, None)

        writer.writerow(["Common Name", "Species", "Url", "Image Description", "Category", "License", "Artist"])

        for index, row in enumerate(reader):
            commonName = row[1].strip()
            species = row[2].strip()

            photos = get_bird_photo_options(species, commonName,max_results=max_results)

            if photos == None:
                continue



            for index2, photo in enumerate(photos):
                if photo:

                    url = photo.get("url")
                    license = photo.get("license")
                    artist = photo.get("artist")
                    description = photo.get("description")
                    categories = photo.get("categories")

                    writer.writerow([commonName,species,url, description, categories, license, artist])
                continue
            print(f"Finished bird {index}  with {len(photos)} photos")

write_bird_photo_urls()