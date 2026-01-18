"""Metric data extraction utilities.

Consolidated helpers for extracting values from PCP metric responses.
"""

from __future__ import annotations


def get_first_value(data: dict, metric: str, default: float = 0.0) -> float:
    """Get first instance value from fetched data."""
    metric_data = data.get(metric, {})
    instances = metric_data.get("instances", {})
    if instances:
        return float(next(iter(instances.values()), default))
    return default


def get_scalar_value(response: dict, metric: str, default: int = 0) -> int:
    """Get scalar value from raw fetch response."""
    for v in response.get("values", []):
        if v.get("name") == metric:
            instances = v.get("instances", [])
            if instances:
                return int(instances[0].get("value", default))
    return default


def sum_instances(data: dict, metric: str) -> float:
    """Sum all instance values for a metric."""
    metric_data = data.get(metric, {})
    instances = metric_data.get("instances", {})
    return sum(float(v) for v in instances.values())


def extract_help_text(metric_dict: dict, default: str = "") -> str:
    """Extract help text from metric info dictionary.

    Tries text-help first, then falls back to text-oneline.
    """
    return metric_dict.get("text-help") or metric_dict.get("text-oneline") or default


def extract_timestamp(response: dict) -> float:
    """Extract timestamp from pmproxy response.

    Converts PCP timestamp (seconds + microseconds) to float seconds.
    """
    ts = response.get("timestamp", {})
    return ts.get("s", 0) + ts.get("us", 0) / 1e6


__all__ = [
    "get_first_value",
    "get_scalar_value",
    "sum_instances",
    "extract_help_text",
    "extract_timestamp",
]
