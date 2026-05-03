"""Generate webapp/catalog.json from utils/seed_data.PRODUCTS.

Run after editing seed_data.py to refresh the WebApp catalog:

    python webapp/build_catalog.py

If you host the WebApp on GitHub Pages or similar, commit the resulting
``catalog.json`` so the static page sees it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.seed_data import CATEGORIES, PRODUCTS  # noqa: E402

# Optional: if you want product photos hosted with the webapp, point this at
# the public URL prefix (e.g. https://your-cdn/photos/). When empty, the
# WebApp will hide images that 404.
PHOTO_URL_PREFIX = ""  # e.g. "https://yourname.github.io/coffee-bot-webapp/photos/"


def _photo_url(asset_path: str) -> str:
    if not asset_path:
        return ""
    if asset_path.startswith(("http://", "https://")):
        return asset_path
    if not PHOTO_URL_PREFIX:
        return ""
    # asset_path is like "assets/photos/01_espresso.jpg"
    filename = Path(asset_path).name
    return PHOTO_URL_PREFIX.rstrip("/") + "/" + filename


def main() -> None:
    catalog = []
    for i, p in enumerate(PRODUCTS, start=1):
        catalog.append({
            "id": i,
            "category": p["category"],
            "emoji": CATEGORIES.get(p["category"], ""),
            "name": p["name"],
            "description": p["description"],
            "price": float(p["price"]),
            "photo": _photo_url(p.get("photo_url", "")),
        })

    out = ROOT / "webapp" / "catalog.json"
    out.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ wrote {out} ({len(catalog)} products)")


if __name__ == "__main__":
    main()
