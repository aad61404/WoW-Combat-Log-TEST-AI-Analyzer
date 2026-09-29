"""
Rebuild local-data/classic-test-reports.csv: public classic WCL report codes for manual live testing.

Source: GitHub issues/PRs (emulators, boss mods, bug trackers) whose body links a classic WCL report.
warcraftlogs.com itself blocks scraping (HTTP 403), so it cannot be crawled directly.

Usage (from repo root, ~2 min):  python3 scripts/find_classic_reports.py
Optional: GITHUB_TOKEN=<token> raises the search rate limit.
"""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

SITES = ("classic", "vanilla", "fresh", "sod")
OUTPUT = Path(__file__).resolve().parent.parent / "local-data" / "classic-test-reports.csv"
PAGE_SIZE = 100
MAX_PAGES = 10  # GitHub search returns at most 1000 results per query
SEARCH_DELAY_SECONDS = 7  # unauthenticated search allows 10 requests/minute
RETRIES = 3

REPORT_URL = re.compile(
    r"https?://(?:[a-z]{2}\.)?(classic|vanilla|fresh|sod)\.warcraftlogs\.com"
    r"/reports/([A-Za-z0-9]{16})([^\s)\]\"'<>]*)"
)

# Title-based guess only; the real zone/encounter must be confirmed through the WCL API.
RAID_PATTERNS = [
    ("ZG", r"zul'?gurub|\bzg\b|hakkar|mandokir|arlokk|jeklik|venoxis|mar'?li|thekal|jin'?do|gahz'?ranka|ohgan"),
    ("MC", r"molten core|\bmc\b|majordomo|golemagg|\bgarr\b|baron geddon|lucifron|magmadar|gehennas|shazzrah|sulfuron"),
    ("Onyxia", r"onyxia|deathbringer proc"),
    ("BWL", r"blackwing lair|\bbwl\b|nefarian|vaelastrasz|razorgore|broodlord|firemaw|ebonroc|flamegor|chromaggus"),
    ("AQ20/AQ40", r"ahn'?qiraj|\baq ?\d*\b|c'?thun|twin emperors|\bouro\b|viscidus|huhuran|skeram|fankriss|sartura|ossirian|\bmoam\b|\bburu\b|rajaxx|ayamiss|kurinnaxx"),
    ("Naxxramas", r"\bnaxx|kel'?thuzad|sapphiron|thaddius|patchwerk|loatheb|heigan|anub'?rekhan|faerlina|maexxna|\bnoth\b|gothik|four horse|grobbulus|gluth|razuvious"),
    ("TBC raids", r"karazhan|gruul|magtheridon|serpentshrine|tempest keep|kael'?thas|black temple|illidan|sunwell|hyjal|anetheron|archimonde|zul'?aman|vashj|supremus|gathios"),
    ("WotLK raids", r"ulduar|icecrown citadel|\bicc\b|lich king|yogg|mimiron|hodir|thorim|freya|algalon|trial of the crusader|sindragosa|putricide|festergut|rotface|marrowgar|halion|sartharion|malygos"),
    ("Cata raids", r"bastion of twilight|blackwing descent|firelands|dragon soul|deathwing|al'?akir|cho'?gall|baleroc|alysrazor|beth'?tilac|rhyolith"),
    ("SoD raids", r"gnomeregan|blackfathom|sunken temple|mekgineer|aku'?mai|kelris|atal'?alarion|shade of eranikus"),
]


def github_search(query: str, page: int) -> dict:
    # curl instead of urllib: the macOS python.org build often lacks CA certificates.
    url = (
        "https://api.github.com/search/issues"
        f"?per_page={PAGE_SIZE}&page={page}&q={urllib.parse.quote(query)}"
    )
    cmd = ["curl", "-sf", "-m", "30", "-A", "wcl-classic-reports", "-H", "Accept: application/vnd.github+json"]
    if token := os.environ.get("GITHUB_TOKEN"):
        cmd += ["-H", f"Authorization: Bearer {token}"]
    result = subprocess.run([*cmd, url], capture_output=True, check=True)
    return json.loads(result.stdout)


def search_site(site: str, reports: dict[str, dict]) -> None:
    query = f'"{site}.warcraftlogs.com/reports"'
    for page in range(1, MAX_PAGES + 1):
        for attempt in range(1, RETRIES + 1):
            try:
                data = github_search(query, page)
            except subprocess.CalledProcessError:
                data = None
            # GitHub can return a short page flagged incomplete_results; retry rather than stop early.
            if data is not None and not data.get("incomplete_results"):
                break
            print(f"  {site} page {page}: retry {attempt}/{RETRIES}", file=sys.stderr)
            time.sleep(30)
        if data is None:
            print(f"  {site} page {page}: failed, skipping", file=sys.stderr)
            continue

        for item in data["items"]:
            for found_site, code, fragment in REPORT_URL.findall(item.get("body") or ""):
                record = reports.setdefault(
                    code, {"site": found_site, "fights": set(), "title": item["title"], "source": item["html_url"]}
                )
                record["fights"].update(int(f) for f in re.findall(r"fight=(\d+)", fragment))

        total = data["total_count"]
        print(f"  {site} page {page}: {len(data['items'])} items of {total}, {len(reports)} codes", file=sys.stderr)
        time.sleep(SEARCH_DELAY_SECONDS)
        if page * PAGE_SIZE >= total:
            break


def guess_raid(title: str) -> str:
    text = title.lower()
    return "; ".join(name for name, pattern in RAID_PATTERNS if re.search(pattern, text)) or "unclassified"


def main() -> None:
    reports: dict[str, dict] = {}
    for site in SITES:
        print(f"Searching {site}...", file=sys.stderr)
        search_site(site, reports)

    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["code", "site", "url", "fight_ids", "raid_guess_from_title", "issue_title", "source"])
        for code, r in sorted(reports.items(), key=lambda item: (item[1]["site"], item[0])):
            writer.writerow([
                code,
                r["site"],
                f"https://{r['site']}.warcraftlogs.com/reports/{code}",
                " ".join(map(str, sorted(r["fights"]))),
                guess_raid(r["title"]),
                r["title"],
                r["source"],
            ])
    print(f"Wrote {len(reports)} reports to {OUTPUT}")


if __name__ == "__main__":
    main()
