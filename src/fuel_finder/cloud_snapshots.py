"""Fuel price snapshots pulled in the cloud (GitHub Actions), parked in Cloudflare R2, and synced down to this PC.

The cloud side (scripts/pull_snapshot_to_r2.py) uploads one gzipped snapshot per pull. The PC side
(scripts/sync_r2_snapshots.py (in the private analysis repo)) downloads each one, checks it, saves it into bronze exactly as a local pull would, and
only then deletes it from R2. This module holds what both sides must agree on, and imports nothing heavy (no pandas)
so the cloud run stays fast.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
from datetime import datetime, timezone

DATASET = "fuel-prices"
KEY_PREFIX = "fuel_prices/"
# fuel_prices/year=2026/month=11/day=05/fuel-prices_20261105T093712Z.json.gz
KEY_PATTERN = re.compile(
    r"^fuel_prices/year=(\d{4})/month=(\d{2})/day=(\d{2})/(fuel-prices_(\d{8}T\d{6}Z)\.json)\.gz$"
)
SHA_METADATA = "sha256"  # sha256 of the uncompressed JSON, stored with each object
RECORDS_METADATA = "records"


def snapshot_bytes(records) -> bytes:
    """The bronze JSON, byte for byte as fuel_finder.lake.parquet_writer.write_json writes it."""
    return json.dumps(records, indent=2).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def object_key(observed_at: datetime) -> str:
    stamp = observed_at.strftime("%Y%m%dT%H%M%SZ")
    return f"{KEY_PREFIX}year={observed_at:%Y}/month={observed_at:%m}/day={observed_at:%d}/{DATASET}_{stamp}.json.gz"


def parse_key(key: str):
    """Return (bronze relative path parts, observed_at) for a snapshot key, or None for anything else."""
    match = KEY_PATTERN.match(key)
    if not match:
        return None
    year, month, day, file_name, stamp = match.groups()
    observed_at = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    return (f"year={year}", f"month={month}", f"day={day}", file_name), observed_at


def compress(data: bytes) -> bytes:
    return gzip.compress(data, compresslevel=6, mtime=0)


def decompress(data: bytes) -> bytes:
    return gzip.decompress(data)


def r2_client():
    """boto3 S3 client pointed at Cloudflare R2. Needs R2_ACCOUNT_ID, R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY."""
    import boto3  # imported here so the rest of the module (and its tests) work without boto3

    missing = [name for name in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY") if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing R2 settings: {', '.join(missing)} (set them in .env or as GitHub secrets)")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def bucket_name() -> str:
    name = os.getenv("R2_BUCKET")
    if not name:
        raise RuntimeError("Missing R2_BUCKET (set it in .env or as a GitHub secret)")
    return name


def list_snapshot_objects(client, bucket):
    """Every object under fuel_prices/, oldest key first: [{'Key', 'Size'}, ...]."""
    objects, token = [], None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": KEY_PREFIX}
        if token:
            kwargs["ContinuationToken"] = token
        page = client.list_objects_v2(**kwargs)
        objects.extend({"Key": item["Key"], "Size": item["Size"]} for item in page.get("Contents", []))
        if not page.get("IsTruncated"):
            break
        token = page["NextContinuationToken"]
    return sorted(objects, key=lambda item: item["Key"])
