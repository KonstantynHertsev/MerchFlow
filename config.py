import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"

# Amazon Merch hard limits
TITLE_MAX_CHARS = 120
BULLET_MAX_CHARS = 256
DESCRIPTION_MAX_CHARS = 2000
BRAND_MAX_CHARS = 50
KEYWORDS_MAX_CHARS = 500

# Amazon forbidden words (will be injected into system prompt)
AMAZON_STOP_WORDS = [
    "t-shirt", "tshirt", "shirt", "top", "tee",
    "high quality", "best quality", "premium quality",
    "eco-friendly", "eco friendly",
    "perfect gift", "great gift",
    "buy now", "limited edition",
    "100%", "guaranteed",
]

# Default profile values (user will override via UI later)
DEFAULT_PRICE = "19.99"
DEFAULT_COLORS = ["Black", "Navy", "Dark Heather", "Asphalt"]
DEFAULT_BRAND = "Independent Artist"
DEFAULT_DEPARTMENT = "mens"
DEFAULT_FIT = "standard"
