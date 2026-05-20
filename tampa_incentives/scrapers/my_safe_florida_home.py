"""
My Safe Florida Home (MSFH) — hurricane mitigation grant program.

Statewide program administered by the Florida Department of Financial
Services. Provides matching grants to single-family homeowners for hurricane
hardening upgrades (roof, opening protection, etc.).

The brief specifically calls this out as the #1 missed-discovery program — up
to $10,000 most eligible homeowners have never heard of.

Source: mysafefloridahome.com
"""

from __future__ import annotations
from datetime import date
from typing import Iterator

from .base import Fetcher
from config import PRIMARY_STATE
from schema import IncentiveRecord


LANDING_URL = "https://mysafefloridahome.com/"
PROGRAM_INFO_URL = "https://mysafefloridahome.com/about/"


# Statewide program. Single record covers the headline grant; auxiliary
# inspection-only product is included as a separate record because eligibility
# differs (no income/insurance gate for the free inspection).
MSFH_PROGRAMS: list[dict] = [
    {
        "program_name": "My Safe Florida Home — Mitigation Grant",
        "incentive_type": "Grants",
        "property_type": "Single-family residential (owner-occupied, homestead)",
        "description": (
            "Florida-administered hurricane hardening grant. Reimburses "
            "$2 of qualifying mitigation work for every $1 the homeowner "
            "spends, up to a maximum state contribution of $10,000. Eligible "
            "improvements include roof deck attachment, secondary water "
            "resistance, roof-to-wall connections, opening protection "
            "(impact windows/doors), garage door reinforcement, and exterior "
            "door upgrades. Must follow a free wind mitigation inspection."
        ),
        "eligibility_criteria": (
            "Site-built single-family home with homestead exemption in "
            "Florida; insured value of $700,000 or less; located in the "
            "wind-borne debris region OR within 15 miles of the coast with "
            "wind speeds of 140 mph or greater; must complete the free "
            "MSFH wind mitigation inspection first; income-qualified low- "
            "and moderate-income applicants prioritized."
        ),
        "incentive_amount": "$2 state match per $1 homeowner spend, up to $10,000 in state funds per home",
        "program_links": "https://mysafefloridahome.com/grants/",
    },
    {
        "program_name": "My Safe Florida Home — Free Wind Mitigation Inspection",
        "incentive_type": "Grants",
        "property_type": "Single-family residential",
        "description": (
            "Free wind mitigation inspection by a state-approved inspector. "
            "Identifies hurricane vulnerabilities and qualifies the home for "
            "the MSFH matching grant. Inspection report can also be submitted "
            "to your homeowner's insurance carrier for potential premium "
            "discounts under FL Statute 627.0629."
        ),
        "eligibility_criteria": (
            "Site-built single-family Florida home; one free inspection per "
            "home per program cycle. No income test required for inspection."
        ),
        "incentive_amount": "Free inspection (state-funded, valued at ~$150)",
        "program_links": "https://mysafefloridahome.com/inspections/",
    },
]


def scrape(fetcher: Fetcher, max_programs: int | None = None) -> Iterator[IncentiveRecord]:
    print("[msfh] verifying program page is reachable")
    html = fetcher.get(LANDING_URL) or ""
    page_ok = bool(html)
    if not page_ok:
        print("[msfh] WARN: could not reach landing page; emitting curated records anyway")

    # Detect a "program paused / funding exhausted" message
    review_all = "No"
    if html:
        lower = html.lower()
        if "paused" in lower or "funding exhausted" in lower or "not currently accepting" in lower:
            print("[msfh] possible program pause detected on landing page")
            review_all = "Yes"

    today = date.today().isoformat()
    count = 0
    for prog in MSFH_PROGRAMS:
        description = prog["description"]
        review = review_all
        if review == "Yes":
            description += " [REVIEW: live page mentions program paused / funding exhausted]"

        rec = IncentiveRecord(
            program_name=prog["program_name"],
            state=PRIMARY_STATE,
            city=None,
            zip_codes=None,  # statewide
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
