import os
import time
from urllib.parse import urljoin

import requests

from fuel_finder.config import (
    load_dotenv,
    normalize_base_url,
    normalize_token_url,
)


load_dotenv()


class FuelFinderClient:
    """Small wrapper around the Fuel Finder API auth and pagination rules."""

    def __init__(self, base_url=None, token_url=None, client_id=None, client_secret=None):
        self.base_url = normalize_base_url(base_url or os.getenv("FUEL_FINDER_BASE_URL"))
        self.token_url = normalize_token_url(
            token_url or os.getenv("FUEL_FINDER_TOKEN_URL"),
            self.base_url,
        )
        self.client_id = (
            client_id
            or os.getenv("FUEL_FINDER_CLIENT_ID")
            or os.getenv("GOV_CLIENT_ID")
        )
        self.client_secret = (
            client_secret
            or os.getenv("FUEL_FINDER_CLIENT_SECRET")
            or os.getenv("GOV_CLIENT_SECRET")
        )
        self._access_token = None
        self._expires_at = 0

    def get_access_token(self):
        # Cache the bearer token in memory so one snapshot run does not request a
        # fresh token for every paginated API call.
        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "Missing Fuel Finder credentials. Set FUEL_FINDER_CLIENT_ID/"
                "FUEL_FINDER_CLIENT_SECRET or GOV_CLIENT_ID/GOV_CLIENT_SECRET."
            )

        if self._access_token and time.time() < self._expires_at:
            return self._access_token

        response = requests.post(
            self.token_url,
            json={"client_id": self.client_id, "client_secret": self.client_secret},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=20,
        )
        response.raise_for_status()
        token_response = response.json()
        data = token_response.get("data", token_response)

        if "access_token" not in data:
            raise RuntimeError(f"Token response did not include access_token: {token_response}")

        self._access_token = data["access_token"]
        self._expires_at = time.time() + data.get("expires_in", 3600) - 60
        return self._access_token

    def get(self, path, params=None):
        # Keep the request method deliberately thin: auth, URL joining, timeout,
        # and HTTP error propagation all happen here.
        token = self.get_access_token()
        url = urljoin(f"{self.base_url}/", path.lstrip("/"))
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get_all_batches(self, path, params=None):
        # Fuel Finder returns at most 500 records per batch. Stop when a short
        # batch arrives, which means there is no next page.
        params = dict(params or {})
        records = []
        batch_number = 1

        while True:
            batch_params = {**params, "batch-number": batch_number}
            batch = self.get(path, batch_params)
            if not batch:
                break

            records.extend(batch)
            if len(batch) < 500:
                break

            batch_number += 1

        return records

    def get_forecourts(self):
        return self.get_all_batches("/pfs")

    def get_fuel_prices(self):
        return self.get_all_batches("/pfs/fuel-prices")
