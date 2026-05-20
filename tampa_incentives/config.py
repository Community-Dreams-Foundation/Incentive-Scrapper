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
    "Rebate Program": "Rebates",
    "Utility Rebate Program": "Rebates",
    "State Rebate Program": "Rebates",
    "Local Rebate Program": "Rebates",
    "Grant Program": "Grants",
    "Federal Grant Program": "Grants",
    "State Grant Program": "Grants",
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
# -----------------------------------------------------------------------------
SOURCES = {
    "dsire": {
        "name": "DSIRE — Database of State Incentives for Renewables & Efficiency",
        "url": "https://www.dsireusa.org/",
        "api": "https://programs.dsireusa.org/api/v1/",
        "priority": "P0",
        "method": "api",
        "expected_programs": "30-50 FL state/utility/local programs",
    },
    "rewiring_america": {
        "name": "Rewiring America — Federal IRA Calculator",
        "url": "https://www.rewiringamerica.org/app/ira-calculator",
        "api": "https://api.rewiringamerica.org/api/v1/",  # public docs path
        "priority": "P0",
        "method": "api",
        "expected_programs": "All federal IRA programs (25C, 25D, etc.)",
    },
    "teco": {
        "name": "Tampa Electric (TECO) Rebates",
        "url": "https://www.tampaelectric.com/residential/saveenergy/rebates/",
        "priority": "P0",
        "method": "scrape",
        "expected_programs": "5-10 utility rebate programs",
    },
    "duke_energy": {
        "name": "Duke Energy Florida Residential Rebates",
        "url": "https://www.duke-energy.com/home/products",
        "priority": "P1",
        "method": "scrape",
        "expected_programs": "3-6 utility programs (HVAC, EnergyWise, EV, weatherization)",
    },
    "my_safe_florida_home": {
        "name": "My Safe Florida Home (hurricane mitigation grant)",
        "url": "https://mysafefloridahome.com/",
        "priority": "P1",
        "method": "scrape",
        "expected_programs": "Mitigation grant + free inspection",
    },
    "irs_energy": {
        "name": "IRS Federal Energy Tax Credits (25C + 25D)",
        "url": "https://www.irs.gov/credits-deductions/residential-clean-energy-credit",
        "priority": "P1",
        "method": "scrape",
        "expected_programs": "25C + 25D + home energy audit credit",
    },
    "florida_housing": {
        "name": "Florida Housing Finance Corporation",
        "url": "https://www.floridahousing.org/programs",
        "priority": "P1",
        "method": "scrape",
        "expected_programs": "Hometown Heroes, FL Assist, HFA Preferred, SHIP, HOME",
    },
    "hillsborough": {
        "name": "Hillsborough County Housing",
        "url": "https://www.hillsboroughcounty.org/en/residents/property-owners-and-renters/housing",
        "priority": "P1",
        "method": "scrape",
        "expected_programs": "SHIP rehab/DPA, CDBG, emergency repair, mobile home",
    },
    "tampa_city": {
        "name": "City of Tampa Community Development",
        "url": "https://www.tampa.gov/community-development",
        "priority": "P2",
        "method": "scrape",
        "expected_programs": "Local rehab + JOC + DPA programs",
    },
    "fema": {
        "name": "FEMA Hazard Mitigation",
        "url": "https://www.fema.gov/grants/mitigation",
        "priority": "P2",
        "method": "scrape",
        "expected_programs": "HMGP, BRIC, FMA",
    },
    "pace": {
        "name": "PACE financing (Ygrene / RenewPACE / FRED / FPFA)",
        "url": "https://www.floridapace.gov/",
        "priority": "P2",
        "method": "scrape",
        "expected_programs": "PACE financing programs (FPFA, RenewPACE, FRED, Ygrene)",
    },
    "hillsborough_rebuilding": {
        "name": "Hillsborough County Rebuilding for Tomorrow (CDBG-DR)",
        "url": "https://rebuildingfortomorrow.hcfl.gov/",
        "priority": "P0-PRIORITY",  # urgent: needs to ship to dreamlineai.org this week
        "method": "scrape",
        "expected_programs": "HRRP (SFH), MFH, SPH + 22 approved infra projects",
    },
}

# -----------------------------------------------------------------------------
# Output
# -----------------------------------------------------------------------------
OUTPUT_COLUMNS = [
    "program_name",
    "state",
    "city",
    "zip_codes",
    "incentive_type",
    "property_type",
    "description",
    "eligibility_criteria",
    "incentive_amount",
    "valid_until",
    "updated_at",
    "review_needed",
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
