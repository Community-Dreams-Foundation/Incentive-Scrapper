# Tampa Incentives Extractor

A Python pipeline that scrapes clean-energy and home-improvement incentive
programs for Tampa / Hillsborough County and produces a CSV matching the
extraction schema in `Incentive_Data_Extraction_Info.pdf`.

## What it does

1. Pulls programs from three sources:
   - **DSIRE** — Florida state, utility, and local programs (web scraper)
   - **Rewiring America** — federal IRA programs (live API if key present, else curated static list)
   - **TECO / Tampa Electric** — utility rebates (live page check + curated baseline)
2. Normalizes each program into Anirudh's 13-column schema
3. Auto-flags incomplete records with `review_needed = Yes`
4. Writes `output/your_name_extracted_tampa_incentives.csv`

## Output schema

| Column | Notes |
|---|---|
| program_name | Title as written on source |
| state | Florida (default) |
| city | Filled only when program is city/locality-specific; blank for statewide/federal |
| zip_codes | Filled only for local programs (Hillsborough ZIPs); blank for statewide/federal |
| incentive_type | One of: Grants, Rebates, Finance Solutions, Tax Credits, Investments |
| property_type | Source-faithful (e.g. "Residential, Commercial") — never "Other"/"Neither" |
| description | 1-3 sentence summary |
| eligibility_criteria | Source-faithful |
| incentive_amount | Source-faithful free text |
| valid_until | ISO YYYY-MM-DD or blank if open-ended |
| updated_at | ISO YYYY-MM-DD when this record was extracted |
| review_needed | "Yes" if any required field missing/ambiguous, else "No" |
| program_links | Direct URL to the official program page |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # optional, for API keys
```

## Usage

```bash
# Full run (all sources)
python main.py

# Just one source (handy for testing)
python main.py --dsire-only
python main.py --rewiring-america-only
python main.py --teco-only

# Cap programs per source
python main.py --max 10

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
├── config.py              # geography, type taxonomy, source registry
├── schema.py              # Pydantic 13-column row model + auto-review-flagger
├── scrapers/
│   ├── base.py            # polite fetcher (rate limit, robots.txt, cache)
│   ├── dsire.py           # DSIRE FL listing → detail pages
│   ├── rewiring_america.py# federal IRA: API or static fallback
│   └── teco.py            # Tampa Electric residential rebates
├── extractor.py           # Claude-based LLM extraction (off by default)
├── main.py                # orchestrator + CSV writer
├── cache/                 # disk-cached HTML/JSON (auto-created)
└── output/                # final CSV (auto-created)
```

## Adding a new source

1. Create `scrapers/<name>.py` with a `scrape(fetcher, max_programs=None)`
   function that yields `IncentiveRecord` objects.
2. Register it in `main.SCRAPERS`.
3. If the source uses a label not in `config.INCENTIVE_TYPE_MAP`, add the
   mapping. Anirudh's spec only allows 5 types; everything must normalize
   to one of them.

Easy candidates to add next (priority order):
- **Duke Energy Florida** rebates (P0 — second-largest Tampa Bay utility)
- **My Safe Florida Home** ($10,000 hurricane mitigation grant — high-value, well-publicized)
- **Florida Housing Finance Corporation** (SHIP, HOME, DPA)
- **Hillsborough County SHIP** (county rehabilitation grants)
- **PACE financing providers** (Ygrene / RenewPACE / FRED)

## Turning on LLM extraction

Some sources (PDFs, JS-rendered pages, free-text news articles) don't have
clean HTML structure. For those, `extractor.py` provides a Claude-based
fallback. To enable:

1. Get an Anthropic API key
2. Add `ANTHROPIC_API_KEY=...` to `.env`
3. `pip install anthropic`
4. Set `USE_LLM_EXTRACTION = True` in `config.py`
5. In a scraper, call `extractor.extract_with_claude(...)` when BeautifulSoup
   parsing returns insufficient fields

The prompt template is already built per the Dreamline brief's spec
(Section 14.3): the model is instructed to return null for missing fields
and never hallucinate amounts.

## Politeness

- ≤ 1 request per second per host
- robots.txt checked before every fetch
- Identifying User-Agent
- Disk cache so reruns don't re-hit servers

If a source's robots.txt disallows the path you need, this script will
skip it and log a warning. Don't override that — find an alternative
source or a public API instead.

## Known gaps / future work

- The legacy DSIRE public API was retired (returns 403 since late 2024); the
  current API is paid. We scrape the public web listing as a workaround.
- Rewiring America's API requires a free API key; without one, we use a
  curated static list of the 5 main federal IRA programs.
- TECO's full program list isn't behind a clean API; we use a curated
  baseline + live page check for closure detection.
- `valid_until` parsing is best-effort; ambiguous date phrasing falls
  through to None and triggers review.
- No deduplication yet — if two sources list the same federal credit, both
  rows appear. Phase 2 work.
