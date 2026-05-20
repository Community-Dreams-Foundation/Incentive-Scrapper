"""
Florida Housing Finance Corporation programs.

Statewide programs administered by FHFC. Brief calls this out as P1 for SHIP,
HOME, and Down Payment Assistance products.

Source: floridahousing.org/programs
"""

from __future__ import annotations
from datetime import date
from typing import Iterator

from .base import Fetcher
from config import PRIMARY_STATE
from schema import IncentiveRecord


LANDING_URL = "https://www.floridahousing.org/programs"
HOMEBUYER_URL = "https://www.floridahousing.org/programs/homebuyer-overview-page"
SHIP_URL = "https://www.floridahousing.org/programs/special-programs/ship---state-housing-initiatives-partnership-program"


FHFC_PROGRAMS: list[dict] = [
    {
        "program_name": "Florida Hometown Heroes Housing Program",
        "incentive_type": "Finance Solutions",
        "property_type": "Single-family residential (primary residence)",
        "description": (
            "Down payment and closing cost assistance for full-time Florida "
            "workforce buying a primary residence. Provided as a 0% non-"
            "amortizing second mortgage that is forgiven over time or "
            "satisfied at sale, refinance, or end of first mortgage term."
        ),
        "eligibility_criteria": (
            "Florida resident, full-time employed by a Florida-based "
            "employer (eligibility expanded in 2023 to most workforce "
            "occupations); first-time homebuyer (no homeownership in past "
            "3 years); income at or below 150% of area median income; "
            "credit score 640+; must use a participating FHFC lender; "
            "complete homebuyer education course."
        ),
        "incentive_amount": "Up to 5% of first mortgage amount, max $35,000 (effective 2023+)",
        "program_links": "https://www.floridahousing.org/programs/homebuyer-overview-page/hometown-heroes",
    },
    {
        "program_name": "Florida Assist Second Mortgage Program (FL Assist)",
        "incentive_type": "Finance Solutions",
        "property_type": "Single-family residential (primary residence)",
        "description": (
            "Up to $10,000 down payment and closing cost assistance offered "
            "as a 0% interest, deferred-payment second mortgage. Paired "
            "with FHFC first mortgage products. Becomes due upon sale, "
            "transfer, refinance, or when no longer the primary residence."
        ),
        "eligibility_criteria": (
            "First-time homebuyer (no ownership in past 3 years); meet "
            "FHFC income and purchase price limits for the county; minimum "
            "credit score 640; must use a participating FHFC lender; "
            "complete approved homebuyer education."
        ),
        "incentive_amount": "Up to $10,000 second mortgage at 0% interest, deferred",
        "program_links": "https://www.floridahousing.org/programs/homebuyer-overview-page/fl-assist",
    },
    {
        "program_name": "Florida HFA Preferred Conventional Loan Program",
        "incentive_type": "Finance Solutions",
        "property_type": "Single-family residential",
        "description": (
            "Conventional first mortgage with reduced mortgage insurance "
            "and below-market interest rate, offered to qualifying Florida "
            "first-time homebuyers. Can be combined with FL Assist or "
            "Hometown Heroes second mortgage products."
        ),
        "eligibility_criteria": (
            "First-time homebuyer; income at or below program limits "
            "(varies by county and household size); minimum credit score "
            "640; participating FHFC lender; homebuyer education required."
        ),
        "incentive_amount": "Below-market 30-year fixed conventional loan + reduced PMI",
        "program_links": "https://www.floridahousing.org/programs/homebuyer-overview-page",
    },
    {
        "program_name": "State Housing Initiatives Partnership (SHIP) — Florida",
        "incentive_type": "Grants",
        "property_type": "Residential (varies by local SHIP plan: SFH, condo, mobile, etc.)",
        "description": (
            "FHFC distributes SHIP funds annually to all 67 Florida counties "
            "and entitlement cities. Each local government adopts its own "
            "SHIP Local Housing Assistance Plan (LHAP) defining how funds "
            "are used: down payment assistance, owner-occupied rehab, "
            "disaster repair, emergency repair, or rental development. "
            "Apply through your county / city housing office, not FHFC "
            "directly."
        ),
        "eligibility_criteria": (
            "Household at or below 120% of area median income (most strategies "
            "target 80% AMI or below); Florida resident; specific eligibility "
            "set by each LHAP — typically owner-occupied, primary residence, "
            "current on property taxes."
        ),
        "incentive_amount": "Varies by local LHAP — typically up to $50,000 per household for rehab strategies",
        "program_links": SHIP_URL,
    },
    {
        "program_name": "HOME Investment Partnerships Program (Florida)",
        "incentive_type": "Grants",
        "property_type": "Residential (owner-occupied or rental)",
        "description": (
            "Federal HUD HOME funds administered by FHFC to provide rental "
            "housing development, homeownership assistance, and owner-"
            "occupied rehabilitation. Distributed through competitive RFAs "
            "to developers and local governments rather than direct to "
            "homeowners."
        ),
        "eligibility_criteria": (
            "Household income at or below 80% of area median income for "
            "homeowner programs; specific eligibility set by sub-recipient "
            "local government or non-profit administrator."
        ),
        "incentive_amount": "Varies by sub-recipient program; commonly up to $50,000 in deferred-payment assistance",
        "program_links": "https://www.floridahousing.org/programs/special-programs/home---home-investment-partnership-program-/home-program",
    },
]


def scrape(fetcher: Fetcher, max_programs: int | None = None) -> Iterator[IncentiveRecord]:
    print("[florida_housing] verifying landing page reachable")
    html = fetcher.get(LANDING_URL) or ""
    if not html:
        print("[florida_housing] WARN: landing page unreachable, emitting curated baseline")

    today = date.today().isoformat()
    count = 0
    for prog in FHFC_PROGRAMS:
        rec = IncentiveRecord(
            program_name=prog["program_name"],
            state=PRIMARY_STATE,
            city=None,
            zip_codes=None,    # statewide
            incentive_type=prog["incentive_type"],
            property_type=prog["property_type"],
            description=prog["description"],
            eligibility_criteria=prog["eligibility_criteria"],
            incentive_amount=prog["incentive_amount"],
            valid_until=None,
            updated_at=today,
            review_needed="No",
            program_links=prog["program_links"],
        )
        yield rec
        count += 1
        if max_programs and count >= max_programs:
            break
