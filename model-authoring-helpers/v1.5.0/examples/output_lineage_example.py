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
builder.write()  # writes /outputs/output_lineage.json
