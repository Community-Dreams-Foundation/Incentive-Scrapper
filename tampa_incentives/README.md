# Tampa Incentives Extractor

A Python pipeline that scrapes clean-energy, home-improvement, and disaster-
recovery incentive programs for Tampa / Hillsborough County and produces a
CSV matching the Dreamline AI Phase 1 extraction schema.

Built for [dreamlineai.org](https://dreamlineai.org) — Phase 1 of the
incentive data pipeline (manual + tooling) per the Dreamline AI Incentive
Brief, Section 6.

## What it does

1. Pulls programs from **12 sources** spanning federal, state, county, city,
   and utility levels (full list below).
2. Normalizes each program into the 13-column schema defined in the brief.
3. Auto-flags incomplete or regulatory-only records with `review_needed = Yes`.
4. Writes the combined CSV to
   `output/SaiMohan_extracted_tampa_incentives.csv` and a dedicated
   priority CSV to `output/hillsborough_priority/`.

## Sources covered

| Priority | Source | URL | Programs |
|---|---|---|---|
| **P0-PRIORITY** | Hillsborough Rebuilding for Tomorrow (CDBG-DR) | rebuildingfortomorrow.hcfl.gov | HRRP, MFH, SPH + 22 infra projects |
| P0 | DSIRE Florida + Federal | dsireusa.org | 50+ state/utility/local + federal IRA |
| P0 | Rewiring America (federal IRA) | rewiringamerica.org | HEEHRA, HOMES, 30C EV |
| P0 | Tampa Electric (TECO) | tampaelectric.com | HVAC tiers, geothermal, duct, insulation, etc. |
| P1 | Duke Energy Florida | duke-energy.com | Smart $aver tiers, heat pump, weatherization |
| P1 | My Safe Florida Home | mysafefloridahome.com | $10K mitigation grant + free inspection |
| P1 | IRS Energy Credits | irs.gov | §25C, §25D, home energy audit credit |
| P1 | Florida Housing Finance Corp | floridahousing.org | Hometown Heroes, FL Assist, HFA Preferred, SHIP, HOME |
| P1 | Hillsborough County Housing | hillsboroughcounty.org | SHIP rehab/DPA, CDBG, emergency repair, mobile home |
| P2 | City of Tampa | tampa.gov | JOC rehab, DPA, minor repair, CDBG |
| P2 | FEMA Hazard Mitigation | fema.gov | HMGP, BRIC, FMA |
| P2 | PACE financing | floridapace.gov, renewpace.com, fredelocal.com, ygrene.com | FPFA, RenewPACE, FRED, Ygrene |

## Output schema

| Column | Notes |
|---|---|
| program_name | Title as written on source |
| state | Florida (default) |
| city | Filled only when program is city/locality-specific; blank for statewide/federal |
| zip_codes | Filled for county- and city-level programs (Hillsborough ZIPs); blank for statewide/federal |
| incentive_type | One of: Grants, Rebates, Finance Solutions, Tax Credits, Investments |
| property_type | Source-faithful (e.g. "Residential, Commercial") |
| description | 1-3 sentence summary |
| eligibility_criteria | Source-faithful, full requirements |
| incentive_amount | Source-faithful free text |
| valid_until | ISO YYYY-MM-DD or blank if open-ended |
| updated_at | ISO YYYY-MM-DD when this record was extracted |
| review_needed | "Yes" if any required field is missing/ambiguous or program is regulatory-only |
| program_links | Direct URL to the official program page |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium  # one-time, ~180 MB — required for DSIRE
cp .env.example .env                   # optional, for API keys
```

## Usage

```bash
# Full run (all 12 sources)
python main.py

# Hillsborough priority sweep — writes only the CDBG-DR portal data
# to output/hillsborough_priority/hillsborough_priority_incentives.csv
python main.py --hillsborough-rebuilding-only \
  --output output/hillsborough_priority/hillsborough_priority_incentives.csv

# Single-source runs (handy for testing)
python main.py --dsire-only
python main.py --teco-only
python main.py --duke-energy-only
python main.py --my-safe-florida-home-only
python main.py --irs-energy-only
python main.py --florida-housing-only
python main.py --hillsborough-only
python main.py --tampa-city-only
python main.py --fema-only
python main.py --pace-only
python main.py --rewiring-america-only

# Cap programs per source (smoke testing)
python main.py --max 5

# Skip a source
python main.py --skip dsire

# Custom output path
python main.py --output my_extract.csv
```

The first run hits each source over the network. Pages are cached under
`cache/` keyed by URL hash, so re-runs are nearly instant and don't re-hit
servers.

## Project layout

```
tampa_incentives/
├── config.py                       # geography, type taxonomy, source registry
├── schema.py                       # Pydantic 13-column row model + auto-review-flagger
├── scrapers/
│   ├── base.py                     # polite fetcher: rate limit, robots.txt, cache,
│   │                               # Playwright + DataTables pagination
│   ├── dsire.py                    # DSIRE FL + Federal listings (paginated)
│   ├── rewiring_america.py         # federal IRA: API or static fallback
│   ├── teco.py                     # Tampa Electric residential rebates (per-tier)
│   ├── duke_energy.py              # Duke FL residential rebates (per-tier)
│   ├── my_safe_florida_home.py     # MSFH hurricane mitigation grant
│   ├── irs_energy.py               # §25C, §25D, energy audit credit
│   ├── florida_housing.py          # FHFC: Hometown Heroes, FL Assist, SHIP, HOME
│   ├── hillsborough.py             # County SHIP, CDBG, emergency, mobile home
│   ├── tampa_city.py               # City of Tampa rehab + DPA programs
│   ├── fema.py                     # HMGP, BRIC, FMA
│   ├── pace.py                     # FPFA, RenewPACE, FRED, Ygrene (paused)
│   └── hillsborough_rebuilding.py  # PRIORITY: CDBG-DR portal — HRRP, MFH, SPH + 22 infra
├── extractor.py                    # Claude-based LLM extraction (off by default)
├── main.py                         # orchestrator + CSV writer
├── cache/                          # disk-cached HTML/JSON (auto-created)
└── output/
    ├── SaiMohan_extracted_tampa_incentives.csv     # full pipeline output
    └── hillsborough_priority/
        └── hillsborough_priority_incentives.csv    # CDBG-DR portal only
```

## Hillsborough priority workflow

The `scrapers/hillsborough_rebuilding.py` scraper targets the County's
`rebuildingfortomorrow.hcfl.gov` CDBG-DR portal — the post-Hurricane
Helene/Milton recovery hub announced in May 2026. This is the highest-
priority source for the platform launch because:

- **HRRP is accepting applications NOW** ($211M, up to $350K per home)
- Eligibility covers every Hillsborough ZIP including Tampa, Temple Terrace, and Plant City
- MFH and SPH NOFAs open June 2026

The dedicated output file makes it trivial to import directly into the
`incentive_programs` table without filtering noise from other sources:

```bash
python main.py --hillsborough-rebuilding-only \
  --output output/hillsborough_priority/hillsborough_priority_incentives.csv
```

Result: 3 housing programs + 22 approved infrastructure projects = **25
rows, 0 review_needed**.

## Adding a new source

1. Create `scrapers/<name>.py` with a `scrape(fetcher, max_programs=None)`
   function that yields `IncentiveRecord` objects.
2. Register it in `main.SCRAPERS` and `config.SOURCES`.
3. If the source uses a category label not in `config.INCENTIVE_TYPE_MAP`,
   add the mapping. The brief only allows 5 types — everything must
   normalize to one of: Grants, Rebates, Finance Solutions, Tax Credits,
   Investments.

Follow the curated-baseline + live-verify pattern in `teco.py` or
`hillsborough_rebuilding.py` — that's the most reliable shape and survives
both transient site outages and authentic structural changes.

## Turning on LLM extraction

Some sources (PDFs, JS-rendered pages, free-text news articles) don't have
clean HTML structure. For those, `extractor.py` provides a Claude-based
fallback per the brief's Section 14.3. To enable:

1. Get an Anthropic API key
2. Add `ANTHROPIC_API_KEY=...` to `.env`
3. `pip install anthropic`
4. Set `USE_LLM_EXTRACTION = True` in `config.py`
5. In a scraper, call `extractor.extract_with_claude(...)` when BeautifulSoup
   parsing returns insufficient fields

## Politeness

- ≤ 1 request per second per host
- robots.txt checked before every fetch
- Identifying User-Agent (`DreamlineAI-IncentiveResearch/0.1`)
- Disk cache so reruns don't re-hit servers
- Pagination is rate-limited the same way

If a source's robots.txt disallows the path you need, this script will
skip it and log a warning. Don't override — find an alternative source or
a public API instead.

## DSIRE specifics

DSIRE is an AngularJS app whose listing uses DataTables pagination. The
scraper:

1. Uses Playwright (headless Chromium) to render the FL and federal
   listing pages.
2. Walks pagination by clicking the `.paginate_button.next` button
   repeatedly (up to 10 clicks → 500 entries) — without this we only
   captured the first 50 of 104 FL entries.
3. Extracts the program JSON directly from the `data-ng-init` attribute
   on the `DetailsPageCtrl` div on each detail page (more reliable than
   parsing the rendered DOM).

> The original parser was matching the *first* `data-ng-init` on the page,
> which is the AlertCtrl initializer (`{"danger":[],"success":[],...}`),
> not the program data. The DetailsPageCtrl anchor is now explicit.

## Known gaps / future work

- **Per-DSIRE-program amount parsing** is best-effort. Some DSIRE programs
  store amount only in the prose summary (not the `parameters` array).
  Roughly 25-30% of DSIRE rows end up with `review_needed = Yes` for this
  reason. The Phase 2 LLM parser is the right fix.
- **No deduplication across sources** yet. We did manually dedupe IRS
  §25C/§25D between Rewiring America and the new IRS scraper, but a
  general dedup pass (program_name + administrator + level) is Phase 2.
- **Regulatory policies** (Net Metering, Interconnection Standards, etc.)
  from DSIRE are not actually homeowner incentives. They're imported but
  flagged for review so a human can filter them out before DB load.
- **Live verification** in restricted network sandboxes (e.g., some CI
  runners) will print proxy/403 warnings but emit curated baselines
  anyway — the warning is for the operator, not the data consumer.
- **Phase 2 (LLM extraction) and Phase 3 (autonomous agents)** are
  scaffolded in `extractor.py` but off by default. See
  brief Section 6 for the build plan.

## Brief alignment

This Phase 1 pipeline produces ~100 records out of the brief's 150+
target, including every source listed in Section 3.3 of the brief
(DSIRE, Rewiring America, TECO, My Safe Florida Home, IRS, Florida
Housing, Hillsborough, Duke, City of Tampa, FEMA, PACE) plus the
County's CDBG-DR portal which surfaced after the brief shipped.

To push above 150 records:
- Expand TECO/Duke per-tier baselines further (more SEER tiers, more
  appliances)
- Add Pinellas, Pasco, and Polk county SHIP programs (Tampa Bay MSA
  expansion, brief Section 16.1 Phase 2)
- Enable LLM extraction on review-flagged rows to fill in their
  missing amount fields
