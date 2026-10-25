# Bridge Town model-authoring helpers v1.7.0

This release contains the supported helpers for Python models running in the
Bridge Town sandbox:

- `bsheet_reader.py` is the canonical short-name reader. `BSheetReader` reads
  new `.bsheet.json` documents and historical `.btsheet.json` documents
  without collapsing missing, blank, formula-error, and numeric-zero states.
  It reads documents up to 4 MiB and records up to 40,000 distinct cells in
  its default value-free lineage telemetry.
- `native_sheet_reader.py` preserves the `lib.native_sheet_reader` import and
  `NativeSheetReader` name for models that still use them. It delegates to
  `bsheet_reader.py` and reads both suffixes.
- `output_lineage.py` emits schema v4 `output_lineage.json` dependency graphs
  for cell explanations and binds named scalar or JSON Pointer metrics
  to existing graph nodes, including outputs without a materialized sheet.

Copy a helper byte-for-byte to the target path shown in `manifest.json`. Verify
the download against `SHA256SUMS` before committing it to a model repository.
The helpers make no network calls. Both sheet-reader modules use only the
Python standard library; `output_lineage.py` additionally imports `pandas`,
which is available in the Bridge Town model sandbox.

`output_lineage.py` supports up to 6,000 nodes, 15,000 edges, 6,000 point or
compressed range coordinate entries, and 6,000 named metric bindings per
output. Run-wide ceilings are 150,000 nodes, 375,000 edges, 150,000 coordinate
entries and 150,000 metric bindings across 25 outputs. JSON Pointers are
limited to 2,048 characters and aliases to 200. The compact JSON artifact
limit is 32 MiB; counts and serialized bytes are separate limits. Coordinate
ranges remain one entry regardless of their cell area.

Coordinate overlap validation uses a row sweep with active column intervals,
and dependency cycle checks use iterative graph traversal. Both keep validation
work bounded for large, otherwise-valid traces. Repeated automatic node labels
use collision-safe generated suffixes.

Documentation:

- <https://www.bridgetown.builders/docs/guides/native-sheet-model-inputs>
- <https://www.bridgetown.builders/docs/guides/output-lineage-authoring>

The source is MIT licensed. Security reports should follow the public
repository's `SECURITY.md`; do not include customer data in a report.
