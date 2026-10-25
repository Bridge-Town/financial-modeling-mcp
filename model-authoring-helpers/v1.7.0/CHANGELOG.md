# Changelog

## v1.7.0 — 2026-10-24

- Raise the Native Sheet reader's per-document byte ceiling to 4 MiB.
- Increase default value-free read-set telemetry to 40,000 entries so a full
  report-sized input can retain complete cell identity evidence.
- Keep the reader and telemetry bounded; older immutable release assets remain
  unchanged.

## v1.6.0 — 2026-10-23

- Bind named scalar aliases and RFC 6901 JSON Pointers to existing lineage
  nodes, including metrics written before any sheet is materialized.
- Add bounded, output-local binding validation; the server retains schema
  v1/v2/v3 artifacts and their existing coordinate mappings.

## v1.5.0 — 2026-10-13

- Publish `bsheet_reader.py` with `BSheetReader` as the short-name API.
- Read canonical `.bsheet.json` files and historical `.btsheet.json` files,
  preferring the canonical path when both exist.
- Ship a `native_sheet_reader.py` compatibility module for existing imports;
  earlier versioned reader files remain unchanged.
- Emit `bsheet_reader` read-set instrumentation while retaining the established
  `native_sheet_read_set.json` artifact path.

## v1.4.0 — 2026-10-11

- Stream compact output-lineage JSON to disk in bounded chunks while enforcing
  the UTF-8 artifact byte limit.

## v1.3.0 — 2026-10-11

- Validate point and compressed-range overlaps with a sweep-line algorithm;
  preserve inclusive intersections without expanding ranges into cells.
- Use iterative cycle validation and per-base automatic-ID suffix counters.
- Support 6,000 coordinate entries per output and 150,000 per run while
  preserving the 32 MiB compact artifact limit.

## v1.2.0 — 2026-10-11

- Raise authored lineage capacity to 6,000 nodes and 15,000 edges per output,
  with 150,000/375,000 run-wide index ceilings and a 32 MiB compact artifact cap.
- Emit compact lineage JSON so representative 25-output traces fit the finite
  artifact and sandbox budgets.
- Keep the explanation display and forward traversal response limits bounded.

## v1.1.0 — 2026-09-05

- Read Native Sheet documents only from the current public `sheets/` location.
- Remove the retired hidden-directory fallback and its compatibility wording.
- Republish integrity hashes and immutable source links for the current helper.

## v1.0.0 — 2026-08-27

- Publish the standalone, standard-library-only Native Sheet reader.
- Publish the standalone output-lineage builder with its canonical validation
  contract inlined into one copyable file.
- Add bounded sandbox examples, SHA-256 integrity data, licensing, and
  ownership metadata.
