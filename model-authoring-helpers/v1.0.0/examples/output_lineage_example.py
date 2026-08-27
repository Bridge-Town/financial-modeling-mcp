"""Trace a compact revenue calculation to one output cell."""

from __future__ import annotations

from lib.output_lineage import InputSourceRef, OutputLineageBuilder

builder = OutputLineageBuilder.from_environment(model_name="revenue_model")
output = builder.output("output.json")
price = output.input_value(
    "Unit price",
    42.0,
    group="Pricing",
    source_ref=InputSourceRef(
        "input_sheet",
        "Drivers!B2",
        sheet_id="sht_inputs",
        tab_id="tab_drivers",
        cell_ref="B2",
    ),
)
units = output.input_value("Units sold", 1_000, group="Volume")
revenue = output.logic_step("Revenue = price * units", price, units, value=42_000.0)
output.output_node("B2", "Total revenue", revenue)
builder.write()
