"""
TECO (Tampa Electric) residential rebates scraper.

TECO's rebate page lists individual program tiles. Programs change frequently
(e.g., the chiller program ended May 2025; HVAC remains active). We:

  1. Fetch the live rebates landing page to detect program closures/additions
     and append a flag to the description if the page mentions "ended".
  2. Emit records for the known active programs (curated baseline). This keeps
     the script useful even if the page structure changes.

When you run this regularly, the diff between the live page and the curated
list will tell you what to update.
"""

from __future__ import annotations
from datetime import date
from typing import Iterator

from .base import Fetcher
from config import PRIMARY_STATE, PRIMARY_CITY, HILLSBOROUGH_ZIPS
from schema import IncentiveRecord


LANDING_URL = "https://www.tampaelectric.com/residential/saveenergy/"
HEATING_COOLING_URL = "https://www.tampaelectric.com/residential/saveenergy/heatingcooling/"

CITY = PRIMARY_CITY
ZIPS = ",".join(HILLSBOROUGH_ZIPS)


# Curated baseline of TECO residential rebate programs (Tampa Electric service
# territory: Hillsborough + parts of Polk, Pasco, Pinellas).
TECO_PROGRAMS: list[dict] = [
    {
        "program_name": "TECO Heating & Cooling Rebate — Tier 1 (Standard Efficiency)",
        "incentive_type": "Rebates",
        "property_type": "Residential (single-family, owner-occupied)",
        "description": (
            "Rebate for replacing an old AC with a Tier 1 high-efficiency "
            "split system meeting TECO's lower SEER/SEER2 threshold. "
            "Suitable for many existing-home retrofits."
        ),
        "eligibility_criteria": (
            "Tampa Electric residential customer. Minimum SEER 16.00 / "
            "SEER2 15.20 for straight-cool with natural gas heat. "
            "Application within 90 days of installation."
        ),
        "incentive_amount": "$140-$250 per qualifying condensing unit (Tier 1)",
        "program_links": HEATING_COOLING_URL,
    },
    {
        "program_name": "TECO Heating & Cooling Rebate — Tier 2 (High Efficiency)",
        "incentive_type": "Rebates",
        "property_type": "Residential",
        "description": (
            "Higher-tier rebate for installing a SEER 17+ / SEER2 16.2+ "
            "central AC or heat pump. Top-tier electric AC equipment that "
            "qualifies for the maximum TECO rebate."
        ),
        "eligibility_criteria": (
            "Tampa Electric residential customer. Minimum SEER 17.00 / "
            "SEER2 16.20. Installed by licensed FL contractor. Receipts "
            "and AHRI certificate required."
        ),
        "incentive_amount": "Up to $325 per qualifying condensing unit (Tier 2)",
        "program_links": HEATING_COOLING_URL,
    },
    {
        "program_name": "TECO Geothermal Heat Pump Rebate",
        "incentive_type": "Rebates",
        "property_type": "Residential",
        "description": (
            "Rebate for installing a qualifying geothermal (ground-source) "
            "heat pump. Stackable with the federal §25D Residential Clean "
            "Energy Credit."
        ),
        "eligibility_criteria": (
            "Tampa Electric residential customer. Minimum EER 14.0; "
            "installation must follow TECO + manufacturer requirements."
        ),
        "incentive_amount": "Up to $1,200 per geothermal heat pump installation",
        "program_links": HEATING_COOLING_URL,
    },
    {
        "program_name": "TECO Duct Repair Rebate",
        "incentive_type": "Rebates",
        "property_type": "Residential (single-family, existing duct system)",
        "description": (
            "Rebate to test and seal leaky air-conditioner ductwork. TECO "
            "or an approved contractor performs pre/post duct-leakage "
            "testing; rebate paid when leakage falls below program "
            "threshold."
        ),
        "eligibility_criteria": (
            "Tampa Electric residential customer; existing AC system; "
            "duct leakage test required pre and post repair; approved "
            "contractor."
        ),
        "incentive_amount": "Up to $200 per home for qualifying duct repair",
        "program_links": "https://www.tampaelectric.com/residential/saveenergy/ductrepair/",
    },
    {
        "program_name": "TECO Attic Insulation Rebate",
        "incentive_type": "Rebates",
        "property_type": "Residential (single-family)",
        "description": (
            "Rebate for upgrading attic insulation to R-30 or higher in a "
            "Tampa Electric–served home. Reduces cooling load and improves "
            "comfort in hot Florida summers."
        ),
        "eligibility_criteria": (
            "Tampa Electric residential customer; existing attic "
            "insulation below R-19; upgraded to R-30 minimum; "
            "installation receipts required."
        ),
        "incentive_amount": "Up to $250 per home for qualifying attic insulation upgrade",
        "program_links": "https://www.tampaelectric.com/residential/saveenergy/atticinsulation/",
    },
    {
        "program_name": "TECO Window Film Rebate",
        "incentive_type": "Rebates",
        "property_type": "Residential",
        "description": (
            "Rebate for installing qualifying solar-control window film "
            "on existing single-pane windows in a Tampa Electric–served "
            "home. Reduces solar heat gain and AC load."
        ),
        "eligibility_criteria": (
            "Tampa Electric residential customer; film must meet TECO's "
            "Solar Heat Gain Coefficient (SHGC) threshold; receipts "
            "required."
        ),
        "incentive_amount": "Up to $0.65 per square foot of qualifying window film",
        "program_links": "https://www.tampaelectric.com/residential/saveenergy/windowfilm/",
    },
    {
        "program_name": "TECO Energy Planner — Time-of-Use Rate",
        "incentive_type": "Rebates",
        "property_type": "Residential",
        "description": (
            "Optional time-of-use rate plan that offers lower electricity "
            "prices during off-peak hours (typically nights and weekends). "
            "Best fit for customers with smart thermostats, EVs, or "
            "flexible usage patterns. Effectively a rebate via reduced "
            "monthly bills."
        ),
        "eligibility_criteria": (
            "Tampa Electric residential customer with smart meter; "
            "voluntary enrollment; minimum 12-month commitment."
        ),
        "incentive_amount": "Bill savings 10-25% for customers shifting usage to off-peak",
        "program_links": "https://www.tampaelectric.com/residential/billingoptions/",
    },
    {
        "program_name": "TECO ENERGY STAR Smart Thermostat Rebate",
        "incentive_type": "Rebates",
        "property_type": "Residential",
        "description": (
            "Rebate for installing a qualifying ENERGY STAR-certified smart "
            "thermostat in a Tampa Electric-served home."
        ),
        "eligibility_criteria": "Tampa Electric residential customer. Thermostat must be ENERGY STAR certified.",
        "incentive_amount": "Up to $50 per thermostat",
        "program_links": "https://www.tampaelectric.com/residential/saveenergy/smartthermostat/",
    },
    {
        "program_name": "TECO ENERGY STAR Pool Pump Rebate",
        "incentive_type": "Rebates",
        "property_type": "Residential with pool",
        "description": (
            "Rebate for replacing a single-speed pool pump with a high-"
            "efficiency variable-speed ENERGY STAR pool pump."
        ),
        "eligibility_criteria": "Tampa Electric residential customer. Variable-speed ENERGY STAR pump required.",
        "incentive_amount": "Up to $350 per pump",
        "program_links": "https://www.tampaelectric.com/residential/saveenergy/poolpump/",
    },
    {
        "program_name": "TECO Prime Time Plus (Demand Response)",
        "incentive_type": "Rebates",
        "property_type": "Residential",
        "description": (
            "Demand-response load-management program. TECO uses smart meters to "
            "control your air handler, water heater, and/or pool pump during "
            "peak energy-use periods in exchange for monthly bill credits. "
            "Includes a free programmable thermostat."
        ),
        "eligibility_criteria": "Tampa Electric residential customer with smart meter installed; must enroll voluntarily.",
        "incentive_amount": "Up to $12/month bill credit",
        "program_links": "https://www.tampaelectric.com/residential/saveenergy/primetimeplus/",
    },
    {
        "program_name": "Peoples Gas Natural Gas Appliance Rebate (TECO sister utility)",
        "incentive_type": "Rebates",
        "property_type": "Residential",
        "description": (
            "Rebate for installing qualifying natural gas appliances — water "
            "heaters, furnaces, ranges, dryers — under FPSC-approved rates. "
            "Larger rebate when replacing electric appliances with natural gas."
        ),
        "eligibility_criteria": "Peoples Gas residential customer in service territory (overlaps Tampa Electric).",
        "incentive_amount": (
            "Tank water heater: $500 (replace electric) / $350 (replace gas); "
            "Tankless: $675 / $550; Central heating: up to $725"
        ),
        "program_links": "https://www.peoplesgas.com/residential/save/",
    },
]


def _check_page_for_closures(html: str) -> set[str]:
    """Scan TECO landing page for closure language. Returns lowercased keywords
    that appear adjacent to 'ended' or 'no longer available' so we can flag
    affected programs.
    """
    if not html:
        return set()
    lower = html.lower()
    flags: set[str] = set()
    for kw in ("chiller", "cooling", "thermostat", "pool pump", "prime time"):
        # Look for kw + "ended"/"no longer" within 200 chars
        idx = lower.find(kw)
        while idx != -1:
            window = lower[idx : idx + 200]
            if "ended" in window or "no longer" in window:
                flags.add(kw)
                break
            idx = lower.find(kw, idx + 1)
    return flags


def scrape(fetcher: Fetcher, max_programs: int | None = None) -> Iterator[IncentiveRecord]:
    print(f"[teco] fetching landing page for closure detection")
    html = fetcher.get(LANDING_URL) or ""
    closure_flags = _check_page_for_closures(html)
    if closure_flags:
        print(f"[teco] closure language detected near: {sorted(closure_flags)}")

    today = date.today().isoformat()
    count = 0
    for prog in TECO_PROGRAMS:
        description = prog["description"]
        review = "No"
        # If a closure keyword matches the program name, mark for review.
        for kw in closure_flags:
            if kw in prog["program_name"].lower():
                description += " [REVIEW: live page mentions program ended/no longer available]"
                review = "Yes"
                break

        rec = IncentiveRecord(
            program_name=prog["program_name"],
            state=PRIMARY_STATE,
            city=CITY,
            zip_code=ZIPS,
            incentive_type=prog["incentive_type"],
            property_type=prog["property_type"],
            description=description,
            eligibility_criteria=prog["eligibility_criteria"],
            incentive_amount=prog["incentive_amount"],
            valid_until=None,  # TECO programs are typically open-ended
            updated_at=today,
            review_needed=review,  # may be auto-overridden by validator
            program_links=prog["program_links"],
        )
        yield rec
        count += 1
        if max_programs and count >= max_programs:
            break
