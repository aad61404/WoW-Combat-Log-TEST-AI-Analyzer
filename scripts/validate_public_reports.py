"""Validate the curated public WCL candidates without saving player data.

Run from the repository root after configuring WCL_CLIENT_ID and
WCL_CLIENT_SECRET in .env:

    .venv/bin/python scripts/validate_public_reports.py

On Windows, use .venv\\Scripts\\python.exe instead.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.services.wcl_client import WCLClient  # noqa: E402


CANDIDATES = ROOT / "data" / "public-report-candidates.json"


async def main() -> int:
    manifest = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    client = WCLClient()
    failures = 0

    try:
        for candidate in manifest["reports"]:
            code = candidate["code"]
            try:
                report = await client.get_report(code)
            except Exception as error:
                failures += 1
                print(f"FAIL {code}: {error}")
                continue

            kills = sum(fight.kill for fight in report.fights)
            wipes = len(report.fights) - kills
            encounters = sorted({fight.encounter_id for fight in report.fights})
            # Deliberately omit title, owner, actors, and character names.
            print(
                f"OK   {code}: fights={len(report.fights)} kills={kills} "
                f"wipes={wipes} encounters={encounters}"
            )
    finally:
        await client.close()

    print(f"\nValidated {len(manifest['reports']) - failures}/{len(manifest['reports'])} reports.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
