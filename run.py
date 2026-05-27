"""
Main entry point — full pipeline for a single image (Step 1 + 2).

Usage:
    python run.py <image_path> [output.csv]

Example:
    python run.py my_design.png
    python run.py my_design.png output/listings.csv
"""

import json
import sys
from pathlib import Path

from ai_vision import get_listing_from_image
from tm_check import check_listing
from csv_writer import write_csv


def run(image_path: str, output_csv: str = "output.csv", profile: dict | None = None):
    print(f"\n[1/3] Sending {image_path!r} to GPT-4o-mini…")
    listing = get_listing_from_image(image_path)
    print("      Done.")
    print(json.dumps({k: v for k, v in listing.items() if not k.startswith("_")}, indent=2, ensure_ascii=False))

    print("\n[2/3] Running trademark check…")
    tm = check_listing(listing)
    print(f"      {tm}")
    if tm.flagged:
        print("  ⚠️  WARNING: flagged terms found. Review before uploading to Amazon.")
        listing["_tm_flagged"] = True
        listing["_tm_hits"] = tm.hits

    print(f"\n[3/3] Writing CSV → {output_csv!r}…")
    path = write_csv([listing], output_csv, profile)
    print(f"      Saved: {path.resolve()}")

    return listing


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    img = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "output.csv"
    run(img, out)
