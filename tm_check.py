"""
Step 2a: Trademark filter.
Checks generated text against a local stop-list.
(Full USPTO/TESS API integration is a separate phase.)
"""

import re
from dataclasses import dataclass, field

# --- Local TM stop-list (seed set — extend as needed) ---
TM_STOPLIST: set[str] = {
    # Sports leagues / events
    "nfl", "nba", "mlb", "nhl", "mls", "ncaa",
    "super bowl", "world series", "stanley cup",
    "march madness", "final four",
    # Brands
    "harley", "harley-davidson", "davidson",
    "nasa", "supreme", "gucci", "louis vuitton",
    "adidas", "nike", "jordan",
    "coca-cola", "coke", "pepsi",
    "disney", "mickey", "minnie",
    "marvel", "dc comics", "batman", "superman",
    "star wars", "jedi", "sith", "mandalorian",
    "harry potter", "hogwarts",
    "pokemon", "pikachu",
    "patriots", "cowboys", "yankees",
    # Music bands
    "rolling stones", "beatles", "metallica",
    "acdc", "ac dc", "ac/dc",
    "led zeppelin", "zeppelin",
    "nirvana", "guns n roses",
    "iron maiden", "black sabbath",
    "pink floyd", "the who",
    # Misc protected
    "olympic", "olympics", "paralympic",
    "red cross", "unicef",
}


@dataclass
class TMResult:
    flagged: bool
    hits: list[str] = field(default_factory=list)

    def __str__(self):
        if not self.flagged:
            return "TM check: CLEAN"
        return f"TM check: FLAGGED — {', '.join(self.hits)}"


def _tokenize(text: str) -> list[str]:
    """Extract 1-, 2-, and 3-word phrases from text."""
    text = text.lower()
    # Replace / with space so "AC/DC" becomes "ac dc" before tokenizing
    text = text.replace("/", " ")
    words = re.findall(r"[a-z0-9'-]+", text)
    phrases = []
    for i, w in enumerate(words):
        phrases.append(w)
        if i + 1 < len(words):
            phrases.append(f"{w} {words[i+1]}")
        if i + 2 < len(words):
            phrases.append(f"{w} {words[i+1]} {words[i+2]}")
    return phrases


def check_listing(listing: dict) -> TMResult:
    """
    Check all text fields in a listing dict against the TM stop-list.
    Returns TMResult with flagged=True and the matching terms if found.
    """
    fields_to_check = ["title", "brand", "bullet_1", "bullet_2",
                       "bullet_3", "bullet_4", "bullet_5", "description"]

    combined = " ".join(str(listing.get(f, "")) for f in fields_to_check)
    phrases = set(_tokenize(combined))

    hits = sorted(phrases & TM_STOPLIST)
    return TMResult(flagged=bool(hits), hits=hits)
