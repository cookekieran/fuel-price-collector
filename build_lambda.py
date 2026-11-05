r"""Build dist/fuel_collector_lambda.zip, ready to upload to AWS Lambda (Python 3.12, x86_64).

The zip holds lambda_handler.py, scripts/pull_snapshot_to_r2.py, src/fuel_finder and the Linux build of requests.
boto3 is not included: the Lambda Python runtime already has it.

Usage (from this folder):
    .venv\Scripts\python build_lambda.py
"""
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ZIP = ROOT / "dist" / "fuel_collector_lambda.zip"
CODE = ["lambda_handler.py", "scripts/pull_snapshot_to_r2.py", "src/fuel_finder"]


def main():
    # Build in a temporary folder outside OneDrive (OneDrive can lock files while it syncs).
    with tempfile.TemporaryDirectory() as folder:
        build(Path(folder))


def build(BUILD):
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--quiet",
         "--target", str(BUILD), "--platform", "manylinux2014_x86_64", "--implementation", "cp",
         "--python-version", "3.12", "--only-binary=:all:", "requests>=2.31,<3"],
        check=True,
    )
    for item in CODE:
        source = ROOT / item
        if source.is_dir():
            shutil.copytree(source, BUILD / item, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            (BUILD / item).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, BUILD / item)

    ZIP.parent.mkdir(exist_ok=True)
    ZIP.unlink(missing_ok=True)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(BUILD.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.parts[len(BUILD.parts)] != "bin":
                archive.write(path, path.relative_to(BUILD).as_posix())
    print(f"built {ZIP} ({ZIP.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
