"""
Main orchestrator for the Tampa incentive extraction pipeline.

Usage:
    python main.py                          # full run, all sources
    python main.py --dsire-only --max 10   # quick smoke-test
    python main.py --skip dsire fema       # skip specific sources
    python main.py --output mydata.csv     # custom combined output path

Outputs (all under output/):
    <name>_extracted_tampa_incentives.csv  -- combined record from all active scrapers
    by_source/<scraper>.csv               -- one file per scraper (new programs isolated here)
    program_geo.csv                       -- program_name, source, zip_code (geo lookup table)
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

GEO_COLUMNS = ["program_name", "source", "zip_code"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tampa incentive scraper")
    p.add_argument(
        "--output",
        default=f"output/{OUTPUT_FILENAME}",
        help="Combined output CSV path (default: output/<OUTPUT_FILENAME>)",
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
        help="Scrapers to skip (e.g. --skip dsire fema)",
    )
    return p.parse_args()


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()

    # Determine active scrapers
    only_flags = {n: getattr(args, f"{n}_only") for n in SCRAPERS}
    if any(only_flags.values()):
        active = [n for n, v in only_flags.items() if v]
    else:
        active = [n for n in SCRAPERS if n not in (args.skip or [])]

    print(f"Running scrapers: {active}\n")

    fetcher = Fetcher()
    all_records: list[IncentiveRecord] = []
    by_source: dict[str, list[IncentiveRecord]] = {}

    for name in active:
        scrape_fn = SCRAPERS[name]
        source_records: list[IncentiveRecord] = []
        try:
            for rec in scrape_fn(fetcher, max_programs=args.max):
                source_records.append(rec)
                all_records.append(rec)
        except Exception as e:
            import traceback
            print(f"[{name}] FAILED: {e}")
            traceback.print_exc()
        by_source[name] = source_records
        print()

    if not all_records:
        print("No records collected. Exiting with error.")
        return 1

    out_path = Path(args.output)

    # 1. Combined output
    _write_csv(out_path, OUTPUT_COLUMNS, [r.to_csv_row() for r in all_records])
    print(f"Combined:  {out_path}  ({len(all_records)} records)")

    # 2. Per-scraper files → output/by_source/<name>.csv
    by_source_dir = out_path.parent / "by_source"
    for name, recs in by_source.items():
        if not recs:
            continue
        src_path = by_source_dir / f"{name}.csv"
        _write_csv(src_path, OUTPUT_COLUMNS, [r.to_csv_row() for r in recs])
        print(f"  {name}: {src_path}  ({len(recs)} records)")

    # 3. program_geo.csv — one row per program with its ZIP list
    geo_rows: list[dict] = []
    for name, recs in by_source.items():
        for rec in recs:
            geo_rows.append({
                "program_name": rec.program_name,
                "source": name,
                "zip_code": rec.zip_code or "",
            })
    geo_path = out_path.parent / "program_geo.csv"
    _write_csv(geo_path, GEO_COLUMNS, geo_rows)
    print(f"Geo:       {geo_path}  ({len(geo_rows)} rows)")

    # Summary
    by_type: dict[str, int] = {}
    review_count = 0
    for rec in all_records:
        key = rec.incentive_type or "(unmapped)"
        by_type[key] = by_type.get(key, 0) + 1
        if rec.review_needed == "Yes":
            review_count += 1

    print()
    print("=" * 60)
    print(f"Total: {len(all_records)} records  |  needs review: {review_count}")
    print("  by incentive_type:")
    for k, v in sorted(by_type.items(), key=lambda kv: -kv[1]):
        print(f"    {v:3d}  {k}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
