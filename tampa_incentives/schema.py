"""
Schema for the output CSV row. Matches Anirudh's 12 columns + zip_codes.

review_needed is auto-set to 'Yes' if any required field is missing/ambiguous.
"""

from __future__ import annotations
from datetime import date
from typing import Optional, Literal
from pydantic import BaseModel, Field, model_validator


IncentiveType = Literal[
    "Grants", "Rebates", "Finance Solutions", "Tax Credits", "Investments"
]


class IncentiveRecord(BaseModel):
    """One row in the final CSV."""

    program_name: str
    state: str = "Florida"
    city: Optional[str] = None  # None = statewide / not city-specific
    zip_codes: Optional[str] = None  # comma-separated, or None for statewide
    incentive_type: Optional[IncentiveType] = None
    property_type: Optional[str] = None
    description: Optional[str] = None
    eligibility_criteria: Optional[str] = None
    incentive_amount: Optional[str] = None  # free-text, source-faithful
    valid_until: Optional[str] = None  # ISO YYYY-MM-DD or None
    updated_at: Optional[str] = None  # ISO YYYY-MM-DD
    review_needed: Literal["Yes", "No"] = "No"
    program_links: Optional[str] = None

    # Required-field set per Anirudh's spec. If any of these are empty/None,
    # we auto-flag review_needed=Yes.
    _REQUIRED_FOR_CLEAN = (
        "program_name",
        "state",
        "incentive_type",
        "property_type",
        "description",
        "incentive_amount",
        "program_links",
    )

    @model_validator(mode="after")
    def _auto_flag_review(self) -> "IncentiveRecord":
        if self.review_needed == "Yes":
            return self
        for field in self._REQUIRED_FOR_CLEAN:
            value = getattr(self, field)
            if value is None or (isinstance(value, str) and not value.strip()):
                self.review_needed = "Yes"
                break
        return self

    def to_csv_row(self) -> dict:
        """Return a dict in the column order Anirudh asked for."""
        return {
            "program_name": self.program_name or "",
            "state": self.state or "",
            "city": self.city or "",
            "zip_codes": self.zip_codes or "",
            "incentive_type": self.incentive_type or "",
            "property_type": self.property_type or "",
            "description": self.description or "",
            "eligibility_criteria": self.eligibility_criteria or "",
            "incentive_amount": self.incentive_amount or "",
            "valid_until": self.valid_until or "",
            "updated_at": self.updated_at or "",
            "review_needed": self.review_needed,
            "program_links": self.program_links or "",
        }
