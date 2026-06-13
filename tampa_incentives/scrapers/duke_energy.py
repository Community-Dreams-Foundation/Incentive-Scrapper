"""
Duke Energy Florida residential rebates scraper.

Duke serves Pinellas, Pasco, parts of Hernando + 35 FL counties, but NOT the
City of Tampa (TECO territory). Included because the brief lists Duke as a P1
source for the Tampa Bay MSA and many adjacent ZIPs are Duke territory.

Approach (same as TECO):
  1. Live-fetch the rebates landing page to detect program closures.
  2. Emit curated baseline of currently active Duke FL residential programs.

Source: duke-energy.com/home/products (FL-specific rebate pages)
"""

from __future__ import annotations
from datetime import date
from typing import Iterator

from .base import Fetcher
from config import PRIMARY_STATE
from schema import IncentiveRecord


LANDING_URL = "https://www.duke-energy.com/home/products"
FL_REBATES_URL = "https://www.duke-energy.com/home/products/save-energy-and-money"


# Duke FL service territory is multi-county; do NOT pin to a single city.
# Leave city/zip_code blank — territory eligibility is enforced via the
# "Duke Energy Florida customer" eligibility criterion.
DUKE_PROGRAMS: list[dict] = [
    {
        "program_name": "Duke Energy Florida Smart $aver — Central AC Tier 1",
        "incentive_type": "Rebates",
        "property_type": "Residential (single-family, owner-occupied)",
        "description": (
            "Tier 1 Smart $aver rebate for installing a qualifying high-"
            "efficiency central air conditioner. Lower-tier SEER2 / EER2 "
            "requirements with a modest rebate."
        ),
        "eligibility_criteria": (
            "Duke Energy Florida residential customer; installation by "
            "participating Smart $aver contractor; equipment meets Tier 1 "
            "SEER2/EER2 minimums."
        ),
        "incentive_amount": "Up to $175 per Tier 1 central AC unit",
        "program_links": "https://www.duke-energy.com/home/products/smart-saver",
    },
    {
        "program_name": "Duke Energy Florida Smart $aver — Central AC Tier 2 (High Efficiency)",
        "incentive_type": "Rebates",
        "property_type": "Residential",
        "description": (
            "Top-tier Smart $aver rebate for the highest-efficiency "
            "central AC equipment qualifying under Duke's specification "
            "(higher SEER2). Best-fit for AC replacements in older homes "
            "with high cooling demand."
        ),
        "eligibility_criteria": (
            "Duke Energy Florida residential customer; participating "
            "contractor; equipment meets Tier 2 SEER2/EER2 minimums."
        ),
        "incentive_amount": "Up to $325 per Tier 2 central AC unit",
        "program_links": "https://www.duke-energy.com/home/products/smart-saver",
    },
    {
        "program_name": "Duke Energy Florida Smart $aver — Heat Pump",
        "incentive_type": "Rebates",
        "property_type": "Residential",
        "description": (
            "Rebate for installing a qualifying high-efficiency residential "
            "heat pump (HSPF2 minimum threshold) under Smart $aver. Heat "
            "pumps qualify for both Duke rebate and federal §25C credit, "
            "stacking up to $2,000 in federal credit + rebate."
        ),
        "eligibility_criteria": (
            "Duke Energy Florida residential customer; participating "
            "contractor; equipment meets HSPF2 minimum."
        ),
        "incentive_amount": "Up to $300 per qualifying heat pump",
        "program_links": "https://www.duke-energy.com/home/products/smart-saver",
    },
    {
        "program_name": "Duke Energy Florida Smart $aver — Duct Repair",
        "incentive_type": "Rebates",
        "property_type": "Residential",
        "description": (
            "Rebate for testing and sealing leaky ductwork in a Duke FL–"
            "served home. Participating contractor performs pre- and "
            "post-repair duct leakage tests."
        ),
        "eligibility_criteria": (
            "Duke Energy Florida residential customer; pre/post duct "
            "leakage testing required; participating contractor."
        ),
        "incentive_amount": "Up to $150 per home for duct sealing/repair",
        "program_links": "https://www.duke-energy.com/home/products/smart-saver",
    },
    {
        "program_name": "Duke Energy Florida Smart $aver — Attic Insulation",
        "incentive_type": "Rebates",
        "property_type": "Residential",
        "description": (
            "Rebate for upgrading attic insulation to R-30+ in Duke FL "
            "residential homes. Cuts AC runtime and improves comfort."
        ),
        "eligibility_criteria": (
            "Duke Energy Florida residential customer; existing insulation "
            "below R-19; upgraded to R-30+; participating contractor or "
            "DIY with receipts."
        ),
        "incentive_amount": "Up to $200 per home for qualifying attic insulation",
        "program_links": "https://www.duke-energy.com/home/products/smart-saver",
    },
    {
        "program_name": "Duke Energy Florida Home Energy Check",
        "incentive_type": "Rebates",
        "property_type": "Residential",
        "description": (
            "Free home energy assessment (online, by phone, or in-person) that "
            "identifies efficiency upgrades. In-home version includes "
            "no-cost direct install of LED bulbs, smart power strips, and "
            "weather stripping for qualifying customers."
        ),
        "eligibility_criteria": (
            "Duke Energy Florida residential customer; home must be primary "
            "residence; one assessment per address per program year."
        ),
        "incentive_amount": "Free assessment + up to ~$50 in free direct-install measures",
        "program_links": "https://www.duke-energy.com/home/products/home-energy-check",
    },
    {
        "program_name": "Duke Energy Florida EnergyWise Home (Demand Response)",
        "incentive_type": "Rebates",
        "property_type": "Residential",
        "description": (
            "Demand-response program: Duke installs a smart device on your AC "
            "and/or electric water heater that briefly cycles equipment during "
            "peak demand. Participants receive annual bill credits."
        ),
        "eligibility_criteria": (
            "Duke Energy Florida residential customer with central AC and/or "
            "electric water heater; must agree to participation during peak "
            "events; smart meter required."
        ),
        "incentive_amount": "Up to $137/year in bill credits depending on devices enrolled",
        "program_links": "https://www.duke-energy.com/home/products/energywise-home",
    },
    {
        "program_name": "Duke Energy Florida Income-Qualified Weatherization",
        "incentive_type": "Grants",
        "property_type": "Residential (income-qualified)",
        "description": (
            "No-cost home weatherization improvements — insulation, duct "
            "sealing, AC tune-up, and direct-install measures — for "
            "income-qualified Duke Energy Florida customers. Coordinated with "
            "the federal Weatherization Assistance Program."
        ),
        "eligibility_criteria": (
            "Duke Energy Florida residential customer; household income at or "
            "below 200% of federal poverty guidelines (or 60% state median "
            "income); applies to both owners and renters with owner consent."
        ),
        "incentive_amount": "Up to several thousand dollars in no-cost weatherization improvements per home",
        "program_links": "https://www.duke-energy.com/home/products/income-qualified",
    },
    {
        "program_name": "Duke Energy Florida Electric Vehicle Charger Rebate (Park & Plug)",
        "incentive_type": "Rebates",
        "property_type": "Residential",
        "description": (
            "Rebate to offset the cost of installing a qualifying Level 2 home "
            "EV charger. Available to Duke Energy Florida residential "
            "customers as part of the Park & Plug program."
        ),
        "eligibility_criteria": (
            "Duke Energy Florida residential customer; charger must be on the "
            "approved equipment list; receipts required; one rebate per "
            "service address."
        ),
        "incentive_amount": "Up to $500 per qualifying Level 2 charger installation",
        "program_links": "https://www.duke-energy.com/home/products/park-and-plug",
    },
]


def _check_page_for_closures(html: str) -> set[str]:
    """Look for closure language near program keywords on the live landing page."""
    if not html:
        return set()
    lower = html.lower()
    flags: set[str] = set()
    for kw in ("hvac", "smart $aver", "energywise", "weatherization",
               "park and plug", "ev charger", "home energy check"):
        idx = lower.find(kw)
        while idx != -1:
            window = lower[idx : idx + 220]
            if "ended" in window or "no longer" in window or "discontinued" in window:
                flags.add(kw)
                break
            idx = lower.find(kw, idx + 1)
    return flags


def scrape(fetcher: Fetcher, max_programs: int | None = None) -> Iterator[IncentiveRecord]:
    print("[duke_energy] fetching landing page for closure detection")
    html = fetcher.get(LANDING_URL) or fetcher.get(FL_REBATES_URL) or ""
    closure_flags = _check_page_for_closures(html)
    if closure_flags:
        print(f"[duke_energy] closure language detected near: {sorted(closure_flags)}")

    today = date.today().isoformat()
    count = 0
    for prog in DUKE_PROGRAMS:
        description = prog["description"]
        review = "No"
        for kw in closure_flags:
            if kw in prog["program_name"].lower():
                description += " [REVIEW: live page mentions program ended/no longer available]"
                review = "Yes"
                break

        rec = IncentiveRecord(
            program_name=prog["program_name"],
            state=PRIMARY_STATE,
            city=None,           # Duke FL is multi-county; not city-specific
            zip_code=None,      # eligibility = "Duke FL customer"
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
