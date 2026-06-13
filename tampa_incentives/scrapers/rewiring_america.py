"""
Rewiring America scraper.

Two modes:
  1. API mode:    if REWIRING_AMERICA_API_KEY env var is set, calls the
                  /api/v1/calculator endpoint for a sample Tampa ZIP.
  2. Static mode: returns hard-coded federal IRA incentives. These are stable,
                  well-documented programs (25C, 25D, HEEHRA, HOMES) — safe to
                  treat as known constants for v1.

API signup: https://rewiring.link/api-signup
"""

from __future__ import annotations
import os
from datetime import date
from typing import Iterator

from .base import Fetcher
from config import PRIMARY_STATE
from schema import IncentiveRecord


API_URL = "https://api.rewiringamerica.org/api/v1/calculator"

# Tampa ZIPs to query for state/local coverage (only used in API mode).
SAMPLE_TAMPA_ZIPS = ["33602", "33603", "33647"]


# -----------------------------------------------------------------------------
# Static mode: known federal IRA programs (cross-checked vs IRS.gov, last
# verified 2026-04). These are nationwide so apply to every Tampa ZIP.
#
# NOTE: 25C and 25D were removed from this list — they are now authoritatively
# covered by scrapers/irs_energy.py (sourced directly from IRS.gov). This file
# now covers only the IRA programs NOT duplicated elsewhere: HEEHRA/HEAR,
# HOMES, and 30C EV charger.
# -----------------------------------------------------------------------------
FEDERAL_IRA_PROGRAMS: list[dict] = [
    {
        "program_name": "High-Efficiency Electric Home Rebate Act (HEEHRA / HEAR)",
        "incentive_type": "Rebates",
        "property_type": "Owner-occupied single-family or qualifying multifamily",
        "description": (
            "Point-of-sale rebates for low- and moderate-income households "
            "installing electric appliances and home upgrades — heat pumps, "
            "heat pump water heaters, electric stoves, electric panel upgrades, "
            "wiring, and insulation. Administered by states; Florida program "
            "rollout is in progress."
        ),
        "eligibility_criteria": (
            "Households at or below 150% of Area Median Income (AMI). "
            "Up to 100% of cost covered for households below 80% AMI; "
            "up to 50% for 80-150% AMI."
        ),
        "incentive_amount": (
            "Up to $14,000 per household, including $8,000 for heat pump, "
            "$1,750 for heat pump water heater, $840 for electric stove, "
            "$2,500 for wiring, $4,000 for panel upgrade"
        ),
        "valid_until": "2031-09-30",
        "program_links": "https://www.energy.gov/scep/home-energy-rebates-programs",
    },
    {
        "program_name": "HOMES Rebate Program",
        "incentive_type": "Rebates",
        "property_type": "Single-family or multifamily residential",
        "description": (
            "Whole-home efficiency rebates based on modeled or measured energy "
            "savings. Administered by states; Florida program rollout in "
            "progress. Stackable with 25C tax credit in many cases."
        ),
        "eligibility_criteria": (
            "Available to all income levels, but rebate amount doubles for "
            "households below 80% AMI. Must achieve at least 20% modeled "
            "energy savings to qualify."
        ),
        "incentive_amount": (
            "Up to $4,000 per household (or $8,000 for low-income); higher caps "
            "for multifamily on a per-unit basis"
        ),
        "valid_until": "2031-09-30",
        "program_links": "https://www.energy.gov/scep/home-energy-rebates-programs",
    },
    {
        "program_name": "Federal EV Charger Tax Credit (30C)",
        "incentive_type": "Tax Credits",
        "property_type": "Residential property in eligible census tract",
        "description": (
            "30% federal tax credit (up to $1,000 for residential, $100,000 for "
            "commercial) for installing a qualified EV charger. Property must "
            "be located in an eligible non-urban or low-income census tract."
        ),
        "eligibility_criteria": (
            "Property must be in a low-income community or non-urban census "
            "tract (per IRS Notice 2024-20). Filed with IRS Form 8911."
        ),
        "incentive_amount": "30% of cost, up to $1,000 (residential)",
        "valid_until": "2032-12-31",
        "program_links": "https://www.irs.gov/credits-deductions/alternative-fuel-vehicle-refueling-property-credit",
    },
]


def _from_static() -> Iterator[IncentiveRecord]:
    today = date.today().isoformat()
    for prog in FEDERAL_IRA_PROGRAMS:
        yield IncentiveRecord(
            program_name=prog["program_name"],
            state=PRIMARY_STATE,  # nationwide but our scope is FL
            city=None,             # statewide → per Dreamline rule, leave blank
            zip_code=None,
            incentive_type=prog["incentive_type"],
            property_type=prog["property_type"],
            description=prog["description"],
            eligibility_criteria=prog["eligibility_criteria"],
            incentive_amount=prog["incentive_amount"],
            valid_until=prog.get("valid_until"),
            updated_at=today,
            program_links=prog["program_links"],
        )


def _from_api(fetcher: Fetcher, api_key: str) -> Iterator[IncentiveRecord]:
    """Hit the live Rewiring America API for each sample Tampa ZIP."""
    fetcher.session.headers.update({"Authorization": f"Bearer {api_key}"})
    seen: set[str] = set()
    got_any = False
    
    for zip_code in SAMPLE_TAMPA_ZIPS:
        params = (
            f"?owner_status=homeowner&household_income=80000"
            f"&household_size=2&zip={zip_code}"
            f"&authority_types=federal"
        )
        url = API_URL + params
        print(f"[rewiring_america] querying {zip_code}")
        data = fetcher.get_json(url)
        if data:
            incentives = data.get('incentives', [])
            print(f"[rewiring_america] {zip_code}: {len(incentives)} incentives, coverage={data.get('coverage')}")
        if not data:
            continue
        for inc in data.get("incentives", []):
            got_any = True
            key = inc.get("program") or inc.get("short_description")
            if not key or key in seen:
                continue
            seen.add(key)
            yield _api_record_to_schema(inc)
    
    if not got_any:
        print("[rewiring_america] API returned no incentives, falling back to static")
        yield from _from_static()


def _api_record_to_schema(inc: dict) -> IncentiveRecord:
    """Map a Rewiring America API incentive object to our row schema."""
    type_map = {
        "tax_credit": "Tax Credits",
        "pos_rebate": "Rebates",
        "rebate": "Rebates",
        "performance_rebate": "Rebates",
        "account_credit": "Rebates",
        "assistance_program": "Grants",
    }
    payment = inc.get("payment_methods", [None])[0]
    incentive_type = type_map.get(payment) if payment else None

    return IncentiveRecord(
        program_name=inc.get("program") or inc.get("short_description") or "Unknown program",
        state=PRIMARY_STATE,
        incentive_type=incentive_type,
        property_type=", ".join(inc.get("owner_status", [])) or "homeowner",
        description=inc.get("short_description") or inc.get("program_description"),
        eligibility_criteria=inc.get("ami_qualification") or inc.get("payment_methods", [""])[0],
        incentive_amount=inc.get("amount", {}).get("representative") or str(inc.get("amount", {})),
        valid_until=inc.get("end_date"),
        updated_at=date.today().isoformat(),
        program_links=inc.get("program_url") or inc.get("more_info_url"),
    )


def scrape(fetcher: Fetcher, max_programs: int | None = None) -> Iterator[IncentiveRecord]:
    api_key = os.environ.get("REWIRING_AMERICA_API_KEY")
    if api_key:
        print("[rewiring_america] using live API")
        gen = _from_api(fetcher, api_key)
    else:
        print("[rewiring_america] no API key — using static federal IRA programs")
        gen = _from_static()

    count = 0
    for record in gen:
        yield record
        count += 1
        if max_programs and count >= max_programs:
            break
