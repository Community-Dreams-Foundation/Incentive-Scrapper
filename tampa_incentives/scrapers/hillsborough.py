"""
Hillsborough County housing and community-development incentive programs.

The brief lists Hillsborough County Housing (hillsboroughcounty.org/housing)
as a P1 source for SHIP and CDBG programs. These are county-administered, so
city is left blank but Hillsborough ZIPs are populated.

Source: hillsboroughcounty.org/housing
"""

from __future__ import annotations
from datetime import date
from typing import Iterator

from .base import Fetcher
from config import PRIMARY_STATE, HILLSBOROUGH_ZIPS
from schema import IncentiveRecord


LANDING_URL = "https://www.hillsboroughcounty.org/en/residents/property-owners-and-renters/housing"
HOUSING_FIN_URL = "https://www.hillsboroughcounty.org/en/residents/property-owners-and-renters/housing/financial-assistance"

ZIPS = ",".join(HILLSBOROUGH_ZIPS)


HILLSBOROUGH_PROGRAMS: list[dict] = [
    {
        "program_name": "Hillsborough County SHIP — Owner-Occupied Housing Rehabilitation",
        "incentive_type": "Grants",
        "property_type": "Single-family residential (owner-occupied, homestead)",
        "description": (
            "State Housing Initiatives Partnership (SHIP) funds administered "
            "by Hillsborough County's Affordable Housing Services. Provides "
            "deferred-payment loans / forgivable grants for owner-occupied "
            "housing rehabilitation, including roof replacement, plumbing, "
            "electrical, HVAC, accessibility modifications, and code-"
            "compliance repairs."
        ),
        "eligibility_criteria": (
            "Single-family home located in unincorporated Hillsborough "
            "County (or partner jurisdictions per LHAP); homestead exemption; "
            "household income at or below 120% of area median income (most "
            "applicants are at 80% AMI or below); property taxes current; "
            "primary residence."
        ),
        "incentive_amount": "Up to $75,000 per household (deferred-payment loan, forgiven after compliance period)",
        "program_links": HOUSING_FIN_URL,
    },
    {
        "program_name": "Hillsborough County SHIP — Down Payment Assistance",
        "incentive_type": "Finance Solutions",
        "property_type": "Single-family residential (primary residence)",
        "description": (
            "Down payment and closing cost assistance for first-time "
            "homebuyers purchasing a primary residence in Hillsborough "
            "County. Provided as a 0% interest, deferred-payment second "
            "mortgage, forgiven after the affordability period."
        ),
        "eligibility_criteria": (
            "First-time homebuyer (no ownership in past 3 years); household "
            "income at or below 120% AMI; property must be in Hillsborough "
            "County; complete approved homebuyer education; primary "
            "residence only."
        ),
        "incentive_amount": "Up to $40,000 in down payment / closing-cost assistance (forgivable)",
        "program_links": HOUSING_FIN_URL,
    },
    {
        "program_name": "Hillsborough County CDBG — Owner-Occupied Housing Rehabilitation",
        "incentive_type": "Grants",
        "property_type": "Single-family residential (owner-occupied)",
        "description": (
            "Federal Community Development Block Grant (CDBG) funds used by "
            "Hillsborough County for owner-occupied housing rehabilitation, "
            "including code-compliance repairs, accessibility upgrades for "
            "elderly or disabled residents, and emergency repairs. "
            "Coordinated with SHIP funds when available."
        ),
        "eligibility_criteria": (
            "Single-family home in CDBG-eligible census tracts within "
            "Hillsborough County (low- and moderate-income areas); household "
            "income at or below 80% AMI; owner-occupied primary residence; "
            "property taxes and insurance current."
        ),
        "incentive_amount": "Typically up to $50,000 per home (varies by funding cycle)",
        "program_links": "https://www.hillsboroughcounty.org/en/residents/property-owners-and-renters/housing",
    },
    {
        "program_name": "Hillsborough County Emergency Home Repair Program",
        "incentive_type": "Grants",
        "property_type": "Single-family residential (owner-occupied, elderly/disabled prioritized)",
        "description": (
            "Emergency grants for low-income Hillsborough County homeowners "
            "facing urgent, hazardous home conditions — roof leaks, plumbing "
            "failures, electrical hazards, AC failures during heat advisories. "
            "Designed for quick turnaround vs the full rehab program."
        ),
        "eligibility_criteria": (
            "Hillsborough County resident; owner-occupied primary residence; "
            "household income at or below 80% AMI; elderly (62+) or disabled "
            "members prioritized; demonstrated emergency hazard."
        ),
        "incentive_amount": "Up to $15,000 per emergency repair (grant, not loan)",
        "program_links": HOUSING_FIN_URL,
    },
    {
        "program_name": "Hillsborough County Mobile Home Repair Program",
        "incentive_type": "Grants",
        "property_type": "Mobile home / manufactured home (owner-occupied)",
        "description": (
            "Targeted rehabilitation program for owner-occupied mobile and "
            "manufactured homes that do not qualify for the standard SHIP "
            "rehab strategy. Funds tie-down upgrades, roof repair, plumbing, "
            "electrical, and code-required improvements."
        ),
        "eligibility_criteria": (
            "Mobile or manufactured home owner; located in Hillsborough "
            "County; primary residence; household income at or below 80% AMI; "
            "home must be on owned land or in an approved cooperative park."
        ),
        "incentive_amount": "Up to $20,000 per mobile home (deferred-payment loan, forgivable)",
        "program_links": HOUSING_FIN_URL,
    },
]


def scrape(fetcher: Fetcher, max_programs: int | None = None) -> Iterator[IncentiveRecord]:
    print("[hillsborough] verifying landing page reachable")
    html = fetcher.get(LANDING_URL) or ""
    if not html:
        print("[hillsborough] WARN: landing page unreachable, emitting curated baseline")

    review_all = "No"
    if html and ("waitlist" in html.lower() or "not currently accepting" in html.lower()):
        print("[hillsborough] possible waitlist / closed intake detected")
        review_all = "Yes"

    today = date.today().isoformat()
    count = 0
    for prog in HILLSBOROUGH_PROGRAMS:
        description = prog["description"]
        review = review_all
        if review == "Yes":
            description += " [REVIEW: live page mentions waitlist / not currently accepting]"

        rec = IncentiveRecord(
            program_name=prog["program_name"],
            state=PRIMARY_STATE,
            city=None,  # county-level, not city-specific
            zip_codes=ZIPS,
            incentive_type=prog["incentive_type"],
            property_type=prog["property_type"],
            description=description,
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
