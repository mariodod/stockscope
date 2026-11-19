"""Request and response models for the screener."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.metric_definition import MetricDirection


class FilterOp(StrEnum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    BETWEEN = "between"
    IN = "in"
    IS_NULL = "is_null"


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


class FilterCondition(BaseModel):
    metric: str
    op: FilterOp
    value: Any = None

    @model_validator(mode="after")
    def check_value_shape(self) -> "FilterCondition":
        if self.op in {FilterOp.BETWEEN, FilterOp.IN}:
            if not isinstance(self.value, list) or not self.value:
                raise ValueError(f"{self.op} requires a non-empty list value")
            if self.op is FilterOp.BETWEEN and len(self.value) != 2:
                raise ValueError("between requires exactly two bounds")
        elif self.op is FilterOp.IS_NULL:
            if self.value is not None and not isinstance(self.value, bool):
                raise ValueError("is_null requires a boolean value or null")
        elif self.value is None:
            raise ValueError(f"{self.op} requires a value")
        return self


class SortSpec(BaseModel):
    metric: str
    dir: SortDirection = SortDirection.DESC


class RankingSpec(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)

    @field_validator("weights")
    @classmethod
    def normalize_weights(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            return value
        if any(weight < 0 for weight in value.values()):
            raise ValueError("weights must not be negative")
        total = sum(value.values())
        if total <= 0:
            raise ValueError("at least one weight must be positive")
        return {key: weight / total for key, weight in value.items()}


class ScreenRequest(BaseModel):
    filters: list[FilterCondition] = Field(default_factory=list)
    sort: list[SortSpec] = Field(default_factory=list)
    ranking: RankingSpec | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class CompanySummary(BaseModel):
    ticker: str
    name: str
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None
    score_components: dict[str, float] = Field(default_factory=dict)
    missing_metrics: list[str] = Field(default_factory=list)


class PagedCompanies(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[CompanySummary]


class LatestMetric(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_key: str
    label: str
    value: Any
    unit: str
    direction: MetricDirection
    period: str
    source: str
    as_of_date: Any


class FactPoint(BaseModel):
    metric_key: str
    period: str
    value: Any
    as_of_date: Any
    source: str


class CompanyDetail(BaseModel):
    ticker: str
    name: str
    cik: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str
    currency: str
    latest_metrics: list[LatestMetric]
    history: list[FactPoint]


class SectorCounts(BaseModel):
    sectors: list[str]
    industries: list[str]
