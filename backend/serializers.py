"""
serializers.py — coerce pandas/agent outputs into JSON-native structures.

The reused Python layer returns DataFrames and dicts containing pandas Timestamps and tuples
(e.g. compute_velocity's peak_window). FastAPI's JSON encoder can't handle those, so every
endpoint funnels its payload through jsonable() here.
"""
import math
from datetime import date, datetime

import pandas as pd


def jsonable(obj):
    """Recursively convert pandas/NumPy/datetime values into JSON-native Python types."""
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        # Strict JSON rejects NaN/Infinity — map to null.
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, pd.DataFrame):
        return [jsonable(rec) for rec in obj.to_dict("records")]
    if isinstance(obj, pd.Series):
        return jsonable(obj.to_dict())
    if isinstance(obj, (pd.Timestamp, datetime, date)):
        return obj.isoformat()
    if obj is pd.NaT:
        return None
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [jsonable(v) for v in obj]
    # numpy scalars expose .item()
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except (ValueError, TypeError):
            pass
    # pandas NaN
    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    return str(obj)
