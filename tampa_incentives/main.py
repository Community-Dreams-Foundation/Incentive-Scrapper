"""
Main orchestrator for the Tampa incentive extraction pipeline.

Usage:
    python main.py
    python main.py --dsire-only --max 10        # quick test
    python main.py --output mydata.csv

Output: a CSV with the 13 columns defined in config.OUTPUT_COLUMNS.
"""

from __future__ import annotations
import argparse
import csv
import sys
from pathlib import Path

from config import OUTPUT_COLUMNS, OUTPUT_FILENAME
from scrapers.base import Fetcher
from scrapers import (
    dsire,
    rewiring_america,
    teco,
    duke_energy,
    my_safe_florida_home,
    irs_energy,
    florida_housing,
    hillsborough,
    tampa_city,
    fema,
    pace,
    hillsborough_rebuilding,
)
from schema import IncentiveRecord


SCRAPERS = {
    "dsire": dsire.scrape,
    "rewiring_america": rewiring_america.scrape,
    "teco": teco.scrape,
    "duke_energy": duke_energy.scrape,
    "my_safe_florida_home": my_safe_florida_home.scrape,
    "irs_energy": irs_energy.scrape,
    "florida_housing": florida_housing.scrape,
    "hillsborough": hillsborough.scrape,
    "tampa_city": tampa_city.scrape,
    "fema": fema.scrape,
    "pace": pace.scrape,
    "hillsborough_rebuilding": hillsborough_rebuilding.scrape,
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tampa incentive scraper")
    p.add_argument(
        "--output",
        default=f"output/{OUTPUT_FILENAME}",
        help="Output CSV path",
    )
    p.add_argument(
        "--max",
        type=int,
        default=None,
        help="Cap programs per source (useful for smoke-testing)",
    )
    for name in SCRAPERS:
        p.add_argument(
            f"--{name.replace('_', '-')}-only",
            action="store_true",
            help=f"Run only the {name} scraper",
        )
    p.add_argument(
        "--skip",
        nargs="*",
        default=[],
        help="Scrapers to skip (e.g. --skip dsire)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # Figure out which scrapers to run
    only_flags = {n: getattr(args, f"{n}_only") for n in SCRAPERS}
    if any(only_flags.values()):
        active = [n for n, v in only_flags.items() if v]
    else:
        active = [n for n in SCRAPERS if n not in args.skip]

    print(f"Running scrapers: {active}")
    print()

    fetcher = Fetcher()
    records: list[IncentiveRecord] = []

    for name in active:
        scrape_fn = SCRAPERS[name]
        try:
            for rec in scrape_fn(fetcher, max_programs=args.max):
                records.append(rec)
        except Exception as e:
            import traceback
            print(f"[{name}] FAILED: {e}")
            traceback.print_exc()
        print()

    if not records:
        print("No records collected. Exiting with error.")
        return 1

    # Write CSV
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for rec in records:
            writer.writerow(rec.to_csv_row())

    # Summary
    by_type: dict[str, int] = {}
    review_count = 0
    for rec in records:
        key = rec.incentive_type or "(unmapped)"
        by_type[key] = by_type.get(key, 0) + 1
        if rec.review_needed == "Yes":
            review_count += 1

    print("=" * 60)
    print(f"Wrote {len(records)} records to {out_path}")
    print(f"  needs review: {review_count}")
    print(f"  by incentive_type:")
    for k, v in sorted(by_type.items(), key=lambda kv: -kv[1]):
        print(f"    {v:3d}  {k}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
