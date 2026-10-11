# Bridge Town model-authoring helpers v1.2.0

This release contains the two supported helpers for Python models running in
the Bridge Town sandbox:

- `native_sheet_reader.py` reads committed Native Sheet inputs without
  collapsing missing, blank, formula-error, and numeric-zero states.
- `output_lineage.py` creates a validated `output_lineage.json` dependency
  graph for cell explanations.

Copy a helper byte-for-byte to the target path shown in `manifest.json`. Verify
the download against `SHA256SUMS` before committing it to a model repository.
The helpers make no network calls. `native_sheet_reader.py` uses only the Python
standard library; `output_lineage.py` additionally imports `pandas`, which is
available in the Bridge Town model sandbox.

`output_lineage.py` supports up to 6,000 nodes and 15,000 edges per output,
with run-wide ceilings of 150,000 nodes and 375,000 edges across 25 outputs.
The compact JSON artifact limit is 32 MiB; node and edge counts remain
independent of that byte budget.

Documentation:

- <https://www.bridgetown.builders/docs/guides/native-sheet-model-inputs>
- <https://www.bridgetown.builders/docs/guides/output-lineage-authoring>

The source is MIT licensed. Security reports should follow the public
repository's `SECURITY.md`; do not include customer data in a report.
