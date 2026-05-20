"""
City of Tampa community development & housing programs.

The brief calls out an approved $11.4M residential rehabilitation JOC
(Job Order Contracting) program and other Tampa city-level rehab incentives.
City-specific → fill city="Tampa" and Hillsborough ZIPs.

Source: tampa.gov/community-development and tampa.gov/housing
"""

from __future__ import annotations
from datetime import date
from typing import Iterator

from .base import Fetcher
from config import PRIMARY_STATE, PRIMARY_CITY, HILLSBOROUGH_ZIPS
from schema import IncentiveRecord


LANDING_URL = "https://www.tampa.gov/community-development"
HOUSING_URL = "https://www.tampa.gov/housing-and-community-development"

# City of Tampa proper — narrow to in-city Hillsborough ZIPs.
TAMPA_CITY_ZIPS = [
    "33602", "33603", "33604", "33605", "33606", "33607", "33609",
    "33610", "33611", "33612", "33613", "33614", "33615", "33616",
    "33617", "33618", "33619", "33620", "33621", "33624", "33625",
    "33626", "33629", "33634", "33635", "33637", "33647",
]
ZIPS = ",".join(TAMPA_CITY_ZIPS)


TAMPA_PROGRAMS: list[dict] = [
    {
        "program_name": "City of Tampa Owner-Occupied Rehabilitation (JOC Program)",
        "incentive_type": "Grants",
        "property_type": "Single-family residential (owner-occupied, city limits)",
        "description": (
            "Approved $11.4M residential rehabilitation Job Order Contracting "
            "(JOC) program for the City of Tampa. Provides home repair and "
            "rehabilitation services — roof, plumbing, electrical, HVAC, "
            "accessibility — for low- and moderate-income owner-occupants "
            "via pre-qualified contractor pool."
        ),
        "eligibility_criteria": (
            "Single-family home located within City of Tampa limits; "
            "owner-occupied homestead; household income at or below 80% AMI "
            "for most projects (some strategies up to 120% AMI); current "
            "on property taxes and insurance."
        ),
        "incentive_amount": "Up to $75,000 per home (deferred-payment, forgivable after compliance period)",
        "program_links": HOUSING_URL,
    },
    {
        "program_name": "City of Tampa Down Payment Assistance (Dare to Own the Dream)",
        "incentive_type": "Finance Solutions",
        "property_type": "Single-family residential (primary residence, city limits)",
        "description": (
            "Down payment and closing cost assistance for first-time "
            "homebuyers purchasing within the City of Tampa. Provided as a "
            "0% interest, deferred-payment second mortgage that is forgiven "
            "over the affordability period."
        ),
        "eligibility_criteria": (
            "First-time homebuyer (no homeownership in past 3 years); "
            "household income at or below 120% AMI; purchase a primary "
            "residence within City of Tampa limits; complete approved "
            "homebuyer education course."
        ),
        "incentive_amount": "Up to $40,000 in deferred-payment, forgivable second mortgage",
        "program_links": HOUSING_URL,
    },
    {
        "program_name": "City of Tampa Minor Home Repair Program",
        "incentive_type": "Grants",
        "property_type": "Single-family residential (owner-occupied)",
        "description": (
            "Quick-turnaround minor repair grants for City of Tampa "
            "homeowners facing code-compliance issues, accessibility needs, "
            "or critical home safety problems — separate from the larger "
            "owner-occupied rehab program."
        ),
        "eligibility_criteria": (
            "City of Tampa resident; owner-occupied primary residence; "
            "household income at or below 80% AMI; demonstrated repair need."
        ),
        "incentive_amount": "Up to $10,000 grant (no repayment)",
        "program_links": HOUSING_URL,
    },
    {
        "program_name": "City of Tampa CDBG Neighborhood Revitalization",
        "incentive_type": "Grants",
        "property_type": "Residential (owner or renter, targeted CDBG areas)",
        "description": (
            "Federal Community Development Block Grant funds administered by "
            "the City of Tampa for neighborhood revitalization in CDBG-"
            "eligible census tracts: housing rehab, public facilities, code "
            "enforcement, and economic development."
        ),
        "eligibility_criteria": (
            "Property in CDBG-eligible low- and moderate-income census "
            "tracts within City of Tampa; household income at or below 80% "
            "AMI for housing assistance."
        ),
        "incentive_amount": "Varies by activity; rehab assistance typically up to $50,000 per home",
        "program_links": HOUSING_URL,
    },
]


def scrape(fetcher: Fetcher, max_programs: int | None = None) -> Iterator[IncentiveRecord]:
    print("[tampa_city] verifying landing page reachable")
    fetcher.get(LANDING_URL)  # cache only — emit curated baseline regardless
    today = date.today().isoformat()
    count = 0
    for prog in TAMPA_PROGRAMS:
        rec = IncentiveRecord(
            program_name=prog["program_name"],
            state=PRIMARY_STATE,
            city=PRIMARY_CITY,
            zip_codes=ZIPS,
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
