# fuel_price_collector

Pulls a snapshot of UK fuel prices from the government [Fuel Finder](https://www.fuel-finder.service.gov.uk) API every
30 minutes and uploads it gzipped to a private Cloudflare R2 bucket. A separate private project downloads the
snapshots, checks them, saves them locally and deletes them from R2.

This repo holds code only: no data and no keys.

## Where it runs

AWS Lambda in the London region (eu-west-2), started every 30 minutes by EventBridge Scheduler. The Fuel Finder API
only accepts UK traffic, so GitHub Actions (US servers) cannot be used: its token request gets 403 Forbidden.

- `lambda_handler.py`: the Lambda entry point (handler `lambda_handler.handler`)
- `scripts/pull_snapshot_to_r2.py`: logs in, pulls every batch of prices, gzips the JSON and uploads it as
  `fuel_prices/year=YYYY/month=MM/day=DD/fuel-prices_<UTC stamp>.json.gz`, with the sha256 of the uncompressed JSON
  in the object's metadata. Warns over 1 GB waiting in the bucket and refuses to upload over 8 GB (so R2 storage
  stays free).
- `build_lambda.py`: builds `dist/fuel_collector_lambda.zip` to upload to Lambda (boto3 comes with the runtime)

## Settings

Locally in `.env` (copy `.env.example`); on AWS as the Lambda function's environment variables.

| Name | What |
|---|---|
| `FUEL_FINDER_CLIENT_ID`, `FUEL_FINDER_CLIENT_SECRET` | Fuel Finder API login |
| `R2_ACCOUNT_ID` | Cloudflare account id |
| `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` | R2 API token, Object Read & Write on the one bucket |
| `R2_BUCKET` | Bucket name |

## Run it locally (Windows)

1. Copy `.env.example` to `.env` and fill it in (`.env` is never committed).
2. `setup.bat` once: creates `.venv` here and installs `requirements.txt`.
3. `run_collector.bat`: pulls one snapshot and uploads it to R2.

## Update the Lambda code

```
.venv\Scripts\python build_lambda.py
```

then in the Lambda console: Code -> Upload from -> .zip file -> `dist/fuel_collector_lambda.zip`.
