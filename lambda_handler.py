"""AWS Lambda entry point: pull one Fuel Finder price snapshot and upload it to R2.

Runs in the London region (eu-west-2) because the Fuel Finder API only accepts UK traffic. EventBridge Scheduler
calls it on a timer. Settings come from the function's environment variables (the same names as .env.example).
Handler setting in the Lambda console: lambda_handler.handler
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location("pull_snapshot_to_r2", ROOT / "scripts" / "pull_snapshot_to_r2.py")
_pull = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pull)


def handler(event, context):
    try:
        _pull.main()
    except SystemExit as stop:
        # The script stops with sys.exit("reason") when it refuses to upload. Raise instead, so Lambda records the
        # run as failed (and the failure alarm, if set up, emails you).
        if stop.code not in (None, 0):
            raise RuntimeError(str(stop.code)) from None
    return {"ok": True}
