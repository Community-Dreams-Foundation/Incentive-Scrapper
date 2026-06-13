"""
LLM-based extraction (disabled in v1; activated by USE_LLM_EXTRACTION=True
in config.py + ANTHROPIC_API_KEY in env).

Used as a fallback when a scraper hits an unstructured page (PDF, free-text
news article, oddly-formatted utility page) and can't pull clean fields with
BeautifulSoup. The Dreamline brief recommends this hybrid pattern.
"""

from __future__ import annotations
import json
import os
import re
from typing import Optional

from schema import IncentiveRecord


SYSTEM_PROMPT = """\
You are a structured data extraction specialist. Extract incentive program
details from the provided content and return a JSON object matching the schema
exactly. Only extract information explicitly stated in the content. If a field
is not mentioned, return null for that field. Never infer or assume values. Do
not hallucinate amounts or eligibility criteria.
"""

USER_PROMPT_TMPL = """\
Extract the incentive program details from the following content scraped from {source_url}.

Source name: {source_name}
Content type: {content_type}

Return ONLY a JSON object (no preamble, no code fence) matching this schema:
{{
  "program_name": str,
  "incentive_type": "Grants" | "Rebates" | "Finance Solutions" | "Tax Credits" | "Investments",
  "property_type": str | null,
  "description": str (1-3 sentences) | null,
  "eligibility_criteria": str | null,
  "incentive_amount": str (free-text, source-faithful) | null,
  "valid_until": "YYYY-MM-DD" | null,
  "program_links": str (URL) | null
}}

CONTENT:
{content}
"""


def extract_with_claude(
    *,
    raw_content: str,
    source_url: str,
    source_name: str,
    content_type: str = "html_text",
    state: str = "Florida",
    city: Optional[str] = None,
    zip_code: Optional[str] = None,
) -> Optional[IncentiveRecord]:
    """Call Claude to extract a structured record. Returns None on failure
    or when ANTHROPIC_API_KEY is not set.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic  # type: ignore[import-not-found]
    except ImportError:
        print("[llm] anthropic SDK not installed — `pip install anthropic`")
        return None

    client = anthropic.Anthropic(api_key=api_key)
    prompt = USER_PROMPT_TMPL.format(
        source_url=source_url,
        source_name=source_name,
        content_type=content_type,
        content=raw_content[:50_000],  # safe truncation
    )
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        print(f"[llm] API error: {e}")
        return None

    text = "".join(b.text for b in resp.content if hasattr(b, "text"))
    # strip code fences if model adds them
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        print(f"[llm] non-JSON response: {text[:200]}")
        return None

    # Map LLM output → schema (strict types preserve invariants)
    return IncentiveRecord(
        program_name=data.get("program_name") or "Unknown program",
        state=state,
        city=city,
        zip_code=zip_code,
        incentive_type=data.get("incentive_type"),
        property_type=data.get("property_type"),
        description=data.get("description"),
        eligibility_criteria=data.get("eligibility_criteria"),
        incentive_amount=data.get("incentive_amount"),
        valid_until=data.get("valid_until"),
        program_links=data.get("program_links") or source_url,
    )
