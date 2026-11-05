# fuel_price_collector

Pulls a snapshot of UK fuel prices from the government [Fuel Finder](https://www.fuel-finder.service.gov.uk) API every
30 minutes with GitHub Actions, and uploads it gzipped to a private Cloudflare R2 bucket. A separate private project
downloads the snapshots, checks them, saves them locally and deletes them from R2.

This repo holds code only: no data and no keys.

## How it runs

- `.github/workflows/collect.yml`: every 30 minutes (at :07 and :37), plus a weekly heartbeat commit so GitHub does
  not turn the schedule off after 60 days without activity. It can also be started by hand from the Actions tab.
- `scripts/pull_snapshot_to_r2.py`: logs in, pulls every batch of prices, gzips the JSON and uploads it as
  `fuel_prices/year=YYYY/month=MM/day=DD/fuel-prices_<UTC stamp>.json.gz`, with the sha256 of the uncompressed JSON in
  the object's metadata. It warns on the run page when more than 1 GB is waiting in the bucket.

## Secrets (Settings -> Secrets and variables -> Actions)

| Secret | What |
|---|---|
| `FUEL_FINDER_CLIENT_ID`, `FUEL_FINDER_CLIENT_SECRET` | Fuel Finder API login |
| `R2_ACCOUNT_ID` | Cloudflare account id |
| `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` | R2 API token, Object Read & Write on the one bucket |
| `R2_BUCKET` | Bucket name |

## Run it locally (Windows)

Everything needed is in this folder; nothing else on the PC is used.

1. Copy `.env.example` to `.env` and fill it in (`.env` is never committed).
2. `setup.bat` once: creates `.venv` here and installs `requirements.txt`.
3. `run_collector.bat`: pulls one snapshot and uploads it to R2.
