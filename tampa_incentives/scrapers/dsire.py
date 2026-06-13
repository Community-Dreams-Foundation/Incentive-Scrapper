"""
DSIRE scraper.

DSIRE is an AngularJS app. Critically, every program detail page embeds the
*entire* program record as JSON inside a `data-ng-init="init({...})"` attribute
on the DetailsPageCtrl div. We extract that JSON directly — much more reliable
than parsing the rendered DOM.

Listing URL:  https://programs.dsireusa.org/system/program?state=FL
Detail URL:   https://programs.dsireusa.org/system/program/detail/<program_id>
"""

from __future__ import annotations
import html as html_lib
import json
import re
from datetime import date, datetime, timezone
from typing import Any, Iterator

from bs4 import BeautifulSoup

from .base import Fetcher
from config import (
    PRIMARY_STATE,
    PRIMARY_CITY,
    HILLSBOROUGH_ZIPS,
    normalize_incentive_type,
)
from schema import IncentiveRecord


# DSIRE's listing UI uses DataTables with a "Next" button and shows only 50
# entries per page. We paginate via Playwright clicking the next button to get
# all entries (FL listing has ~104 programs; without pagination we only saw 50).
LISTING_URLS = [
    # Florida-tagged programs (state + utility + local + federal applicable to FL)
    "https://programs.dsireusa.org/system/program?state=FL",
    # Federal-only listing (programs not pinned to any single state)
    "https://programs.dsireusa.org/system/program?state=US",
]
DETAIL_URL_TMPL = "https://programs.dsireusa.org/system/program/detail/{pid}"

# DataTables pagination selectors. DSIRE uses standard DataTables markup
# ("dataTables_paginate paging_full_numbers" wrapper, ".next" button).
PAGINATE_SELECTOR = "a.paginate_button.next:not(.disabled)"


def _clean_text(s: str | None) -> str | None:
    if s is None:
        return None
    text = re.sub(r"<[^>]+>", " ", s)  # strip HTML tags from summary
    text = html_lib.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _extract_program_links(listing_html: str) -> list[tuple[str, str]]:
    """Return [(program_id, program_name)] from the FL listing page."""
    soup = BeautifulSoup(listing_html, "html.parser")
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=re.compile(r"/system/program/detail/\d+")):
        href = a.get("href", "")
        m = re.search(r"/detail/(\d+)", href)
        if not m:
            continue
        pid = m.group(1)
        if pid in seen:
            continue
        seen.add(pid)
        name = _clean_text(a.get_text()) or f"DSIRE Program {pid}"
        out.append((pid, name))
    return out


# DSIRE detail pages have ~13 data-ng-init attributes; only the one on the
# div with data-ng-controller="DetailsPageCtrl" carries the program JSON.
# The first ng-init on the page is the AlertCtrl initializer
# (init({"danger":[],"success":[],"warning":[],"info":[]})) — easy to mistake
# for the program data. Always anchor on DetailsPageCtrl.
def _extract_ng_init_json(html: str) -> dict[str, Any] | None:
    """Pull the JSON object out of the DetailsPageCtrl's data-ng-init."""
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find(attrs={"data-ng-controller": "DetailsPageCtrl"})
    if not tag or not tag.get("data-ng-init"):
        return None
    ng_init = tag["data-ng-init"]  # already HTML-unescaped by BS4

    # ng-init value looks like:  init({...json...})
    m = re.match(r"\s*init\((.*)\)\s*$", ng_init, re.DOTALL)
    if not m:
        return None
    raw = m.group(1).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: find the outermost balanced {...} object
        depth = 0
        end = -1
        for i, ch in enumerate(raw):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > 0:
            try:
                return json.loads(raw[:end])
            except json.JSONDecodeError:
                return None
        return None


# DSIRE typeObj.name → Anirudh's 5 incentive types.
_DSIRE_TYPE_TO_BUCKET = {
    "Personal Tax Credit": "Tax Credits",
    "Corporate Tax Credit": "Tax Credits",
    "Personal Tax Deduction": "Tax Credits",
    "Corporate Tax Deduction": "Tax Credits",
    "Personal Tax Exemption": "Tax Credits",
    "Corporate Tax Exemption": "Tax Credits",
    "Property Tax Incentive": "Tax Credits",
    "Sales Tax Incentive": "Tax Credits",
    "Corporate Depreciation": "Tax Credits",    # MACRS (Modified Accelerated Cost-Recovery)
    "Federal Depreciation": "Tax Credits",
    "Green Building Incentive": "Grants",       # expedited-permit / green-build programs
    "Local Grant Program": "Grants",
    "Rebate Program": "Rebates",
    "Utility Rebate Program": "Rebates",
    "State Rebate Program": "Rebates",
    "Local Rebate Program": "Rebates",
    "Grant Program": "Grants",
    "Federal Grant Program": "Grants",
    "State Grant Program": "Grants",
    "Loan Program": "Finance Solutions",
    "PACE Financing": "Finance Solutions",
    "Energy Efficient Mortgage": "Finance Solutions",
    "Performance-Based Incentive": "Investments",
    "Industry Recruitment/Support": "Investments",
    "Bond Program": "Investments",
}

# Regulatory policies aren't actually "incentives" in Anirudh's 5-bucket sense.
# We still record them but mark review_needed=Yes so a human decides.
_REGULATORY_TYPES = {
    "Net Metering",
    "Interconnection Standards",
    "Renewables Portfolio Standard",
    "Energy Efficiency Goals",
    "Fuel Mix Disclosure",
    "Public Benefits Fund",
    "Generation Disclosure",
    "Solar/Wind Access Policy",
    "Building Energy Code",
    "Appliance/Equipment Efficiency Standards",
}


def _bucket_for(program: dict) -> tuple[str | None, bool]:
    """Return (incentive_type, is_regulatory)."""
    type_name = (program.get("typeObj") or {}).get("name") or ""
    if type_name in _REGULATORY_TYPES:
        return None, True
    if type_name in _DSIRE_TYPE_TO_BUCKET:
        return _DSIRE_TYPE_TO_BUCKET[type_name], False
    fallback = normalize_incentive_type(type_name)
    return fallback, False


def _extract_amount(program: dict) -> str | None:
    """DSIRE doesn't always have a single amount field. Try parameters,
    then $ amounts in the summary text.
    """
    params = program.get("parameters") or []
    if params:
        bits: list[str] = []
        for p in params[:4]:
            amt = p.get("amount")
            units = p.get("units") or ""
            label = (p.get("technologyObj") or {}).get("name") or p.get("source") or ""
            if amt is not None:
                piece = str(amt).strip()
                if units:
                    piece = f"{piece} {units}".strip()
                if label:
                    piece = f"{label}: {piece}"
                bits.append(piece)
        if bits:
            return "; ".join(bits)
    summary = _clean_text(program.get("summary") or "")
    if summary:
        amounts = re.findall(r"\$[\d,]+(?:\.\d+)?(?:\s*(?:per|/)\s*\w+)?", summary)
        if amounts:
            return ", ".join(amounts[:3])
    return None


def _is_local_florida(program: dict) -> tuple[str | None, str | None]:
    """If admin'd locally in Tampa/Hillsborough, return (city, zip_csv)."""
    administrator = (program.get("administrator") or "").lower()
    name = (program.get("name") or "").lower()
    haystack = f"{administrator} {name}"
    local_keywords = ("tampa", "hillsborough", "teco", "tampa electric")
    if any(kw in haystack for kw in local_keywords):
        return PRIMARY_CITY, ",".join(HILLSBOROUGH_ZIPS)
    return None, None


def _format_date(value: Any) -> str | None:
    """DSIRE dates come as ISO strings or epoch ms. Return YYYY-MM-DD."""
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
        except (ValueError, OverflowError):
            return None
    if isinstance(value, str):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", value)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None


def _build_record(program: dict, program_id: str) -> IncentiveRecord:
    name = program.get("name") or f"DSIRE Program {program_id}"
    incentive_type, is_regulatory = _bucket_for(program)

    sector = (program.get("sectorObj") or {}).get("name")
    technologies = program.get("technologies") or []
    tech_names = [
        (t.get("technologyObj") or {}).get("name") or t.get("name") or ""
        for t in technologies
    ]
    tech_names = [t for t in tech_names if t]

    eligible_sectors = program.get("eligibleSectors") or []
    sector_names = [
        (es.get("sectorObj") or {}).get("name") or es.get("name") or ""
        for es in eligible_sectors
    ]
    sector_names = [s for s in sector_names if s]

    property_type = ", ".join(sector_names) if sector_names else (sector or None)

    summary = _clean_text(program.get("summary"))
    if summary and len(summary) > 800:
        summary = summary[:797].rstrip() + "..."
    if tech_names and summary:
        description = f"Applies to: {', '.join(tech_names[:5])}. {summary}"
    else:
        description = summary

    eligibility_bits: list[str] = []
    if sector_names:
        eligibility_bits.append(f"Eligible sectors: {', '.join(sector_names)}")
    eligibility = "; ".join(eligibility_bits) or None

    incentive_amount = _extract_amount(program)
    valid_until = _format_date(program.get("expirationDate"))
    updated_at = _format_date(program.get("lastUpdate")) or date.today().isoformat()

    city, zip_codes = _is_local_florida(program)

    rec = IncentiveRecord(
        program_name=name,
        state=PRIMARY_STATE,
        city=city,
        zip_code=zip_codes,
        incentive_type=incentive_type,
        property_type=property_type,
        description=description,
        eligibility_criteria=eligibility,
        incentive_amount=incentive_amount,
        valid_until=valid_until,
        updated_at=updated_at,
        program_links=DETAIL_URL_TMPL.format(pid=program_id),
    )
    if is_regulatory:
        rec.review_needed = "Yes"
    return rec


def scrape(fetcher: Fetcher, max_programs: int | None = None) -> Iterator[IncentiveRecord]:
    """Yield IncentiveRecord for every Florida + federal program in DSIRE."""
    programs: list[tuple[str, str]] = []
    seen: set[str] = set()

    for listing_url in LISTING_URLS:
        print(f"[dsire] fetching listing (rendered, paginated): {listing_url}")
        listing_html = fetcher.get_rendered(
            listing_url,
            wait_selector='a[href*="/system/program/detail/"]',
            wait_ms=8000,
            paginate_click_selector=PAGINATE_SELECTOR,
            paginate_max_clicks=10,        # 10 pages * 50 = up to 500 entries
            paginate_wait_ms=1500,
        )
        if not listing_html:
            print(f"[dsire] listing fetch failed for {listing_url}; skipping it")
            continue

        for pid, name in _extract_program_links(listing_html):
            if pid in seen:
                continue
            seen.add(pid)
            programs.append((pid, name))

    print(f"[dsire] found {len(programs)} unique program links across all listings")

    if max_programs:
        programs = programs[:max_programs]

    for pid, fallback_name in programs:
        url = DETAIL_URL_TMPL.format(pid=pid)
        print(f"[dsire]   {pid}  {fallback_name[:60]}")
        html = fetcher.get_rendered(
            url,
            wait_selector='[data-ng-controller="DetailsPageCtrl"]',
            wait_ms=4000,
        )
        if not html:
            continue
        program_data = _extract_ng_init_json(html)
        if not program_data:
            print(f"[dsire]   no ng-init JSON found for {pid}")
            continue
        program = program_data.get("program") or program_data
        try:
            rec = _build_record(program, pid)
            yield rec
        except Exception as e:
            print(f"[dsire]   build error on {pid}: {e}")
