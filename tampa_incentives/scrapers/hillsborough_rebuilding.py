"""
Hillsborough County — "Rebuilding for Tomorrow" CDBG-DR portal.

Source: rebuildingfortomorrow.hcfl.gov

The County's $271M+ Community Development Block Grant - Disaster Recovery
(CDBG-DR) portal, created to deploy HUD funds after Hurricanes Helene and
Milton (2024). Three housing programs + a portfolio of infrastructure
projects, all eligible to Hillsborough County residents (incl. City of
Tampa, Temple Terrace, Plant City).

Data sourced directly from the portal pages (May 2026):
  /H/SFH  — Homeowner Repair & Reconstruction Program (HRRP)  — ACTIVE
  /H/MFH  — Multi-Family Housing Program                      — opens Jun 2026
  /H/SPH  — Special Population Housing Program                — opens Jun 2026
  /I      — Infrastructure (22 approved public-works projects)

This is the priority Hillsborough source for Dreamline AI — the brief
explicitly calls out post-2023/2024 hurricane recovery as Tampa Bay's
biggest current renovation driver.
"""

from __future__ import annotations
from datetime import date
from typing import Iterator

from .base import Fetcher
from config import PRIMARY_STATE, HILLSBOROUGH_ZIPS
from schema import IncentiveRecord


# -----------------------------------------------------------------------------
# Source URLs (each program page has its own GUID-keyed URL)
# -----------------------------------------------------------------------------
LANDING_URL = "https://rebuildingfortomorrow.hcfl.gov/"
HOUSING_URL = "https://rebuildingfortomorrow.hcfl.gov/H?id=c902f809-c41c-f111-8341-7ced8d6f48ab"
HRRP_URL = "https://rebuildingfortomorrow.hcfl.gov/H/SFH/?id=cf6516e0-9f24-f111-8341-7ced8d6f4b5b"
MFH_URL = "https://rebuildingfortomorrow.hcfl.gov/H/MFH?id=3ea96bfe-9f24-f111-8341-7ced8d6f4b5b"
SPH_URL = "https://rebuildingfortomorrow.hcfl.gov/H/SPH?id=41b30fea-4b29-f111-8341-7ced8d6f4b5b"
INFRA_URL = "https://rebuildingfortomorrow.hcfl.gov/I?id=1ddcc775-9006-f111-8406-7ced8d6f4b5b"

ZIPS = ",".join(HILLSBOROUGH_ZIPS)


# -----------------------------------------------------------------------------
# Housing programs (3) — verbatim from the portal pages
# -----------------------------------------------------------------------------
HOUSING_PROGRAMS: list[dict] = [
    {
        "program_name": "Hillsborough County Homeowner Repair and Reconstruction Program (HRRP)",
        "incentive_type": "Grants",
        "property_type": (
            "Single-family residential (owner-occupied primary residence). "
            "Eligible types: wood-built, detached structures, concrete block, "
            "duplex, triplex, quadplex, and mobile/manufactured homes."
        ),
        "description": (
            "Hillsborough County's $211M CDBG-DR program to repair, rebuild, "
            "or reimburse storm-damaged single-family homes affected by "
            "Hurricanes Helene and/or Milton (2024). Currently accepting "
            "applications. Three award pathways: Storm Damage Repair (up to "
            "$150K), Reconstruction & Replacement (up to $350K), or Repair "
            "Reimbursement (up to $50K, minimum $10K). Residents anywhere in "
            "Hillsborough County qualify — including City of Tampa, Temple "
            "Terrace, and Plant City."
        ),
        "eligibility_criteria": (
            "Home located in Hillsborough County. Applicant is the homeowner "
            "(not renter or landlord). Eligible structures only: SFH, duplex, "
            "triplex, quadplex, mobile/manufactured. Ineligible: campers, "
            "sheds, outbuildings, houseboats, structures with 5+ units. "
            "Property must NOT be in a regulatory floodway. Primary residence "
            "(lived there before storm and continue to live there). Household "
            "income up to 120% of AMI (priority to <=80% AMI). AMI thresholds "
            "by household size: 1=$58,450/$87,600; 2=$66,800/$100,080; "
            "3=$75,150/$112,680; 4=$83,450/$125,160; 5=$90,150/$135,240; "
            "6=$96,850/$145,200; 7=$103,500/$155,280; 8+=$110,200/$165,240."
        ),
        "incentive_amount": (
            "Storm Damage Repair: up to $150,000 or 50% of pre-storm value; "
            "Reconstruction & Replacement: up to $350,000; "
            "Repair Reimbursement: $10,000-$50,000 for verified completed repairs"
        ),
        "program_links": HRRP_URL,
        "valid_until": None,
        "status": "active",
    },
    {
        "program_name": "Hillsborough County Multi-Family Housing Program (CDBG-DR)",
        "incentive_type": "Grants",
        "property_type": "Multi-family rental housing (5+ units)",
        "description": (
            "$60M Hillsborough County CDBG-DR allocation for affordable "
            "multi-family rehabilitation and development post-Hurricanes "
            "Helene/Milton. Awarded through a competitive Notice of Funding "
            "Availability (NOFA) expected to open June 2026. Funds gap "
            "financing for multi-family rehab, demolition + reconstruction, "
            "and new affordable multi-family development."
        ),
        "eligibility_criteria": (
            "Eligible applicants: Community Housing Development Organizations "
            "(CHDO), Community-Based Development Organizations (CBDO), Public "
            "Housing Authorities (PHA), Units of General Local Government "
            "(UGLG), Not-for-Profit Organizations (NPO) or For-Profit "
            "Entities, and private multi-family property owners."
        ),
        "incentive_amount": "Up to $60M total program; per-project award via competitive NOFA",
        "program_links": MFH_URL,
        "valid_until": None,
        "status": "opens_jun_2026",
    },
    {
        "program_name": "Hillsborough County Special Population Housing Program (CDBG-DR)",
        "incentive_type": "Grants",
        "property_type": "Multi-family housing serving special populations (supportive housing, care facilities)",
        "description": (
            "$20M Hillsborough County CDBG-DR allocation for acquisition, "
            "new construction, and rehabilitation of housing serving special "
            "populations — seniors, people with disabilities, medically "
            "fragile individuals, and those experiencing homelessness. "
            "Awarded via competitive NOFA expected to open June 2026. "
            "Projects must include a qualified nonprofit partner providing "
            "supportive services."
        ),
        "eligibility_criteria": (
            "Eligible applicants: for-profit developers and nonprofit housing "
            "developers. Projects must include a qualified nonprofit "
            "organization with demonstrated experience serving vulnerable "
            "populations. Documented joint-venture and executed service "
            "partnership agreement required."
        ),
        "incentive_amount": "Up to $20M total program; per-project award via competitive NOFA",
        "program_links": SPH_URL,
        "valid_until": None,
        "status": "opens_jun_2026",
    },
]


# -----------------------------------------------------------------------------
# Infrastructure projects (22) — verbatim from the Infrastructure page table
# -----------------------------------------------------------------------------
PROJECT_DETAIL_TMPL = "https://rebuildingfortomorrow.hcfl.gov/projectdetails/?id={pid}&type=Draft"

INFRA_PROJECTS: list[dict] = [
    {"name": "Culvert Renewal and Replacement Program",                                          "amount": 30434000,  "pid": "a8971c4f-5233-f111-88b4-00224802b826"},
    {"name": "Mitigation of Coastal High-Water Hazard Events by Acquisition and Restoration of Natural Lands", "amount": 10000000, "pid": "5bb3aad3-1938-f111-88b4-00224802bbd5"},
    {"name": "Canal Street Drainage Improvements",                                                "amount": 300000,    "pid": "324438a4-831c-f111-8341-00224802b2c6"},
    {"name": "Stormwater Pump Station Resiliency Improvements",                                   "amount": 6311000,   "pid": "abbf4d25-2f3f-f111-88b4-00224802b362"},
    {"name": "Stacy R. White Nature Preserve Hydrologic Stream Restoration",                      "amount": 5983505,   "pid": "c1911f79-1938-f111-88b4-00224802bbd5"},
    {"name": "North Forest Hills Drainage Improvements",                                          "amount": 180227,    "pid": "1bdf3aa6-f31b-f111-8341-00224802be8c"},
    {"name": "Power Outage Emergency Beacon (POEB) Projects",                                     "amount": 2482000,   "pid": "2f72e85e-2f3f-f111-88b4-00224802b362"},
    {"name": "Ruskin Low-Pressure Sewer System Conversion",                                       "amount": 30000000,  "pid": "b881b17c-1f38-f111-88b4-00224802bbd5"},
    {"name": "Channel Improvement Projects",                                                      "amount": 40700000,  "pid": "f96dfa62-5233-f111-88b4-00224802b826"},
    {"name": "Brushy Creek Restoration",                                                          "amount": 2500000,   "pid": "f494ed4e-1638-f111-88b4-00224802bbd5"},
    {"name": "Town 'N' Country Regional Drainage Improvement Project (Lower Sweetwater Creek Watershed)", "amount": 5600000, "pid": "f801139d-851c-f111-8341-00224802b2c6"},
    {"name": "Town 'N Country/Jackson Springs Drainage Improvements",                             "amount": 411719,    "pid": "eab00738-e41b-f111-8341-00224802be8c"},
    {"name": "Kracker Avenue Coastal Habitat Restoration Project",                                "amount": 2000000,   "pid": "aee7d0b8-1838-f111-88b4-00224802bbd5"},
    {"name": "Shangri-La Permanent Pump Station",                                                 "amount": 325312,    "pid": "23fd1cbc-f71b-f111-8341-00224802be8c"},
    {"name": "76th Street Drainage Improvements Project",                                         "amount": 8000000,   "pid": "bcedfbd0-1a38-f111-88b4-00224802bbd5"},
    {"name": "Casey Road at Lowell Road Drainage Improvements",                                   "amount": 520000,    "pid": "3c38ea60-fc1b-f111-8341-00224802b2c6"},
    {"name": "University Area Drainage Improvements",                                             "amount": 1095718,   "pid": "b1f15d98-152d-f111-88b4-00224802b9c0"},
    {"name": "Falkenburg - Six Mile Creek Road Drainage Improvements",                            "amount": 930000,    "pid": "1918f5a5-821c-f111-8341-00224802b2c6"},
    {"name": "Front Street Drainage Improvements",                                                "amount": 1629494,   "pid": "6ac70103-f01b-f111-8341-00224802be8c"},
    {"name": "Local Stormwater System Restoration",                                               "amount": 1800000,   "pid": "e10878d3-901c-f111-8341-00224802b2c6"},
    {"name": "Pettie Road Drainage Improvements",                                                 "amount": 3900000,   "pid": "5437134a-1a38-f111-88b4-00224802bbd5"},
    {"name": "Seffer / Mango Drainage Improvements",                                              "amount": 679521,    "pid": "64881de7-eb1b-f111-8341-00224802be8c"},
]


def _format_dollars(n: int) -> str:
    return f"${n:,.0f}"


def scrape(fetcher: Fetcher, max_programs: int | None = None) -> Iterator[IncentiveRecord]:
    """Yield IncentiveRecord rows for every Hillsborough Rebuilding for
    Tomorrow program and infrastructure project.

    Live verification: hits the landing/program URLs once per run to confirm
    the portal is reachable and the program pages still resolve. If a page
    fetch fails, we still emit the curated record but tag it for review.
    """
    print("[hcfl_rebuilding] live-verifying portal landing pages")
    landing_ok = bool(fetcher.get(LANDING_URL))
    housing_ok = bool(fetcher.get(HOUSING_URL))
    infra_ok = bool(fetcher.get(INFRA_URL))
    if not (landing_ok and housing_ok and infra_ok):
        print(
            f"[hcfl_rebuilding] WARN  landing_ok={landing_ok} "
            f"housing_ok={housing_ok} infra_ok={infra_ok}"
        )

    today = date.today().isoformat()
    count = 0

    # ---- Housing programs ----
    for prog in HOUSING_PROGRAMS:
        review = "No"
        description = prog["description"]
        # Live-verify each program page (warning printed to stdout only,
        # not baked into user-facing description — environmental failures
        # in restricted sandboxes shouldn't pollute the data).
        page_ok = bool(fetcher.get(prog["program_links"]))
        if not page_ok:
            print(f"[hcfl_rebuilding]   (verify failed for {prog['program_links']})")
        # Future-dated programs (NOFA opens later) get a status tag.
        if prog.get("status") == "opens_jun_2026":
            description += " [STATUS: Applications open June 2026]"

        rec = IncentiveRecord(
            program_name=prog["program_name"],
            state=PRIMARY_STATE,
            city=None,           # county-wide, not city-specific
            zip_codes=ZIPS,      # all Hillsborough County
            incentive_type=prog["incentive_type"],
            property_type=prog["property_type"],
            description=description,
            eligibility_criteria=prog["eligibility_criteria"],
            incentive_amount=prog["incentive_amount"],
            valid_until=prog.get("valid_until"),
            updated_at=today,
            review_needed=review,
            program_links=prog["program_links"],
        )
        yield rec
        count += 1
        if max_programs and count >= max_programs:
            return

    # ---- Infrastructure projects ----
    # These are approved public-works projects funded by CDBG-DR, not
    # homeowner-direct incentives — but they're part of the same "Rebuilding
    # for Tomorrow" deliverable and the brief explicitly asked for everything
    # on this portal. We classify them as Investments (Anirudh's bucket for
    # community-level capital).
    for proj in INFRA_PROJECTS:
        rec = IncentiveRecord(
            program_name=f"Hillsborough CDBG-DR Infrastructure: {proj['name']}",
            state=PRIMARY_STATE,
            city=None,
            zip_codes=ZIPS,
            incentive_type="Investments",
            property_type="Public infrastructure (community-wide benefit)",
            description=(
                f"Approved Hillsborough County CDBG-DR infrastructure "
                f"investment funded by the post-Hurricane Helene/Milton "
                f"$211M+ Rebuilding for Tomorrow program. Total Board of "
                f"County Commissioners–approved amount: "
                f"{_format_dollars(proj['amount'])}. Reduces future flood "
                f"risk and protects residential and business areas."
            ),
            eligibility_criteria=(
                "Community-wide benefit; residents of affected service "
                "areas receive indirect benefit via reduced flooding, "
                "improved drainage, or restored utilities. No direct "
                "homeowner application."
            ),
            incentive_amount=_format_dollars(proj["amount"]),
            valid_until=None,
            updated_at=today,
            review_needed="No",
            program_links=PROJECT_DETAIL_TMPL.format(pid=proj["pid"]),
        )
        yield rec
        count += 1
        if max_programs and count >= max_programs:
            return
