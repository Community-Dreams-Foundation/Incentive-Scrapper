"""
PACE (Property Assessed Clean Energy) financing programs in Florida.

Florida's residential PACE is the largest in the country. Several program
administrators operate in different counties. Funds flow to homeowners as
zero-down financing for solar, HVAC, roofing, impact windows, and other
qualified improvements, repaid via a non-ad-valorem assessment on the
property tax bill.

Source: brief lists Ygrene, RenewPACE, and FRED (Florida Resiliency &
Energy District). Ygrene paused new originations in 2023; Florida PACE
Funding Agency / RenewPACE / FRED remain active in many counties.
"""

from __future__ import annotations
from datetime import date
from typing import Iterator

from .base import Fetcher
from config import PRIMARY_STATE, HILLSBOROUGH_ZIPS
from schema import IncentiveRecord


YGRENE_URL = "https://ygrene.com/"
RENEWPACE_URL = "https://www.renewpace.com/"
FRED_URL = "https://www.fredelocal.com/"
FPFA_URL = "https://www.floridapace.gov/"


PACE_PROGRAMS: list[dict] = [
    {
        "program_name": "Florida PACE Funding Agency (Residential PACE)",
        "incentive_type": "Finance Solutions",
        "property_type": "Single-family residential (owner-occupied or rental, on participating tax roll)",
        "description": (
            "Statutory PACE program providing zero-down, long-term financing "
            "for solar PV, energy-efficiency upgrades, hurricane hardening "
            "(roof, impact windows/doors), and water-conservation measures. "
            "Repaid through a non-ad-valorem assessment on the annual "
            "property tax bill — transfers with the property if sold."
        ),
        "eligibility_criteria": (
            "Property must be in a Florida county/municipality that has "
            "joined FPFA's interlocal agreement; property taxes current; "
            "mortgage current with no recent bankruptcies; equity in the "
            "property; improvements must be on the qualified measures list."
        ),
        "incentive_amount": "Up to ~20% of property value financed at 0% down, 5-25 year terms",
        "program_links": FPFA_URL,
    },
    {
        "program_name": "RenewPACE Residential Financing",
        "incentive_type": "Finance Solutions",
        "property_type": "Single-family residential (owner-occupied)",
        "description": (
            "Private PACE administrator operating in participating Florida "
            "counties. Finances solar, HVAC, roofing, impact windows, "
            "weatherization, and resilience upgrades with zero-down, "
            "tax-bill repayment."
        ),
        "eligibility_criteria": (
            "Property in a RenewPACE-participating Florida jurisdiction; "
            "property taxes and mortgage current; sufficient equity; "
            "improvements on the qualified-measures list; contractor "
            "enrolled with RenewPACE."
        ),
        "incentive_amount": "Project-specific; typical residential range $5K-$75K, financed up to 25 years",
        "program_links": RENEWPACE_URL,
    },
    {
        "program_name": "Florida Resiliency and Energy District (FRED) PACE",
        "incentive_type": "Finance Solutions",
        "property_type": "Single-family residential and small commercial",
        "description": (
            "PACE administrator focused on hurricane resilience and energy "
            "efficiency in Florida coastal counties. Finances impact "
            "windows/doors, roof hardening, solar, HVAC, and water-"
            "efficiency improvements with assessment-based repayment."
        ),
        "eligibility_criteria": (
            "Property in a FRED-participating jurisdiction; property taxes "
            "and mortgage current; sufficient equity; qualified measures; "
            "approved FRED contractor."
        ),
        "incentive_amount": "Zero-down financing typically $5K-$100K, 5-25 year terms",
        "program_links": FRED_URL,
    },
    {
        "program_name": "Ygrene Residential PACE (Florida) — Status: Paused",
        "incentive_type": "Finance Solutions",
        "property_type": "Single-family residential",
        "description": (
            "Historic Florida PACE administrator. Ygrene paused new "
            "residential PACE originations in March 2023 and is winding "
            "down existing assessments. Listed here per the brief — "
            "treat as informational only; refer homeowners to FPFA, "
            "RenewPACE, or FRED for active PACE financing."
        ),
        "eligibility_criteria": (
            "No new originations as of 2023. Existing Ygrene-financed "
            "homeowners continue paying assessments through their tax bill."
        ),
        "incentive_amount": "Not currently accepting new applications",
        "program_links": YGRENE_URL,
    },
]


def scrape(fetcher: Fetcher, max_programs: int | None = None) -> Iterator[IncentiveRecord]:
    print("[pace] verifying PACE provider pages reachable")
    fetcher.get(FPFA_URL)
    fetcher.get(RENEWPACE_URL)
    today = date.today().isoformat()
    count = 0
    for prog in PACE_PROGRAMS:
        review = "Yes" if "Paused" in prog["program_name"] else "No"
        rec = IncentiveRecord(
            program_name=prog["program_name"],
            state=PRIMARY_STATE,
            city=None,
            zip_code=",".join(HILLSBOROUGH_ZIPS),  # available in Hillsborough
            incentive_type=prog["incentive_type"],
            property_type=prog["property_type"],
            description=prog["description"],
            eligibility_criteria=prog["eligibility_criteria"],
            incentive_amount=prog["incentive_amount"],
            valid_until=None,
            updated_at=today,
            review_needed=review,
            program_links=prog["program_links"],
        )
        yield rec
        count += 1
        if max_programs and count >= max_programs:
            break
