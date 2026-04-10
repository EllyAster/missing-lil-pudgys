import os
from pathlib import Path

# Lil Pudgys image API
LIL_IMAGE_URL = "https://api.pudgypenguins.io/lil/image/{id}"

# OpenSea API key — read from environment variable first, then from the key file.
_KEY_FILE = Path(__file__).parent.parent / "sample_data" / "opensea_key.txt"
_PLACEHOLDER = "PASTE_YOUR_OPENSEA_API_KEY_HERE"


def _load_api_key() -> str:
    # 1. Environment variable takes priority (for Docker / CI usage)
    key = os.environ.get("OPENSEA_API_KEY", "").strip()
    if key:
        return key
    # 2. Fall back to the key file
    if _KEY_FILE.exists():
        key = _KEY_FILE.read_text().strip()
        if key and key != _PLACEHOLDER:
            return key
    return ""


OPENSEA_API_KEY = _load_api_key()

OPENSEA_BEST_LISTING_URL = (
    "https://api.opensea.io/api/v2/listings/collection/{slug}/nfts/{identifier}/best"
)
PUDGY_PENGUINS_SLUG = "pudgypenguins"
PUDGY_PENGUINS_CONTRACT = "0xBd3531dA5CF5857e7CfAA92426877b022e612cf8"
OPENSEA_NFT_BASE_URL = (
    "https://opensea.io/assets/ethereum/{contract}/{token_id}"
)

# HTTP defaults
DEFAULT_CONCURRENCY = 5
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
