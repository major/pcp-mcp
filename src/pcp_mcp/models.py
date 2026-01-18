"""Pydantic response models for strict output schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MetricValue(BaseModel):
    """A single metric value from PCP."""

    name: str = Field(description="Full metric name")
    value: float | int | str | None = Field(description="Metric value")
    units: str | None = Field(default=None, description="Unit of measurement")
    semantics: str | None = Field(default=None, description="counter, instant, or discrete")
    instance: str | None = Field(default=None, description="Instance name if per-instance metric")


class MetricInfo(BaseModel):
    """Metadata about a PCP metric."""

    name: str = Field(description="Full metric name")
    type: str = Field(description="Data type (u32, u64, float, string, etc.)")
    semantics: str = Field(description="counter, instant, or discrete")
    units: str = Field(description="Unit of measurement")
    help_text: str | None = Field(default=None, description="Metric help text")
    indom: str | None = Field(default=None, description="Instance domain if per-instance")


class MetricSearchResult(BaseModel):
    """Result from searching for metrics."""

    name: str = Field(description="Full metric name")
    help_text: str | None = Field(default=None, description="Brief description")


class InstancedMetric(BaseModel):
    """Metric with per-instance values (e.g., per-CPU, per-disk)."""

    name: str = Field(description="Metric name")
    instances: dict[str, float | int] = Field(
        description="Per-instance values, e.g., {'cpu0': 15.2, 'sda': 1000}"
    )
    aggregate: float | None = Field(
        default=None, description="Optional rollup (sum/avg) for quick reference"
    )
