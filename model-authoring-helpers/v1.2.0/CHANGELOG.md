# Changelog

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
