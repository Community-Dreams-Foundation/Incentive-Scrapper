"""
FEMA Hazard Mitigation programs (federal).

Federal programs administered by FEMA, passed through state and local
governments. Funds flow to homeowners via local mitigation projects rather
than direct application. Statewide / nationwide eligibility — no ZIPs.

Source: fema.gov/grants/mitigation
"""

from __future__ import annotations
from datetime import date
from typing import Iterator

from .base import Fetcher
from config import PRIMARY_STATE
from schema import IncentiveRecord


LANDING_URL = "https://www.fema.gov/grants/mitigation"


FEMA_PROGRAMS: list[dict] = [
    {
        "program_name": "FEMA Hazard Mitigation Grant Program (HMGP)",
        "incentive_type": "Grants",
        "property_type": "Residential and non-residential (administered via state/local)",
        "description": (
            "Post-disaster federal funding for projects that reduce future "
            "disaster losses — home elevation, acquisition/buyout of flood-"
            "prone properties, wind retrofits, safe rooms, and infrastructure "
            "hardening. Activated after a Presidential disaster declaration; "
            "Florida is a frequent recipient post-hurricane."
        ),
        "eligibility_criteria": (
            "Applications submitted by states, tribes, territories, and "
            "local governments; homeowners participate via local sub-"
            "applicants. Property must be at risk of future hazards. "
            "Federal cost share generally 75% (higher for small impoverished "
            "communities)."
        ),
        "incentive_amount": "Up to 75% federal cost share; project totals commonly $30K-$300K+ per home for elevation/acquisition",
        "program_links": "https://www.fema.gov/grants/mitigation/hazard-mitigation",
    },
    {
        "program_name": "FEMA Building Resilient Infrastructure and Communities (BRIC)",
        "incentive_type": "Grants",
        "property_type": "Community and residential mitigation (via state/local sub-applicants)",
        "description": (
            "Annual competitive pre-disaster mitigation program funding "
            "infrastructure projects, building code adoption/enforcement, "
            "and capability- and capacity-building. Successor to the legacy "
            "PDM program."
        ),
        "eligibility_criteria": (
            "States, territories, federally recognized tribes, and local "
            "governments apply. Florida communities apply via FDEM. Property "
            "owners benefit indirectly through community-level resilience "
            "projects."
        ),
        "incentive_amount": "Up to 75% federal cost share; up to $50M per project for some categories",
        "program_links": "https://www.fema.gov/grants/mitigation/building-resilient-infrastructure-communities",
    },
    {
        "program_name": "FEMA Flood Mitigation Assistance (FMA)",
        "incentive_type": "Grants",
        "property_type": "Residential properties insured under NFIP",
        "description": (
            "Federal grants to states and local communities to reduce or "
            "eliminate flood-insurance claims on NFIP-insured structures. "
            "Funds elevation, acquisition/buyout, dry floodproofing, and "
            "minor localized flood reduction projects. Higher cost share "
            "available for Severe Repetitive Loss properties."
        ),
        "eligibility_criteria": (
            "Property must be insured by the National Flood Insurance "
            "Program (NFIP). Applications submitted by states, local "
            "governments, and tribes. Repetitive Loss and Severe Repetitive "
            "Loss properties prioritized."
        ),
        "incentive_amount": "Up to 75% federal cost share (100% for SRL properties)",
        "program_links": "https://www.fema.gov/grants/mitigation/floods",
    },
]


def scrape(fetcher: Fetcher, max_programs: int | None = None) -> Iterator[IncentiveRecord]:
    print("[fema] verifying landing page reachable")
    fetcher.get(LANDING_URL)
    today = date.today().isoformat()
    count = 0
    for prog in FEMA_PROGRAMS:
        rec = IncentiveRecord(
            program_name=prog["program_name"],
            state=PRIMARY_STATE,   # federal but tagged FL for FL CSV
            city=None,
            zip_codes=None,
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
