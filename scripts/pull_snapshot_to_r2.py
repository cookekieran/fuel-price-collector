"""Pull one Fuel Finder price snapshot and upload it, gzipped, to Cloudflare R2. Run by GitHub Actions.

Nothing is written locally. scripts/sync_r2_snapshots.py (in the private analysis repo) later brings each snapshot down into bronze on the PC and
deletes it from R2. Every pull is uploaded (unchanged or partial ones too): the sync applies the same no-update and
completeness rules as a local pull, so both routes end up the same in bronze and in ingestion_runs.jsonl.

Settings (environment variables / GitHub secrets):
    FUEL_FINDER_CLIENT_ID, FUEL_FINDER_CLIENT_SECRET   the API login (base and token URLs have defaults)
    R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET

Usage:
    python scripts/pull_snapshot_to_r2.py
"""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fuel_finder import cloud_snapshots as cs  # noqa: E402
from fuel_finder.sources.fuel_finder_client import FuelFinderClient  # noqa: E402

# Snapshots pile up in R2 only while the PC has not synced. R2's free storage is 10 GB a month.
WARN_BUCKET_BYTES = 1_000_000_000  # yellow warning on the run page
STOP_BUCKET_BYTES = 8_000_000_000  # refuse to upload (the run fails, and GitHub emails you), so storage never costs money


def main():
    started = time.monotonic()
    observed_at = datetime.now(timezone.utc).replace(microsecond=0)
    client, bucket = cs.r2_client(), cs.bucket_name()
    waiting = cs.list_snapshot_objects(client, bucket)
    total = sum(item["Size"] for item in waiting)
    print(f"bucket holds {len(waiting)} snapshots not yet synced ({total / 1e6:.0f} MB)")
    if total > STOP_BUCKET_BYTES:
        sys.exit(
            f"{total / 1e9:.1f} GB already waiting in R2, over the {STOP_BUCKET_BYTES / 1e9:.0f} GB safety limit: "
            "nothing uploaded. Run scripts/sync_r2_snapshots.py on the PC."
        )
    if total > WARN_BUCKET_BYTES:
        # A ::warning:: line shows as a yellow annotation on the run's summary page.
        print(f"::warning::{total / 1e9:.1f} GB waiting in R2. Run scripts/sync_r2_snapshots.py on the PC.")

    records = FuelFinderClient().get_fuel_prices()
    if not records:
        sys.exit("The API returned no records; nothing uploaded.")

    raw = cs.snapshot_bytes(records)
    body = cs.compress(raw)
    key = cs.object_key(observed_at)
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
        ContentEncoding="gzip",
        Metadata={cs.SHA_METADATA: cs.sha256(raw), cs.RECORDS_METADATA: str(len(records))},
    )
    print(f"uploaded {key}: {len(records):,} records, {len(raw) / 1e6:.1f} MB -> {len(body) / 1e6:.2f} MB gzipped")
    print(f"done in {time.monotonic() - started:.1f}s")


if __name__ == "__main__":
    main()
