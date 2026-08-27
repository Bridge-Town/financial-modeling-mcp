# Bridge Town model-authoring helpers v1.0.0

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

Documentation:

- <https://www.bridgetown.builders/docs/guides/native-sheet-model-inputs>
- <https://www.bridgetown.builders/docs/guides/output-lineage-authoring>

The source is MIT licensed. Security reports should follow the public
repository's `SECURITY.md`; do not include customer data in a report.
