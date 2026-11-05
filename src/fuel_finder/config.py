import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_LAKE_ROOT = PROJECT_ROOT / "data_lake"
DEFAULT_GOVERNMENT_FUEL_PRICES_ROOT = DEFAULT_DATA_LAKE_ROOT / "government_fuel_prices"
DEFAULT_TRANSACTIONS_ROOT = DEFAULT_DATA_LAKE_ROOT / "transactions"
DEFAULT_BASE_URL = "https://www.fuel-finder.service.gov.uk/api/v1"


def load_dotenv(path=PROJECT_ROOT / ".env"):
    # Prefer python-dotenv when installed, but keep a tiny fallback so basic
    # scripts still run in lightweight environments.
    try:
        from dotenv import load_dotenv as _load_dotenv
    except ImportError:
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        return

    _load_dotenv(path)


def normalize_base_url(value):
    # The Fuel Finder docs and earlier project notes used a couple of base URL
    # variants. Normalize them so the rest of the code can always append paths.
    if not value:
        return DEFAULT_BASE_URL

    base_url = value.rstrip("/")
    if base_url == "https://api.fuelfinder.service.gov.uk":
        return DEFAULT_BASE_URL
    if not base_url.endswith("/api/v1"):
        return f"{base_url}/api/v1"
    return base_url


def normalize_token_url(value, base_url):
    # Token generation now lives under the same API base URL; this keeps older
    # .env files from pointing at the retired auth host.
    if not value or "auth.fuelfinder.service.gov.uk" in value:
        return f"{base_url}/oauth/generate_access_token"
    return value


def data_lake_root():
    # This can point at a OneDrive-backed folder later, but defaults to a local
    # ignored data_lake/ folder for development.
    return Path(os.getenv("FUEL_DATA_LAKE_ROOT", DEFAULT_DATA_LAKE_ROOT))


def government_fuel_prices_root(lake_root=None):
    root = Path(lake_root or data_lake_root())
    if root.name == "government_fuel_prices":
        return root
    return root / "government_fuel_prices"


def transactions_root(lake_root=None):
    root = Path(lake_root or data_lake_root())
    if root.name == "transactions":
        return root
    return root / "transactions"
