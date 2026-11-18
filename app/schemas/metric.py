"""Metric registry response."""

from pydantic import BaseModel, ConfigDict

from app.models.metric_definition import MetricDirection


class MetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    category: str
    unit: str
    direction: MetricDirection
    formula: str
    description: str
    is_derived: bool
