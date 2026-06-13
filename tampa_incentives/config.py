"""
Configuration: geography, incentive type taxonomy, source registry.

Anirudh's spec defines 5 incentive types. We normalize everything to these.
"""

# -----------------------------------------------------------------------------
# Geographic scope (Phase 1: Tampa + Hillsborough; expandable to Tampa Bay MSA)
# -----------------------------------------------------------------------------
PRIMARY_STATE = "Florida"
PRIMARY_CITY = "Tampa"
PRIMARY_COUNTY = "Hillsborough"

# Hillsborough County ZIP codes (Tampa city limits + unincorporated county).
# Source: USPS / HUD ZIP-county crosswalk for Hillsborough County, FL.
HILLSBOROUGH_ZIPS = [
    "33510", "33511", "33527", "33534", "33547", "33548", "33549", "33550",
    "33556", "33558", "33559", "33563", "33565", "33566", "33567", "33569",
    "33570", "33572", "33573", "33578", "33579", "33584", "33592", "33594",
    "33596", "33598", "33602", "33603", "33604", "33605", "33606", "33607",
    "33609", "33610", "33611", "33612", "33613", "33614", "33615", "33616",
    "33617", "33618", "33619", "33620", "33621", "33624", "33625", "33626",
    "33629", "33634", "33635", "33637", "33647",
]

# Tampa Bay MSA expansion ZIPs (set EXPAND_TO_MSA=True to include).
# Pasco, Pinellas, Manatee, Hernando — listed but not enabled by default.
EXPAND_TO_MSA = False

# -----------------------------------------------------------------------------
# Incentive type taxonomy — maps to Anirudh's 5 allowed values exactly
# -----------------------------------------------------------------------------
INCENTIVE_TYPES = {
    "Grants",
    "Rebates",
    "Finance Solutions",
    "Tax Credits",
    "Investments",
}

# Maps DSIRE / source-specific labels → our 5-bucket taxonomy.
# Add to this as new sources get added.
INCENTIVE_TYPE_MAP = {
    # DSIRE category labels
    "Personal Tax Credit": "Tax Credits",
    "Corporate Tax Credit": "Tax Credits",
    "Sales Tax Incentive": "Tax Credits",
    "Property Tax Incentive": "Tax Credits",
    "Personal Tax Deduction": "Tax Credits",
    "Personal Tax Exemption": "Tax Credits",
    "Corporate Tax Deduction": "Tax Credits",
    "Corporate Tax Exemption": "Tax Credits",
    "Corporate Depreciation": "Tax Credits",   # MACRS and similar
    "Federal Depreciation": "Tax Credits",
    "Rebate Program": "Rebates",
    "Utility Rebate Program": "Rebates",
    "State Rebate Program": "Rebates",
    "Local Rebate Program": "Rebates",
    "Grant Program": "Grants",
    "Federal Grant Program": "Grants",
    "State Grant Program": "Grants",
    "Green Building Incentive": "Grants",      # expedited-review/green-build programs
    "Local Grant Program": "Grants",
    "Loan Program": "Finance Solutions",
    "PACE Financing": "Finance Solutions",
    "Performance-Based Incentive": "Investments",
    "Industry Recruitment/Support": "Investments",
    "Bond Program": "Investments",
    # Generic / source-internal labels
    "tax_credit": "Tax Credits",
    "tax_exemption": "Tax Credits",
    "rebate": "Rebates",
    "grant": "Grants",
    "loan": "Finance Solutions",
    "financing": "Finance Solutions",
    "investment": "Investments",
}


def normalize_incentive_type(raw_label: str) -> str | None:
    """Return one of the 5 allowed types, or None if no clean mapping exists.
    Caller should set review_needed='Yes' when this returns None.
    """
    if not raw_label:
        return None
    key = raw_label.strip()
    if key in INCENTIVE_TYPE_MAP:
        return INCENTIVE_TYPE_MAP[key]
    # case-insensitive fallback
    for k, v in INCENTIVE_TYPE_MAP.items():
        if k.lower() == key.lower():
            return v
    return None


# -----------------------------------------------------------------------------
# Source registry
# Each entry may include scrape_notes documenting freshness, gaps, and fragility.
# -----------------------------------------------------------------------------
SOURCES = {
    "dsire": {
        "name": "DSIRE — Database of State Incentives for Renewables & Efficiency",
        "url": "https://www.dsireusa.org/",
        "api": "https://programs.dsireusa.org/api/v1/",
        "priority": "P0",
        "method": "scrape",
        "expected_programs": "30-50 FL state/utility/local programs",
        "scrape_notes": (
            "DSIRE's paid API returns 403; we scrape the public AngularJS listing. "
            "Each detail page embeds full JSON in a data-ng-init attribute — "
            "parse that, not the rendered DOM. Regulatory-only entries "
            "(Net Metering, Interconnection Standards, etc.) have no incentive_type "
            "and are flagged review_needed=Yes by design. "
            "Re-run monthly; DSIRE updates programs weekly."
        ),
    },
    "rewiring_america": {
        "name": "Rewiring America — Federal IRA Calculator",
        "url": "https://www.rewiringamerica.org/app/ira-calculator",
        "api": "https://api.rewiringamerica.org/api/v1/",
        "priority": "P0",
        "method": "api",
        "expected_programs": "All federal IRA programs (25C, 25D, etc.)",
        "scrape_notes": (
            "Requires a free Rewiring America API key (REWIRING_AMERICA_API_KEY in .env). "
            "Without a key, falls back to a curated static list of 5 core IRA programs. "
            "API returns per-ZIP eligibility; we query a sample of Tampa ZIPs and deduplicate. "
            "Federal programs don't expire on a fixed date — monitor IRA reauthorization news."
        ),
    },
    "teco": {
        "name": "Tampa Electric (TECO) Rebates",
        "url": "https://www.tampaelectric.com/residential/saveenergy/rebates/",
        "priority": "P0",
        "method": "scrape",
        "expected_programs": "5-10 utility rebate programs",
        "scrape_notes": (
            "TECO's rebate page is static HTML — straightforward BeautifulSoup parse. "
            "Rebate amounts and eligibility change seasonally; re-run quarterly. "
            "If the page returns 403, TECO may have moved the URL — check the site manually. "
            "Baseline records are curated in-scraper as a fallback if the live page is unavailable."
        ),
    },
    "duke_energy": {
        "name": "Duke Energy Florida Residential Rebates",
        "url": "https://www.duke-energy.com/home/products",
        "priority": "P1",
        "method": "scrape",
        "expected_programs": "3-6 utility programs (HVAC, EnergyWise, EV, weatherization)",
        "scrape_notes": (
            "Duke Energy Florida serves parts of the Tampa Bay area but not Tampa proper. "
            "Programs are curated in-scraper (live page is JS-rendered and fragile). "
            "Verify program status quarterly at duke-energy.com. "
            "zip_code left blank — eligibility is 'Duke FL service territory', not ZIP-specific."
        ),
    },
    "my_safe_florida_home": {
        "name": "My Safe Florida Home (hurricane mitigation grant)",
        "url": "https://mysafefloridahome.com/",
        "priority": "P1",
        "method": "scrape",
        "expected_programs": "Mitigation grant + free inspection",
        "scrape_notes": (
            "Funded by Florida Legislature annually — program can open/close mid-year "
            "when funds are exhausted. Check mysafefloridahome.com for current status "
            "before including in any consumer-facing output. "
            "Grants up to $10,000 (2:1 match). Hurricane-season demand spikes in Q3/Q4."
        ),
    },
    "irs_energy": {
        "name": "IRS Federal Energy Tax Credits (25C + 25D)",
        "url": "https://www.irs.gov/credits-deductions/residential-clean-energy-credit",
        "priority": "P1",
        "method": "scrape",
        "expected_programs": "25C + 25D + home energy audit credit",
        "scrape_notes": (
            "IRS pages are static and rarely restructured — scrape is stable. "
            "Credit amounts and eligible equipment change with legislation; "
            "verify after any tax bill passage. "
            "Note: the One Big Beautiful Bill (2025) repealed or curtailed several IRA credits — "
            "check valid_until dates carefully and re-scrape after major tax legislation."
        ),
    },
    "florida_housing": {
        "name": "Florida Housing Finance Corporation",
        "url": "https://www.floridahousing.org/programs",
        "priority": "P1",
        "method": "scrape",
        "expected_programs": "Hometown Heroes, FL Assist, HFA Preferred, SHIP, HOME",
        "scrape_notes": (
            "FHFC programs are mostly curated in-scraper; the website is JS-heavy. "
            "Hometown Heroes income limits and interest rates update frequently — "
            "pull the PDF fact sheet from floridahousing.org quarterly. "
            "SHIP allocations vary by county; Hillsborough SHIP is tracked separately "
            "in the hillsborough scraper."
        ),
    },
    "hillsborough": {
        "name": "Hillsborough County Housing",
        "url": "https://www.hillsboroughcounty.org/en/residents/property-owners-and-renters/housing",
        "priority": "P1",
        "method": "scrape",
        "expected_programs": "SHIP rehab/DPA, CDBG, emergency repair, mobile home",
        "scrape_notes": (
            "County website pages are fairly stable HTML. "
            "SHIP program funds are annual — applications typically open Oct 1. "
            "Confirm program availability with the county Housing Finance Division "
            "before publishing; some programs exhaust funds within weeks of opening."
        ),
    },
    "tampa_city": {
        "name": "City of Tampa Community Development",
        "url": "https://www.tampa.gov/community-development",
        "priority": "P2",
        "method": "scrape",
        "expected_programs": "Local rehab + JOC + DPA programs",
        "scrape_notes": (
            "Tampa city programs are curated in-scraper; the CD website has inconsistent structure. "
            "Programs are funded through federal CDBG/HOME allocations renewed annually. "
            "Check tampa.gov/community-development for updated program guides each October."
        ),
    },
    "fema": {
        "name": "FEMA Hazard Mitigation",
        "url": "https://www.fema.gov/grants/mitigation",
        "priority": "P2",
        "method": "scrape",
        "expected_programs": "HMGP, BRIC, FMA",
        "scrape_notes": (
            "FEMA mitigation grants (HMGP, BRIC, FMA) are curated in-scraper; "
            "they flow through the Florida Division of Emergency Management, not directly to homeowners. "
            "Individual homeowners apply through their local government. "
            "BRIC was defunded in 2025 — verify current program status before publishing."
        ),
    },
    "pace": {
        "name": "PACE financing (Ygrene / RenewPACE / FRED / FPFA)",
        "url": "https://www.floridapace.gov/",
        "priority": "P2",
        "method": "scrape",
        "expected_programs": "PACE financing programs (FPFA, RenewPACE, FRED, Ygrene)",
        "scrape_notes": (
            "Florida PACE programs are curated in-scraper. "
            "PACE carries a mortgage-lien risk disclosure requirement per FL law (2023). "
            "Ygrene exited the FL market in 2022; verify active providers at floridapace.gov. "
            "All Hillsborough ZIPs are eligible; add zip_code = HILLSBOROUGH_ZIPS join."
        ),
    },
    "hillsborough_rebuilding": {
        "name": "Hillsborough County Rebuilding for Tomorrow (CDBG-DR)",
        "url": "https://rebuildingfortomorrow.hcfl.gov/",
        "priority": "P0-PRIORITY",
        "method": "scrape",
        "expected_programs": "HRRP (SFH), MFH, SPH + 22 approved infra projects",
        "scrape_notes": (
            "URGENT: this program is live and accepting applications (as of May 2025). "
            "Data pulled from the Rebuilding for Tomorrow public API (hcfl.gov JSON endpoints). "
            "Infrastructure project list and award amounts update as the BCC approves phases — "
            "re-run weekly during active disbursement. "
            "MFH and SPH NOFAs open June 2026; update valid_until and status after NOFA launch."
        ),
    },
}

# -----------------------------------------------------------------------------
# Output
# review_needed is intentionally excluded — it's an internal QA flag, not a
# deliverable column per Anirudh's 12-column spec.
# -----------------------------------------------------------------------------
OUTPUT_COLUMNS = [
    "program_name",
    "state",
    "city",
    "zip_code",
    "incentive_type",
    "property_type",
    "description",
    "eligibility_criteria",
    "incentive_amount",
    "valid_until",
    "updated_at",
    "program_links",
]

OUTPUT_FILENAME = "your_name_extracted_tampa_incentives.csv"

# -----------------------------------------------------------------------------
# Politeness / network
# -----------------------------------------------------------------------------
REQUEST_DELAY_SECONDS = 1.0  # ≤1 req/sec to any single host
USER_AGENT = (
    "DreamlineAI-IncentiveResearch/0.1 "
    "(+https://dreamlineai.org; research@dreamlineai.org)"
)
REQUEST_TIMEOUT = 30
CACHE_DIR = "cache"

# Toggle this to True once you have ANTHROPIC_API_KEY and want LLM-based
# extraction for messy sources (PDFs, JS-heavy pages).
USE_LLM_EXTRACTION = False
