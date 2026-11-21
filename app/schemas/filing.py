"""Filing event response."""

from datetime import date

from pydantic import BaseModel


class FilingRead(BaseModel):
    ticker: str
    company_name: str
    accession_number: str
    form: str
    filing_date: date
    primary_document: str | None = None
