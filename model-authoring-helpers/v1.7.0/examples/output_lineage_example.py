"""Trace a compact revenue table to one output cell."""

from __future__ import annotations

import json
import os
from pathlib import Path

from lib.output_lineage import OutputLineageBuilder

builder = OutputLineageBuilder.from_environment(model_name="example_model")
output = builder.output("output.json")  # exact persisted filename
revenue = output.input_value("Revenue", 1_000_000, source_ref=("parameter", "revenue"))
output.output_node("B2", "Revenue", revenue, value=1_000_000, auto_code_ref=False)
output_path = Path(os.environ.get("SANDBOX_OUTPUT_PATH", "/outputs")) / "output.json"
output_path.write_text(
    json.dumps({"columns": ["Metric", "Value"], "rows": [["Revenue", revenue.value]]}),
    encoding="utf-8",
)
metrics = builder.output("metrics.json")
trials = metrics.input_value("Year 1 trials", 120, source_ref=("parameter", "trials"))
price = metrics.input_value("Trial price", 8.5, source_ref=("parameter", "price"))
year1_revenue = metrics.logic_step(
    "Revenue = trials * price", trials, price, value=1_020.0, auto_code_ref=False
)
metrics.bind_metric("year1_revenue", year1_revenue)
metrics.bind_json_pointer("/year1/revenue", year1_revenue, alias="revenue")
metrics.bind_metric("trial_count", trials)
metrics.bind_json_pointer("/year1/trials", trials)
metrics.bind_json_pointer("/nested/a~1b/~0key", price)
metrics_path = Path(os.environ.get("SANDBOX_OUTPUT_PATH", "/outputs")) / "metrics.json"
metrics_path.write_text(
    json.dumps(
        {
            "year1": {"revenue": year1_revenue.value, "trials": trials.value},
            "nested": {"a/b": {"~key": price.value}},
        }
    ),
    encoding="utf-8",
)
builder.write()  # writes /outputs/output_lineage.json
