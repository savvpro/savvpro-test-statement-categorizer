"""Download the reference statement samples used by tests/test_parsing_bank_standards.py.

The four files are official public sample files that PostFinance publishes so that
software vendors can test camt.053 and MT940 imports. Their licence is not stated, so
they are kept out of git (tests/reference_cache/ is ignored) and fetched on demand.
The tests that need them skip themselves when the files are missing.

Usage, from the backend directory:

    python scripts/fetch_reference_samples.py
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://www.postfinance.ch/content/dam/pfch/doc/musterfile/"
SAMPLES = {
    "camt053_v2009.xml": "camt053_P_CH2909000000250094239_1110092698_0_2020062503071366_v2009.xml",
    "camt053_v2019.xml": "camt053_P_CH2909000000250094239_1110092698_0_2020112503071366_v2019.xml",
    "mt940_nocode.dat": "181119_MT940_P_CH2909000000250094239_1110092694_0_2019111902092045.dat",
    "mt940_code.dat": "181119_MT940_P_CH2909000000250094239_1110092695_0_2019111901432790.dat",
}
TARGET = Path(__file__).resolve().parents[1] / "tests" / "reference_cache"
TIMEOUT_SECONDS = 30
MAX_BYTES = 1024 * 1024


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "reference-sample-fetch/1.0"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
        body = response.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError(f"larger than the {MAX_BYTES // 1024} KiB limit")
    if not body:
        raise ValueError("empty response")
    return body


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name, remote in SAMPLES.items():
        destination = TARGET / name
        if destination.exists():
            print(f"skip   {name} (already present)")
            continue
        try:
            body = fetch(BASE + remote)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            failures += 1
            print(f"FAILED {name}: {exc}")
            continue
        destination.write_bytes(body)
        print(f"saved  {name} ({len(body)} bytes)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
