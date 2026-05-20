"""
IRS federal energy tax credits.

Two flagship federal credits under the Inflation Reduction Act:
  - 25C  Energy Efficient Home Improvement Credit
  - 25D  Residential Clean Energy Credit

These are federal, so city/zip_codes stay blank. Source-of-truth URLs are the
permanent IRS pages; we live-verify them on each run.

Source: irs.gov/credits-deductions/individuals/...
"""

from __future__ import annotations
from datetime import date
from typing import Iterator

from .base import Fetcher
from config import PRIMARY_STATE
from schema import IncentiveRecord


URL_25C = "https://www.irs.gov/credits-deductions/energy-efficient-home-improvement-credit"
URL_25D = "https://www.irs.gov/credits-deductions/residential-clean-energy-credit"
URL_OVERVIEW = "https://www.irs.gov/credits-deductions/individuals/energy-efficient-home-improvement-credit"


IRS_PROGRAMS: list[dict] = [
    {
        "program_name": "Federal Residential Clean Energy Credit (IRC §25D)",
        "incentive_type": "Tax Credits",
        "property_type": "Residential (any home owned and used by the taxpayer)",
        "description": (
            "Non-refundable federal income tax credit equal to 30% of the "
            "cost of qualified residential clean-energy property placed in "
            "service in the taxpayer's home. Eligible property: solar "
            "photovoltaic, solar water heating (non-pool/non-hot-tub), wind "
            "turbines, geothermal heat pumps, biomass fuel stoves, and "
            "battery storage technology with capacity of 3 kWh or greater. "
            "No annual or lifetime dollar cap. Excess credit can carry "
            "forward to future tax years. 30% rate runs through 2032, then "
            "steps down to 26% (2033) and 22% (2034)."
        ),
        "eligibility_criteria": (
            "Individual taxpayer; property must be installed on a home "
            "located in the United States that the taxpayer uses as a "
            "residence (primary or secondary, but not rentals). Must file "
            "IRS Form 5695 with federal income tax return. Equipment must "
            "be new (not used). Battery storage must be >= 3 kWh."
        ),
        "incentive_amount": "30% of qualified cost, no cap (30% through 2032; 26% 2033; 22% 2034)",
        "valid_until": "2034-12-31",
        "program_links": URL_25D,
    },
    {
        "program_name": "Federal Energy Efficient Home Improvement Credit (IRC §25C)",
        "incentive_type": "Tax Credits",
        "property_type": "Residential (primary residence in the U.S.)",
        "description": (
            "Federal income tax credit of 30% of the cost of qualified "
            "energy-efficiency improvements and residential energy property "
            "expenditures, subject to annual caps. Annual aggregate cap of "
            "$1,200 for most items, plus a separate $2,000 annual cap for "
            "heat pumps, heat pump water heaters, and biomass stoves. "
            "Per-item caps include: $600 for exterior windows/skylights, "
            "$250/door (max $500), $600 for central AC, $600 for furnaces/"
            "boilers, $150 for home energy audits. Available for tax years "
            "2023 through 2032."
        ),
        "eligibility_criteria": (
            "Individual taxpayer; improvement must be made to the taxpayer's "
            "principal residence located in the United States. Equipment "
            "must meet specified efficiency standards (typically ENERGY "
            "STAR Most Efficient or Consortium for Energy Efficiency Tier). "
            "Beginning tax year 2025, manufacturers must provide a Product "
            "Identification Number (PIN). File IRS Form 5695."
        ),
        "incentive_amount": "30% of cost; up to $1,200/yr aggregate + $2,000/yr for heat pumps/biomass",
        "valid_until": "2032-12-31",
        "program_links": URL_25C,
    },
    {
        "program_name": "Federal Home Energy Audit Credit (under §25C)",
        "incentive_type": "Tax Credits",
        "property_type": "Residential (primary residence)",
        "description": (
            "A subset of the §25C Energy Efficient Home Improvement Credit "
            "that specifically reimburses 30% of the cost of a qualified "
            "home energy audit performed by a certified auditor. Capped at "
            "$150 per year. Often the first step homeowners take before "
            "pursuing larger §25C improvements."
        ),
        "eligibility_criteria": (
            "Audit must be conducted by a Qualified Home Energy Auditor "
            "(certified by an approved certification program — e.g., BPI, "
            "RESNET). Audit must include a written report identifying "
            "significant and cost-effective energy efficiency improvements "
            "and an estimate of savings. Counts toward the §25C $1,200 "
            "annual aggregate cap."
        ),
        "incentive_amount": "30% of audit cost, capped at $150 per tax year",
        "valid_until": "2032-12-31",
        "program_links": URL_25C,
    },
]


def scrape(fetcher: Fetcher, max_programs: int | None = None) -> Iterator[IncentiveRecord]:
    print("[irs_energy] verifying IRS credit pages reachable")
    ok_25c = bool(fetcher.get(URL_25C))
    ok_25d = bool(fetcher.get(URL_25D))
    if not (ok_25c and ok_25d):
        print(f"[irs_energy] WARN: 25C reachable={ok_25c}, 25D reachable={ok_25d}")

    today = date.today().isoformat()
    count = 0
    for prog in IRS_PROGRAMS:
        rec = IncentiveRecord(
            program_name=prog["program_name"],
            state=PRIMARY_STATE,   # federal program but stored under FL row for FL CSV
            city=None,
            zip_codes=None,        # federal — no ZIP restriction
            incentive_type=prog["incentive_type"],
            property_type=prog["property_type"],
            description=prog["description"],
            eligibility_criteria=prog["eligibility_criteria"],
            incentive_amount=prog["incentive_amount"],
            valid_until=prog.get("valid_until"),
            updated_at=today,
            review_needed="No",
            program_links=prog["program_links"],
        )
        yield rec
        count += 1
        if max_programs and count >= max_programs:
            break
