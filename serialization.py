"""Strict JSON serialization, including non-finite values read from target memory."""

import json
import math


def safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {k: safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
    return value


def dumps(value, **kwargs):
    return json.dumps(safe(value), allow_nan=False, **kwargs)
