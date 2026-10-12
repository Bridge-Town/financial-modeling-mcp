"""Read two required driver cells and emit value-free read telemetry."""

from __future__ import annotations

import json

from lib.native_sheet_reader import NativeSheetReader

with NativeSheetReader() as sheets:
    base_revenue = sheets.read_value("sht_inputs", "tab_drivers", "B2")
    growth_rate = sheets.read_value("sht_inputs", "tab_drivers", "B3")

result = {
    "base_revenue": base_revenue,
    "growth_rate": growth_rate,
    "next_period_revenue": round(float(base_revenue) * (1 + float(growth_rate)), 2),
}
print(json.dumps(result, sort_keys=True))
