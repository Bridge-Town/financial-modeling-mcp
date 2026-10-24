"""Read required driver cells through the short-name bsheet reader."""

from __future__ import annotations

import json

from lib.bsheet_reader import BSheetReader

with BSheetReader() as sheets:
    base_revenue = sheets.read_value("sht_inputs", "tab_drivers", "B2")
    growth_rate = sheets.read_value("sht_inputs", "tab_drivers", "B3")

result = {
    "base_revenue": base_revenue,
    "growth_rate": growth_rate,
    "next_period_revenue": round(float(base_revenue) * (1 + float(growth_rate)), 2),
}
print(json.dumps(result, sort_keys=True))
