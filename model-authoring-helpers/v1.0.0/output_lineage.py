"""Standalone limits and author-time validation for output lineage artifacts.

The server imports this module directly. The output-lineage scaffold generator
also inlines it ahead of ``output_lineage_helpers.py`` so copied model code has
the identical contract without importing the Bridge Town server package.
"""

from __future__ import annotations

import json
import re

OUTPUT_LINEAGE_LIMITS: dict[str, int] = {
    "MAX_ARTIFACT_BYTES": 512 * 1024,
    "MAX_OUTPUTS": 25,
    "MAX_NODES_PER_OUTPUT": 60,
    "MAX_EDGES_PER_OUTPUT": 150,
    "MAX_INDEX_NODES": 1_500,
    "MAX_INDEX_EDGES": 3_750,
    "MAX_INDEX_COORDINATES": 1_500,
    "MAX_ID_LENGTH": 128,
    "MAX_LABEL_LENGTH": 200,
    "MAX_VALUE_LENGTH": 500,
    "MAX_REF_LENGTH": 256,
    "MAX_GROUP_LENGTH": 64,
    "MAX_OUTPUT_NAME_LENGTH": 200,
    "MAX_RUN_ID_LENGTH": 128,
    "MAX_MODEL_NAME_LENGTH": 255,
    "MAX_OUTPUT_CELL_REF_LENGTH": 12,
    "MAX_CANONICAL_ID_LENGTH": 128,
    "MAX_CANONICAL_CELL_REF_LENGTH": 12,
    "MAX_IDENTITY_DIAGNOSTIC_LENGTH": 128,
}

MAX_ARTIFACT_BYTES = OUTPUT_LINEAGE_LIMITS["MAX_ARTIFACT_BYTES"]
MAX_OUTPUTS = OUTPUT_LINEAGE_LIMITS["MAX_OUTPUTS"]
MAX_NODES_PER_OUTPUT = OUTPUT_LINEAGE_LIMITS["MAX_NODES_PER_OUTPUT"]
MAX_EDGES_PER_OUTPUT = OUTPUT_LINEAGE_LIMITS["MAX_EDGES_PER_OUTPUT"]
MAX_INDEX_NODES = OUTPUT_LINEAGE_LIMITS["MAX_INDEX_NODES"]
MAX_INDEX_EDGES = OUTPUT_LINEAGE_LIMITS["MAX_INDEX_EDGES"]
MAX_INDEX_COORDINATES = OUTPUT_LINEAGE_LIMITS["MAX_INDEX_COORDINATES"]
MAX_ID_LENGTH = OUTPUT_LINEAGE_LIMITS["MAX_ID_LENGTH"]
MAX_LABEL_LENGTH = OUTPUT_LINEAGE_LIMITS["MAX_LABEL_LENGTH"]
MAX_VALUE_LENGTH = OUTPUT_LINEAGE_LIMITS["MAX_VALUE_LENGTH"]
MAX_REF_LENGTH = OUTPUT_LINEAGE_LIMITS["MAX_REF_LENGTH"]
MAX_GROUP_LENGTH = OUTPUT_LINEAGE_LIMITS["MAX_GROUP_LENGTH"]
MAX_OUTPUT_NAME_LENGTH = OUTPUT_LINEAGE_LIMITS["MAX_OUTPUT_NAME_LENGTH"]
MAX_RUN_ID_LENGTH = OUTPUT_LINEAGE_LIMITS["MAX_RUN_ID_LENGTH"]
MAX_MODEL_NAME_LENGTH = OUTPUT_LINEAGE_LIMITS["MAX_MODEL_NAME_LENGTH"]
MAX_OUTPUT_CELL_REF_LENGTH = OUTPUT_LINEAGE_LIMITS["MAX_OUTPUT_CELL_REF_LENGTH"]
MAX_CANONICAL_ID_LENGTH = OUTPUT_LINEAGE_LIMITS["MAX_CANONICAL_ID_LENGTH"]
MAX_CANONICAL_CELL_REF_LENGTH = OUTPUT_LINEAGE_LIMITS["MAX_CANONICAL_CELL_REF_LENGTH"]
MAX_IDENTITY_DIAGNOSTIC_LENGTH = OUTPUT_LINEAGE_LIMITS["MAX_IDENTITY_DIAGNOSTIC_LENGTH"]

CELL_REF_PATTERN = r"^[A-Z]+[1-9][0-9]*$"
_CELL_REF_RE = re.compile(CELL_REF_PATTERN)
_CANONICAL_ID_RE = re.compile(rf"^[A-Za-z0-9_-]{{1,{MAX_CANONICAL_ID_LENGTH}}}$")
_CANONICAL_CELL_REF_RE = re.compile(r"^[A-Z]{1,3}[1-9][0-9]*$")


class LineageBuildError(Exception):
    """Raised when authoring code constructs an invalid or oversized trace graph."""

    def __init__(self, category: str, reason: str) -> None:
        self.category = category
        self.reason = reason
        super().__init__(f"{category}: {reason}")


def parse_cell_ref(cell_ref: str) -> tuple[int, int]:
    """Return the 1-based ``(row, column)`` indexes for an A1 reference.

    This deliberately performs no artifact-specific error mapping. Callers at
    the author and server boundaries translate ``ValueError`` into their own
    stable validation category.
    """
    if len(cell_ref) > MAX_OUTPUT_CELL_REF_LENGTH or not _CELL_REF_RE.fullmatch(cell_ref):
        raise ValueError("invalid cell reference")
    match = re.fullmatch(r"([A-Z]+)([1-9][0-9]*)", cell_ref)
    assert match is not None
    letters, row_text = match.groups()
    column = 0
    for char in letters:
        column = column * 26 + ord(char) - ord("A") + 1
    return int(row_text), column


def coordinate_range_bounds(start: str, end: str) -> tuple[int, int, int, int]:
    """Return ``(start_row, end_row, start_col, end_col)`` for a rectangle.

    Ranges must be authored top-left to bottom-right. Normalizing reversed
    corners would hide authoring mistakes and make overlap diagnostics depend
    on reader behavior.
    """
    start_row, start_col = parse_cell_ref(start)
    end_row, end_col = parse_cell_ref(end)
    if start_row > end_row or start_col > end_col:
        raise ValueError("range corners are reversed")
    return start_row, end_row, start_col, end_col


def coordinate_range_contains(start: str, end: str, cell_ref: str) -> bool:
    """Whether *cell_ref* is inside the inclusive rectangular range."""
    start_row, end_row, start_col, end_col = coordinate_range_bounds(start, end)
    row, column = parse_cell_ref(cell_ref)
    return start_row <= row <= end_row and start_col <= column <= end_col


def coordinate_ranges_overlap(
    first: tuple[int, int, int, int], second: tuple[int, int, int, int]
) -> bool:
    """Whether two inclusive ``(row,row,col,col)`` rectangles overlap."""
    first_start_row, first_end_row, first_start_col, first_end_col = first
    second_start_row, second_end_row, second_start_col, second_end_col = second
    return (
        first_start_row <= second_end_row
        and second_start_row <= first_end_row
        and first_start_col <= second_end_col
        and second_start_col <= first_end_col
    )


def _require_bounded_text(value: object, *, field: str, limit: int, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise LineageBuildError("malformed", f"{context} has an empty or non-string {field}")
    if len(value) > limit:
        raise LineageBuildError(
            "limit_exceeded", f"{context} {field} exceeds the {limit}-character limit"
        )
    return value


def _validate_source_ref(
    source_ref: object,
    *,
    output_name: str,
    node_id: str,
    seen_exact: dict[tuple[str, str, str], str],
) -> None:
    if not isinstance(source_ref, dict):
        raise LineageBuildError(
            "malformed", f"output {output_name!r} node {node_id!r} has a malformed source_ref"
        )
    context = f"output {output_name!r} node {node_id!r} source_ref"
    kind = source_ref.get("kind")
    if kind not in {"input_sheet", "data_source", "parameter"}:
        raise LineageBuildError("malformed", f"{context} has an invalid kind")
    _require_bounded_text(source_ref.get("ref"), field="ref", limit=MAX_REF_LENGTH, context=context)

    identity_state = source_ref.get("identity_state")
    canonical_values = tuple(source_ref.get(field) for field in ("sheet_id", "tab_id", "cell_ref"))
    if identity_state is None and canonical_values == (None, None, None):
        return
    if kind != "input_sheet" or identity_state not in {"exact", "partial"}:
        raise LineageBuildError(
            "invalid_source_identity",
            f"{context} must use kind='input_sheet' and identity_state='exact' or 'partial'",
        )
    sheet_id = _require_bounded_text(
        canonical_values[0], field="sheet_id", limit=MAX_CANONICAL_ID_LENGTH, context=context
    )
    tab_id = _require_bounded_text(
        canonical_values[1], field="tab_id", limit=MAX_CANONICAL_ID_LENGTH, context=context
    )
    if not _CANONICAL_ID_RE.match(sheet_id) or not _CANONICAL_ID_RE.match(tab_id):
        raise LineageBuildError(
            "invalid_source_identity", f"{context} has an invalid sheet_id or tab_id"
        )
    cell_ref_value = canonical_values[2]
    if identity_state == "partial":
        if cell_ref_value is not None:
            raise LineageBuildError(
                "invalid_source_identity", f"{context} is partial but includes cell_ref"
            )
        return
    cell_ref = _require_bounded_text(
        cell_ref_value,
        field="cell_ref",
        limit=MAX_CANONICAL_CELL_REF_LENGTH,
        context=context,
    )
    if not _CANONICAL_CELL_REF_RE.match(cell_ref):
        raise LineageBuildError(
            "invalid_source_identity", f"{context} has invalid exact cell_ref {cell_ref!r}"
        )
    key = (sheet_id, tab_id, cell_ref)
    previous_node_id = seen_exact.get(key)
    if previous_node_id is not None:
        raise LineageBuildError(
            "duplicate_source_identity",
            f"output {output_name!r} node {node_id!r} source_ref {cell_ref!r} duplicates "
            f"node {previous_node_id!r}'s exact identity",
        )
    seen_exact[key] = node_id


def _check_acyclic(output_name: str, node_ids: set[str], edges: list[dict[str, object]]) -> None:
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in edges:
        adjacency[str(edge["source"])].append(str(edge["target"]))
    visiting: set[str] = set()
    visited: set[str] = set()

    def _visit(node_id: str) -> None:
        if node_id in visiting:
            raise LineageBuildError(
                "invalid_graph",
                f"output {output_name!r} contains a cycle through node {node_id!r}",
            )
        if node_id in visited:
            return
        visiting.add(node_id)
        for target in adjacency[node_id]:
            _visit(target)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in node_ids:
        _visit(node_id)


def _validated_output_parts(
    output: dict[str, object],
) -> tuple[str, list[object], list[object], dict[object, object], list[object]]:
    output_name = _require_bounded_text(
        output.get("output_name"),
        field="output_name",
        limit=MAX_OUTPUT_NAME_LENGTH,
        context="lineage output",
    )
    context = f"output {output_name!r}"
    if output.get("coverage") not in {"traced", "partial", "untraced"}:
        raise LineageBuildError("malformed", f"{context} has an invalid coverage value")
    for field in ("sheet_id", "tab_id"):
        value = output.get(field)
        if value is not None:
            _require_bounded_text(value, field=field, limit=MAX_REF_LENGTH, context=context)

    nodes_value = output.get("nodes")
    edges_value = output.get("edges")
    coordinates_value = output.get("coordinates")
    coordinate_ranges_value = output.get("coordinate_ranges", [])
    if not isinstance(nodes_value, list) or not nodes_value:
        raise LineageBuildError("malformed", f"{context} must contain at least one node")
    if (
        not isinstance(edges_value, list)
        or not isinstance(coordinates_value, dict)
        or not isinstance(coordinate_ranges_value, list)
    ):
        raise LineageBuildError(
            "malformed", f"{context} has malformed edges, coordinates, or coordinate_ranges"
        )
    if not coordinates_value and not coordinate_ranges_value:
        raise LineageBuildError("missing_coordinates", f"{context} has no coordinates registered")
    if len(nodes_value) > MAX_NODES_PER_OUTPUT:
        raise LineageBuildError(
            "limit_exceeded", f"{context} exceeds the {MAX_NODES_PER_OUTPUT}-node limit"
        )
    if len(edges_value) > MAX_EDGES_PER_OUTPUT:
        raise LineageBuildError(
            "limit_exceeded", f"{context} exceeds the {MAX_EDGES_PER_OUTPUT}-edge limit"
        )
    return output_name, nodes_value, edges_value, coordinates_value, coordinate_ranges_value


def _validate_node(
    node_value: object,
    *,
    output_name: str,
    node_ids: set[str],
    seen_exact: dict[tuple[str, str, str], str],
) -> dict[str, object]:
    context = f"output {output_name!r}"
    if not isinstance(node_value, dict):
        raise LineageBuildError("malformed", f"{context} contains a malformed node")
    node = node_value
    node_id = _require_bounded_text(
        node.get("id"), field="id", limit=MAX_ID_LENGTH, context=f"{context} node"
    )
    if node_id in node_ids:
        raise LineageBuildError("invalid_graph", f"{context} has duplicate node id {node_id!r}")
    node_ids.add(node_id)
    node_context = f"{context} node {node_id!r}"
    _require_bounded_text(
        node.get("label"), field="label", limit=MAX_LABEL_LENGTH, context=node_context
    )
    if node.get("kind") not in {"input", "logic", "output", "assumption", "unknown"}:
        raise LineageBuildError("malformed", f"{node_context} has invalid kind")
    value = node.get("value")
    if value is not None:
        _require_bounded_text(value, field="value", limit=MAX_VALUE_LENGTH, context=node_context)
    group = node.get("group")
    if group is not None and (not isinstance(group, str) or len(group) > MAX_GROUP_LENGTH):
        raise LineageBuildError(
            "limit_exceeded",
            f"{node_context} group exceeds the {MAX_GROUP_LENGTH}-character limit",
        )
    if "source_ref" in node:
        _validate_source_ref(
            node["source_ref"],
            output_name=output_name,
            node_id=node_id,
            seen_exact=seen_exact,
        )
    return node


def _validated_nodes(
    node_values: list[object], *, output_name: str
) -> tuple[list[dict[str, object]], set[str]]:
    nodes: list[dict[str, object]] = []
    node_ids: set[str] = set()
    seen_exact: dict[tuple[str, str, str], str] = {}
    for node_value in node_values:
        nodes.append(
            _validate_node(
                node_value,
                output_name=output_name,
                node_ids=node_ids,
                seen_exact=seen_exact,
            )
        )
    return nodes, node_ids


def _validate_edge(
    edge_value: object, *, output_name: str, node_ids: set[str]
) -> dict[str, object]:
    context = f"output {output_name!r}"
    if not isinstance(edge_value, dict):
        raise LineageBuildError("malformed", f"{context} contains a malformed edge")
    edge = edge_value
    edge_id = _require_bounded_text(
        edge.get("id"), field="id", limit=MAX_ID_LENGTH, context=f"{context} edge"
    )
    edge_context = f"{context} edge {edge_id!r}"
    source = _require_bounded_text(
        edge.get("source"), field="source", limit=MAX_ID_LENGTH, context=edge_context
    )
    target = _require_bounded_text(
        edge.get("target"), field="target", limit=MAX_ID_LENGTH, context=edge_context
    )
    if source not in node_ids or target not in node_ids:
        missing = source if source not in node_ids else target
        raise LineageBuildError(
            "invalid_graph", f"{edge_context} references unknown node {missing!r}"
        )
    return edge


def _validated_edges(
    edge_values: list[object], *, output_name: str, node_ids: set[str]
) -> list[dict[str, object]]:
    return [
        _validate_edge(edge, output_name=output_name, node_ids=node_ids) for edge in edge_values
    ]


_CoordinateEntry = tuple[str, tuple[int, int, int, int]]


def _validated_point_coordinate(
    cell_ref: object, node_id_value: object, *, context: str, node_ids: set[str]
) -> _CoordinateEntry:
    if (
        not isinstance(cell_ref, str)
        or len(cell_ref) > MAX_OUTPUT_CELL_REF_LENGTH
        or not _CELL_REF_RE.match(cell_ref)
    ):
        raise LineageBuildError(
            "invalid_coordinate", f"{context} coordinate {cell_ref!r} is not a valid cell reference"
        )
    node_id = _require_bounded_text(
        node_id_value,
        field="node id",
        limit=MAX_ID_LENGTH,
        context=f"{context} coordinate {cell_ref!r}",
    )
    if node_id not in node_ids:
        raise LineageBuildError(
            "invalid_graph",
            f"{context} coordinate {cell_ref!r} references unknown node {node_id!r}",
        )
    row, column = parse_cell_ref(cell_ref)
    return cell_ref, (row, row, column, column)


def _validated_coordinate_range(
    range_value: object, *, context: str, node_ids: set[str]
) -> _CoordinateEntry:
    if not isinstance(range_value, dict):
        raise LineageBuildError("malformed", f"{context} contains a malformed coordinate range")
    if set(range_value) != {"start", "end", "node_id"}:
        raise LineageBuildError(
            "malformed", f"{context} coordinate range has missing or unknown fields"
        )
    start = _require_bounded_text(
        range_value.get("start"),
        field="start",
        limit=MAX_OUTPUT_CELL_REF_LENGTH,
        context=f"{context} coordinate range",
    )
    end = _require_bounded_text(
        range_value.get("end"),
        field="end",
        limit=MAX_OUTPUT_CELL_REF_LENGTH,
        context=f"{context} coordinate range",
    )
    node_id = _require_bounded_text(
        range_value.get("node_id"),
        field="node_id",
        limit=MAX_ID_LENGTH,
        context=f"{context} coordinate range {start!r}:{end!r}",
    )
    if node_id not in node_ids:
        raise LineageBuildError(
            "invalid_graph",
            f"{context} coordinate range {start!r}:{end!r} references unknown node {node_id!r}",
        )
    try:
        bounds = coordinate_range_bounds(start, end)
    except ValueError as exc:
        raise LineageBuildError(
            "invalid_coordinate", f"{context} coordinate range {start!r}:{end!r} is invalid"
        ) from exc
    return f"{start}:{end}", bounds


def _reject_coordinate_overlaps(entries: list[_CoordinateEntry], *, context: str) -> None:
    ordered = sorted(entries, key=lambda entry: (entry[1], entry[0]))
    for index, (first_ref, first_bounds) in enumerate(ordered):
        for second_ref, second_bounds in ordered[index + 1 :]:
            if coordinate_ranges_overlap(first_bounds, second_bounds):
                raise LineageBuildError(
                    "ambiguous_coordinate",
                    f"{context} coordinate mappings {first_ref!r} and {second_ref!r} overlap",
                )


def _validate_coordinates(
    coordinates: dict[object, object],
    coordinate_ranges: list[object],
    *,
    output_name: str,
    node_ids: set[str],
) -> list[str]:
    context = f"output {output_name!r}"
    entries = [
        _validated_point_coordinate(cell_ref, node_id, context=context, node_ids=node_ids)
        for cell_ref, node_id in coordinates.items()
    ]
    entries.extend(
        _validated_coordinate_range(item, context=context, node_ids=node_ids)
        for item in coordinate_ranges
    )
    _reject_coordinate_overlaps(entries, context=context)
    return [ref for ref, _bounds in entries]


def _updated_run_totals(
    *,
    output_name: str,
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]],
    coordinate_refs: list[str],
    previous: tuple[int, int, int],
) -> tuple[int, int, int]:
    context = f"output {output_name!r}"
    total_nodes, total_edges, total_coordinates = previous
    new_total_nodes = total_nodes + len(nodes)
    new_total_edges = total_edges + len(edges)
    new_total_coordinates = total_coordinates + len(coordinate_refs)
    if new_total_nodes > MAX_INDEX_NODES:
        offending = nodes[MAX_INDEX_NODES - total_nodes]
        raise LineageBuildError(
            "limit_exceeded",
            f"{context} node {offending['id']!r} exceeds the run's {MAX_INDEX_NODES}-node limit",
        )
    if new_total_edges > MAX_INDEX_EDGES:
        offending = edges[MAX_INDEX_EDGES - total_edges]
        raise LineageBuildError(
            "limit_exceeded",
            f"{context} edge {offending['id']!r} exceeds the run's {MAX_INDEX_EDGES}-edge limit",
        )
    if new_total_coordinates > MAX_INDEX_COORDINATES:
        offending_ref = coordinate_refs[MAX_INDEX_COORDINATES - total_coordinates]
        raise LineageBuildError(
            "limit_exceeded",
            f"{context} coordinate {offending_ref!r} exceeds the run's "
            f"{MAX_INDEX_COORDINATES}-coordinate limit",
        )
    return new_total_nodes, new_total_edges, new_total_coordinates


def _validate_output_graph(
    output: dict[str, object], *, previous_totals: tuple[int, int, int]
) -> tuple[int, int, int]:
    output_name, node_values, edge_values, coordinates, coordinate_ranges = _validated_output_parts(
        output
    )
    nodes, node_ids = _validated_nodes(node_values, output_name=output_name)
    edges = _validated_edges(edge_values, output_name=output_name, node_ids=node_ids)
    coordinate_refs = _validate_coordinates(
        coordinates,
        coordinate_ranges,
        output_name=output_name,
        node_ids=node_ids,
    )
    _check_acyclic(output_name, node_ids, edges)
    return _updated_run_totals(
        output_name=output_name,
        nodes=nodes,
        edges=edges,
        coordinate_refs=coordinate_refs,
        previous=previous_totals,
    )


def _json_size(value: object) -> int:
    return len(json.dumps(value).encode("utf-8"))


def _validate_artifact_size(artifact: dict[str, object]) -> None:
    try:
        serialized_bytes = _json_size(artifact)
    except (TypeError, ValueError) as exc:
        raise LineageBuildError("malformed", "artifact contains a non-JSON value") from exc
    if serialized_bytes <= MAX_ARTIFACT_BYTES:
        return
    outputs_value = artifact.get("outputs")
    largest_output = "unknown"
    if isinstance(outputs_value, list) and outputs_value:
        largest = max(outputs_value, key=_json_size)
        if isinstance(largest, dict):
            largest_output = str(largest.get("output_name", "unknown"))
    raise LineageBuildError(
        "size_exceeded",
        f"artifact is {serialized_bytes:,} bytes, exceeds the {MAX_ARTIFACT_BYTES:,}-byte "
        f"limit; largest output is {largest_output!r}",
    )


def _validated_artifact_parts(artifact: dict[str, object]) -> list[object]:
    if artifact.get("schema_version") != 3:
        raise LineageBuildError(
            "malformed", "the current output-lineage helper emits schema_version=3"
        )
    run_value = artifact.get("run")
    outputs_value = artifact.get("outputs")
    if not isinstance(run_value, dict) or not isinstance(outputs_value, list):
        raise LineageBuildError("malformed", "artifact has malformed run or outputs fields")
    _require_bounded_text(
        run_value.get("run_id"), field="run_id", limit=MAX_RUN_ID_LENGTH, context="artifact run"
    )
    _require_bounded_text(
        run_value.get("model_name"),
        field="model_name",
        limit=MAX_MODEL_NAME_LENGTH,
        context="artifact run",
    )
    if not outputs_value:
        raise LineageBuildError("missing_outputs", "no outputs registered on this run")
    if len(outputs_value) > MAX_OUTPUTS:
        raise LineageBuildError("limit_exceeded", f"run exceeds the {MAX_OUTPUTS}-output limit")
    return outputs_value


def validate_lineage_artifact(artifact: dict[str, object]) -> None:
    """Enforce every author-visible server and index-ingestion invariant."""
    _validate_artifact_size(artifact)
    outputs_value = _validated_artifact_parts(artifact)
    totals = (0, 0, 0)
    seen_output_names: set[str] = set()
    for output_value in outputs_value:
        if not isinstance(output_value, dict):
            raise LineageBuildError("malformed", "artifact contains a malformed output")
        output_name = str(output_value.get("output_name", ""))
        if output_name in seen_output_names:
            raise LineageBuildError(
                "duplicate_output", f"output {output_name!r} appears more than once"
            )
        seen_output_names.add(output_name)
        totals = _validate_output_graph(output_value, previous_totals=totals)


"""Model-author helper API for explicit ``output_lineage.json`` traces (bt-hu12i.2).

This module is the ergonomic authoring surface a model author writes against
directly in their model code -- it builds the same artifact shape that
:mod:`services.mcp_server.run_output_lineage` validates. Authors declare input
values, assumptions, business-logic steps, and output coordinates; the
builder assigns stable node ids, wires dependency edges, and enforces the
size/shape limits up front so a mistake fails loudly at authoring time rather
than producing a malformed artifact that only fails much later, at run
validation.

Delivery note (self-containment): unlike ``run_output_lineage.py``, this
module deliberately does **not** import that module's pydantic models. Model
code runs inside the network-isolated ECS sandbox
(``services/sandbox/Dockerfile``), which has no access to the
``bridge_town_core`` server package -- only the project's own repo
(``/repo``) plus a handful of pre-installed libraries (pandas among them).
To be usable by a real model author, this module must be copyable, as-is,
into a model repo's ``lib/`` directory (the existing shared-helper-code
convention documented in ``services/mcp_server/scaffold.py``'s
``SCAFFOLD_RUN_PY``) and run there standalone. The scaffold renderer inlines
``output_lineage_contract.py`` ahead of this module, so ``OUTPUT_LINEAGE_LIMITS``
and its validator remain canonical without leaving sandbox authors with a
server-package import.
``tests/unit/test_output_lineage_helpers.py`` cross-validates every example
this module builds through
``run_output_lineage.validate_lineage_artifact`` to keep the two from
drifting apart (the "helper output matches the runner schema exactly" review
focus for bt-hu12i.2).

See ``docs/native-sheets-output-lineage-authoring.md`` for the model-author
guide and copy-pasteable finance examples (driver inputs, revenue build,
margin calculation, SUM, SUMPRODUCT-style weighted sums, XNPV/XIRR-style
calculations, and table-row outputs).

Canonical input-cell identity (bt-m5mnf.5): pass an :class:`InputSourceRef`
instead of a plain ``(kind, ref)`` tuple to ``source_ref=`` when your model's
own input-loading code already resolved a real ``sheet_id``/``tab_id`` (and
optionally ``cell_ref``) -- this lets Explain match the node back to a real
input cell by id (``identity_state="exact"``/``"partial"``) instead of by
display-label guessing. Omit the canonical fields entirely (or keep using
the plain tuple) when you don't have them; a bare ``ref`` string remains
fully valid and degrades to a best-effort, never-``exact`` match at explain
time (contract doc ``docs/native-sheets-staged-run-lineage-contract.md``
§8.2). This module mirrors that contract's ``TraceSourceRefV2`` shape by
literal value, not by import. The generated scaffold inlines the standalone
contract above this helper so these limits stay canonical in both environments.
"""


import inspect
import os
import pathlib
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

import pandas as pd

SCHEMA_VERSION = 3

# Epic bt-hu12i locked decision: "render at most five input groups,
# collapsing low-materiality inputs into Other."
MAX_INPUT_GROUPS = 5
OTHER_GROUP_LABEL = "Other"

REDACTED_VALUE = "[redacted]"

NodeKind = Literal["input", "logic", "output", "assumption", "unknown"]
CoverageState = Literal["traced", "partial", "untraced"]

_CELL_REF_RE = re.compile(CELL_REF_PATTERN)
_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Canonical sheet_id/tab_id are opaque platform-generated ids, never
# user-authored free text -- an allowlist charset rejects path-like
# (``/``, ``..``), control-character, and oversize values in one check,
# rather than truncating (silently truncating an id risks colliding with an
# unrelated real id, unlike truncating a display label).
_CANONICAL_ID_RE = re.compile(rf"^[A-Za-z0-9_-]{{1,{MAX_CANONICAL_ID_LENGTH}}}$")
_CANONICAL_CELL_REF_RE = re.compile(r"^[A-Z]{1,3}[1-9][0-9]*$")

_CREDENTIAL_VALUE_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"AKIA[0-9A-Z]{16}",
        r"sk-[A-Za-z0-9]{20,}",
        r"ghp_[A-Za-z0-9]{30,}",
        r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",  # JWT-shaped
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    )
)
_CREDENTIAL_LABEL_HINTS = (
    "password",
    "secret",
    "api_key",
    "apikey",
    "token",
    "credential",
    "private_key",
)


@dataclass(frozen=True)
class NodeRef:
    """A handle to a previously-added node, used as a precedent/edge source.

    ``value`` carries the raw (pre-string-coercion) value the author passed
    in -- used internally by :meth:`OutputTraceBuilder.sum_of` and
    :meth:`OutputTraceBuilder.weighted_sum` to auto-derive a computed value
    when the author does not supply one explicitly. Do not reuse a
    ``NodeRef`` returned by one output's builder as a precedent on a
    *different* output's builder -- node ids are only unique within a single
    output's graph.
    """

    id: str
    kind: NodeKind
    value: object = None


@dataclass(frozen=True)
class InputSourceRef:
    """Canonical, v2 form of an input node's ``source_ref`` (bt-m5mnf.5).

    Additive alternative to the plain ``(kind, ref)`` 2-tuple accepted
    everywhere ``source_ref=`` is: set ``sheet_id``/``tab_id`` (and
    optionally ``cell_ref``, for a single-cell match rather than a
    range/aggregate) when your model's own input-loading code already
    resolved them, so Explain can match this node back to a real
    ``NativeSheetDocument`` cell by id instead of by display-label guessing.
    ``ref`` is still required and stays the free-text display string either
    way -- never dropped, even when the canonical fields are also present.

    Only ``kind="input_sheet"`` may carry the canonical fields -- a data
    source or parameter reference has no sheet/tab/cell to identify.
    Supplying ``sheet_id``/``cell_ref`` without ``tab_id`` (or vice versa) is
    an authoring error (:class:`LineageBuildError`,
    ``category="invalid_source_identity"``): a canonical identity needs at
    least ``sheet_id``+``tab_id`` together (contract doc §8.2's ``partial``
    state), never one alone.
    """

    kind: Literal["input_sheet", "data_source", "parameter"]
    ref: str
    sheet_id: str | None = None
    tab_id: str | None = None
    cell_ref: str | None = None


def _build_source_ref(
    output_name: str,
    source_ref: tuple[Literal["input_sheet", "data_source", "parameter"], str] | InputSourceRef,
) -> dict[str, object]:
    """Return the ``source_ref`` dict for a node, v1 or v2 shaped.

    v1 (plain tuple, or an :class:`InputSourceRef` with no canonical fields
    set): ``{"kind": ..., "ref": ...}``, byte-identical to today's shape.
    v2 (:class:`InputSourceRef` with ``sheet_id``/``tab_id`` set): additive
    ``sheet_id``/``tab_id``/``cell_ref``/``identity_state`` fields, matching
    ``TraceSourceRefV2`` (``docs/native-sheets-staged-run-lineage-contract.md``
    §8.1) exactly -- ``identity_state="exact"`` only when ``cell_ref`` is
    also present, else ``"partial"``, mirroring that contract's locked rule
    that a helper may only ever claim ``exact``/``partial``, never
    ``inferred``/``ambiguous`` (those are backend-only, explain-time states).
    """
    if isinstance(source_ref, InputSourceRef):
        kind, ref = source_ref.kind, source_ref.ref
        sheet_id, tab_id, cell_ref = source_ref.sheet_id, source_ref.tab_id, source_ref.cell_ref
    else:
        kind, ref = source_ref
        sheet_id = tab_id = cell_ref = None

    built: dict[str, object] = {"kind": kind, "ref": ref[:MAX_REF_LENGTH]}
    if sheet_id is None and tab_id is None and cell_ref is None:
        return built

    if kind != "input_sheet":
        raise LineageBuildError(
            "invalid_source_identity",
            f"output {output_name!r}: canonical sheet_id/tab_id/cell_ref may only be set "
            f"when kind='input_sheet', got kind={kind!r}",
        )
    if sheet_id is None or tab_id is None:
        raise LineageBuildError(
            "invalid_source_identity",
            f"output {output_name!r}: a canonical source identity requires at least "
            "sheet_id and tab_id together (contract doc §8.2 'partial') -- got only one",
        )
    for field_name, field_value in (("sheet_id", sheet_id), ("tab_id", tab_id)):
        if not _CANONICAL_ID_RE.match(field_value):
            raise LineageBuildError(
                "invalid_source_identity",
                f"output {output_name!r}: {field_name} is not a safe canonical id "
                "(must be 1-128 chars of letters, digits, '_', or '-')",
            )
    if cell_ref is not None and (
        len(cell_ref) > MAX_CANONICAL_CELL_REF_LENGTH or not _CANONICAL_CELL_REF_RE.match(cell_ref)
    ):
        raise LineageBuildError(
            "invalid_source_identity",
            f"output {output_name!r}: {cell_ref!r} is not a valid canonical cell reference",
        )

    built["sheet_id"] = sheet_id
    built["tab_id"] = tab_id
    if cell_ref is not None:
        built["cell_ref"] = cell_ref
    built["identity_state"] = "exact" if cell_ref is not None else "partial"
    return built


def _looks_like_credential(label: str, value: str) -> bool:
    if any(pattern.search(value) for pattern in _CREDENTIAL_VALUE_PATTERNS):
        return True
    lowered_label = label.lower()
    return len(value) >= 6 and any(hint in lowered_label for hint in _CREDENTIAL_LABEL_HINTS)


def _format_scalar(value: object) -> str:
    if isinstance(value, float):
        if value != value:  # noqa: PLR0124 -- NaN check without importing math -- owner: platform-team expires: 2027-07-24
            return "NaN"
        return f"{value:.6g}"
    return str(value)


def _coerce_value(label: str, value: object) -> str | None:
    if value is None:
        return None
    text = value if isinstance(value, str) else _format_scalar(value)
    if _looks_like_credential(label, text):
        return REDACTED_VALUE
    if len(text) > MAX_VALUE_LENGTH:
        text = text[: MAX_VALUE_LENGTH - 1] + "…"
    return text


def _try_numeric(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return None


def _try_sum(precedents: Sequence[NodeRef]) -> float | None:
    if not precedents:
        return None
    values = [_try_numeric(p.value) for p in precedents]
    if any(v is None for v in values):
        return None
    return sum(v for v in values if v is not None)


def _try_weighted_sum(terms: Sequence[tuple[NodeRef, float]]) -> float | None:
    if not terms:
        return None
    total = 0.0
    for node, weight in terms:
        numeric = _try_numeric(node.value)
        if numeric is None:
            return None
        total += numeric * weight
    return total


def _slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.strip().lower()).strip("-")
    return slug[:80] if slug else "node"


def _unique_id(base: str, existing_ids: set[str]) -> str:
    if base not in existing_ids:
        return base
    n = 2
    while f"{base}-{n}" in existing_ids:
        n += 1
    return f"{base}-{n}"


def _caller_code_ref(skip: int) -> tuple[str, int | None]:
    """Return ``(file, line)`` of the model-author frame ``skip`` levels up.

    ``skip`` counts frames above this function's own: 1 is this function's
    direct caller, 2 is that caller's caller, etc. Builder methods that call
    this directly use ``skip=2`` (skip this function, skip the builder
    method); convenience methods that delegate to another builder method
    (e.g. :meth:`OutputTraceBuilder.sum_of` calling
    :meth:`OutputTraceBuilder.logic_step`) add one more level of skip.
    """
    frame = inspect.stack()[skip]
    return frame.filename, frame.lineno


def _parse_cell_ref(ref: str) -> tuple[int, int]:
    """Return 0-indexed ``(col, row)`` for an ``A1``-style cell reference."""
    if len(ref) > MAX_OUTPUT_CELL_REF_LENGTH or not _CELL_REF_RE.match(ref):
        raise LineageBuildError("invalid_coordinate", f"{ref!r} is not a valid cell reference")
    match = re.match(r"^([A-Z]+)([1-9][0-9]*)$", ref)
    assert match is not None  # guarded by _CELL_REF_RE.match above
    col_letters, row_digits = match.groups()
    col_idx = 0
    for ch in col_letters:
        col_idx = col_idx * 26 + (ord(ch) - ord("A") + 1)
    return col_idx - 1, int(row_digits) - 1


def _col_letters(col_idx0: int) -> str:
    n = col_idx0 + 1
    letters = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


def _cell_ref(col_idx0: int, row_idx0: int) -> str:
    return f"{_col_letters(col_idx0)}{row_idx0 + 1}"


def _collapse_input_groups(
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]],
    materiality: dict[str, float],
    protected_ids: set[str],
    max_groups: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Collapse low-materiality ``input``/``assumption`` groups into "Other".

    Groups nodes by their ``group`` field (each ungrouped node is its own
    singleton group, keyed by node id, so it is never accidentally merged
    with an unrelated ungrouped node). If more than ``max_groups`` distinct
    groups exist, keeps the ``max_groups - 1`` highest-total-materiality
    groups and merges the rest into a single new "Other" node, redirecting
    their edges. Nodes referenced directly by an output coordinate
    (``protected_ids``) are never collapsed -- collapsing one would leave a
    coordinate pointing at a node id that no longer exists.
    """
    grouped: dict[str, list[dict[str, object]]] = {}
    for node in nodes:
        if node["kind"] not in ("input", "assumption") or node["id"] in protected_ids:
            continue
        key = str(node.get("group")) if node.get("group") is not None else f"__solo__{node['id']}"
        grouped.setdefault(key, []).append(node)

    if len(grouped) <= max_groups:
        return nodes, edges

    order = list(grouped.keys())

    def _group_materiality(key: str) -> float:
        return sum(materiality.get(str(n["id"]), 1.0) for n in grouped[key])

    ranked = sorted(order, key=lambda k: (-_group_materiality(k), order.index(k)))
    collapsed_keys = set(ranked[max_groups - 1 :])
    collapsed_ids = {str(n["id"]) for key in collapsed_keys for n in grouped[key]}
    if not collapsed_ids:
        return nodes, edges

    other_id = _unique_id("input-other", {str(n["id"]) for n in nodes})
    other_node: dict[str, object] = {
        "id": other_id,
        "kind": "input",
        "label": OTHER_GROUP_LABEL,
        "group": OTHER_GROUP_LABEL,
    }
    new_nodes = [n for n in nodes if str(n["id"]) not in collapsed_ids]
    new_nodes.append(other_node)

    new_edges: list[dict[str, object]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for edge in edges:
        source = other_id if str(edge["source"]) in collapsed_ids else str(edge["source"])
        target = other_id if str(edge["target"]) in collapsed_ids else str(edge["target"])
        if source == target or (source, target) in seen_pairs:
            continue
        seen_pairs.add((source, target))
        new_edge = dict(edge)
        new_edge["id"] = f"e{len(new_edges) + 1}"
        new_edge["source"] = source
        new_edge["target"] = target
        new_edges.append(new_edge)

    return new_nodes, new_edges


class OutputTraceBuilder:
    """Builds one output's trace graph (nodes, edges, and cell coordinates).

    Returned by :meth:`OutputLineageBuilder.output` -- do not construct
    directly.
    """

    def __init__(
        self,
        output_name: str,
        coverage: CoverageState,
        max_input_groups: int,
    ) -> None:
        self._output_name = output_name[:MAX_OUTPUT_NAME_LENGTH]
        self._coverage: CoverageState = coverage
        self._max_input_groups = max_input_groups
        self._nodes: list[dict[str, object]] = []
        self._edges: list[dict[str, object]] = []
        self._node_ids: set[str] = set()
        self._exact_source_ids: dict[tuple[str, str, str], str] = {}
        self._materiality: dict[str, float] = {}
        self._coordinates: dict[str, str] = {}
        self._coordinate_ranges: list[dict[str, str]] = []
        self._coordinate_bounds: list[tuple[str, tuple[int, int, int, int]]] = []

    def _make_node_id(self, kind: str, label: str, node_id: str | None) -> str:
        candidate = node_id if node_id is not None else f"{kind}-{_slugify(label)}"
        candidate = candidate[:MAX_ID_LENGTH]
        if candidate not in self._node_ids:
            return candidate
        if node_id is not None:
            raise LineageBuildError(
                "duplicate_node_id",
                f"node id {candidate!r} already used in output {self._output_name!r}",
            )
        n = 2
        while f"{candidate}-{n}" in self._node_ids:
            n += 1
        return f"{candidate}-{n}"[:MAX_ID_LENGTH]

    def _register_exact_source_identity(
        self, source_ref: dict[str, object], *, node_id: str
    ) -> None:
        if source_ref.get("identity_state") != "exact":
            return
        key = (
            str(source_ref["sheet_id"]),
            str(source_ref["tab_id"]),
            str(source_ref["cell_ref"]),
        )
        previous_node_id = self._exact_source_ids.get(key)
        if previous_node_id is not None:
            raise LineageBuildError(
                "duplicate_source_identity",
                f"output {self._output_name!r} node {node_id!r} source_ref {key[2]!r} "
                f"duplicates node {previous_node_id!r}'s exact identity",
            )
        self._exact_source_ids[key] = node_id

    def _add_node(
        self,
        kind: NodeKind,
        label: str,
        *,
        value: object = None,
        code_ref: tuple[str, int | None] | None = None,
        source_ref: tuple[Literal["input_sheet", "data_source", "parameter"], str]
        | InputSourceRef
        | None = None,
        group: str | None = None,
        materiality: float = 1.0,
        node_id: str | None = None,
    ) -> NodeRef:
        if len(self._nodes) >= MAX_NODES_PER_OUTPUT:
            raise LineageBuildError(
                "limit_exceeded",
                f"output {self._output_name!r} would exceed the {MAX_NODES_PER_OUTPUT}-node limit",
            )
        bounded_label = label[:MAX_LABEL_LENGTH]
        final_id = self._make_node_id(kind, bounded_label, node_id)

        node: dict[str, object] = {"id": final_id, "kind": kind, "label": bounded_label}
        coerced_value = _coerce_value(bounded_label, value)
        if coerced_value is not None:
            node["value"] = coerced_value
        if code_ref is not None:
            file, line = code_ref
            ref: dict[str, object] = {"file": file[:MAX_REF_LENGTH]}
            if line is not None:
                ref["line"] = line
            node["code_ref"] = ref
        if source_ref is not None:
            built_source_ref = _build_source_ref(self._output_name, source_ref)
            self._register_exact_source_identity(built_source_ref, node_id=final_id)
            node["source_ref"] = built_source_ref
        if group is not None:
            node["group"] = group[:MAX_GROUP_LENGTH]
        self._node_ids.add(final_id)
        self._nodes.append(node)
        if kind in ("input", "assumption"):
            self._materiality[final_id] = materiality
        return NodeRef(id=final_id, kind=kind, value=value)

    def _add_edge(self, source: NodeRef, target: NodeRef, *, label: str | None = None) -> None:
        if source.id not in self._node_ids:
            raise LineageBuildError(
                "unknown_precedent",
                f"node id {source.id!r} is not part of output {self._output_name!r}'s graph",
            )
        if target.id not in self._node_ids:
            raise LineageBuildError(
                "unknown_precedent",
                f"node id {target.id!r} is not part of output {self._output_name!r}'s graph",
            )
        if len(self._edges) >= MAX_EDGES_PER_OUTPUT:
            raise LineageBuildError(
                "limit_exceeded",
                f"output {self._output_name!r} would exceed the {MAX_EDGES_PER_OUTPUT}-edge limit",
            )
        edge: dict[str, object] = {
            "id": f"e{len(self._edges) + 1}",
            "source": source.id,
            "target": target.id,
        }
        if label is not None:
            edge["label"] = label[:MAX_LABEL_LENGTH]
        self._edges.append(edge)

    def input_value(
        self,
        label: str,
        value: object = None,
        *,
        source_ref: tuple[Literal["input_sheet", "data_source", "parameter"], str]
        | InputSourceRef
        | None = None,
        group: str | None = None,
        materiality: float = 1.0,
        node_id: str | None = None,
    ) -> NodeRef:
        """Declare a traced input value (a concrete driver the model reads).

        Pass an :class:`InputSourceRef` instead of a plain ``(kind, ref)``
        tuple for ``source_ref`` to additionally attach a canonical
        ``sheet_id``/``tab_id``/``cell_ref`` identity -- see this module's
        docstring and :class:`InputSourceRef` for when and why.
        """
        return self._add_node(
            "input",
            label,
            value=value,
            source_ref=source_ref,
            group=group,
            materiality=materiality,
            node_id=node_id,
        )

    def assumption(
        self,
        label: str,
        value: object = None,
        *,
        group: str | None = None,
        materiality: float = 1.0,
        node_id: str | None = None,
    ) -> NodeRef:
        """Declare a hardcoded/inferred assumption (no concrete input-sheet source)."""
        return self._add_node(
            "assumption", label, value=value, group=group, materiality=materiality, node_id=node_id
        )

    def logic_step(
        self,
        label: str,
        *precedents: NodeRef,
        value: object = None,
        node_id: str | None = None,
        auto_code_ref: bool = True,
        _skip: int = 0,
    ) -> NodeRef:
        """Declare an intermediate business-logic step derived from *precedents*."""
        code_ref = _caller_code_ref(2 + _skip) if auto_code_ref else None
        node = self._add_node("logic", label, value=value, code_ref=code_ref, node_id=node_id)
        for precedent in precedents:
            self._add_edge(precedent, node)
        return node

    def output_node(
        self,
        cell_ref: str,
        label: str,
        *precedents: NodeRef,
        value: object = None,
        node_id: str | None = None,
        auto_code_ref: bool = True,
    ) -> NodeRef:
        """Declare the output node for *cell_ref* and register its coordinate."""
        code_ref = _caller_code_ref(2) if auto_code_ref else None
        node = self._add_node("output", label, value=value, code_ref=code_ref, node_id=node_id)
        for precedent in precedents:
            self._add_edge(precedent, node)
        self.coordinate(cell_ref, node)
        return node

    def coordinate(self, cell_ref: str, node: NodeRef) -> None:
        """Map an output-sheet cell reference to *node*'s id directly.

        Use this when a cell's derivation root already has a node (e.g. to
        map several cells to the same computed node) without creating a new
        output node.
        """
        if len(cell_ref) > MAX_OUTPUT_CELL_REF_LENGTH or not _CELL_REF_RE.match(cell_ref):
            raise LineageBuildError(
                "invalid_coordinate", f"{cell_ref!r} is not a valid cell reference"
            )
        if node.id not in self._node_ids:
            raise LineageBuildError(
                "unknown_precedent",
                f"node id {node.id!r} is not part of output {self._output_name!r}'s graph",
            )
        column_index, row_index = _parse_cell_ref(cell_ref)
        row = row_index + 1
        column = column_index + 1
        self._register_coordinate_bounds(cell_ref, (row, row, column, column))
        self._coordinates[cell_ref] = node.id

    def _register_coordinate_bounds(
        self, coordinate_ref: str, bounds: tuple[int, int, int, int]
    ) -> None:
        for existing_ref, existing_bounds in self._coordinate_bounds:
            if coordinate_ranges_overlap(existing_bounds, bounds):
                raise LineageBuildError(
                    "ambiguous_coordinate",
                    f"output {self._output_name!r} coordinate mappings {existing_ref!r} and "
                    f"{coordinate_ref!r} overlap",
                )
        self._coordinate_bounds.append((coordinate_ref, bounds))

    def coordinate_range(self, start: str, end: str, node: NodeRef) -> None:
        """Map an inclusive rectangular output range to one node.

        The v3 artifact and reverse index retain this as one entry. ``start``
        must be the top-left corner and ``end`` the bottom-right corner; the
        range is never expanded into individual cell mappings.
        """
        if node.id not in self._node_ids:
            raise LineageBuildError(
                "unknown_precedent",
                f"node id {node.id!r} is not part of output {self._output_name!r}'s graph",
            )
        try:
            bounds = coordinate_range_bounds(start, end)
        except ValueError as exc:
            raise LineageBuildError(
                "invalid_coordinate", f"{start!r}:{end!r} is not a valid coordinate range"
            ) from exc
        coordinate_ref = f"{start}:{end}"
        self._register_coordinate_bounds(coordinate_ref, bounds)
        self._coordinate_ranges.append({"start": start, "end": end, "node_id": node.id})

    def sum_of(
        self, label: str, *precedents: NodeRef, value: object = None, node_id: str | None = None
    ) -> NodeRef:
        """Convenience for a SUM-style logic step; auto-computes *value* when omitted."""
        resolved_value = value if value is not None else _try_sum(precedents)
        return self.logic_step(label, *precedents, value=resolved_value, node_id=node_id, _skip=1)

    def weighted_sum(
        self,
        label: str,
        terms: Sequence[tuple[NodeRef, float]],
        *,
        value: object = None,
        node_id: str | None = None,
    ) -> NodeRef:
        """Convenience for a SUMPRODUCT-style weighted logic step.

        *terms* is a sequence of ``(precedent, weight)`` pairs. Auto-computes
        *value* as the weighted sum when omitted and every precedent carries
        a numeric value.
        """
        resolved_value = value if value is not None else _try_weighted_sum(terms)
        precedents = tuple(term[0] for term in terms)
        return self.logic_step(label, *precedents, value=resolved_value, node_id=node_id, _skip=1)

    def table_rows(
        self,
        df: pd.DataFrame,
        *,
        anchor: str,
        row_label: Callable[[object, pd.Series], str] | str | None = None,
        row_value: Callable[[object, pd.Series], object] | str | None = None,
        row_precedents: Callable[[object, pd.Series], Sequence[NodeRef]] | None = None,
        group: str | None = None,
        header_row: bool = False,
    ) -> list[NodeRef]:
        """Trace a whole rendered DataFrame table without per-cell annotation.

        Creates one ``output`` node per row of *df* and maps every column of
        that row (starting at *anchor*, e.g. ``"A2"``) to the row's node --
        so a model author tracing a table output does not need to call
        :meth:`output_node` once per cell. *row_label*/*row_value* may be a
        column name (looked up per row) or a callable ``(index, row) ->
        value``; *row_precedents* is a callable returning the precedent
        nodes for a row (e.g. the driver inputs that produced it).
        """
        col_start, row_start = _parse_cell_ref(anchor)
        n_cols = len(df.columns)
        row_offset = 1 if header_row else 0
        nodes: list[NodeRef] = []
        for i, (index, row) in enumerate(df.iterrows()):
            if callable(row_label):
                label = row_label(index, row)
            elif isinstance(row_label, str):
                label = str(row[row_label])
            else:
                label = str(index)

            if callable(row_value):
                value = row_value(index, row)
            elif isinstance(row_value, str):
                value = row[row_value]
            else:
                value = None

            precedents = row_precedents(index, row) if row_precedents is not None else ()

            node = self._add_node(
                "output",
                label,
                value=value,
                code_ref=_caller_code_ref(2),
                group=group,
            )
            for precedent in precedents:
                self._add_edge(precedent, node)
            row_idx0 = row_start + row_offset + i
            if n_cols:
                self.coordinate_range(
                    _cell_ref(col_start, row_idx0),
                    _cell_ref(col_start + n_cols - 1, row_idx0),
                    node,
                )
            nodes.append(node)
        return nodes

    def to_dict(self) -> dict[str, object]:
        """Finalize this output's trace, applying input-group collapsing."""
        if not self._coordinates and not self._coordinate_ranges:
            raise LineageBuildError(
                "missing_coordinates", f"output {self._output_name!r} has no coordinates registered"
            )
        protected_ids = set(self._coordinates.values()) | {
            coordinate_range["node_id"] for coordinate_range in self._coordinate_ranges
        }
        nodes, edges = _collapse_input_groups(
            self._nodes, self._edges, self._materiality, protected_ids, self._max_input_groups
        )
        return {
            "output_name": self._output_name,
            "coverage": self._coverage,
            "coordinates": dict(self._coordinates),
            "coordinate_ranges": list(self._coordinate_ranges),
            "nodes": nodes,
            "edges": edges,
            "truncated": False,
        }


class OutputLineageBuilder:
    """Builds a full ``output_lineage.json`` artifact for one model run.

    Example::

        builder = OutputLineageBuilder(run_id=RUN_ID, model_name="revenue_model")
        out = builder.output("output.json")
        price = out.input_value("Unit price", 42.0, group="Pricing")
        units = out.input_value("Units sold", 1_000, group="Volume")
        revenue = out.logic_step("Revenue = price * units", price, units, value=42_000)
        out.output_node("B2", "Total revenue", revenue, value=42_000)
        builder.write()  # writes /outputs/output_lineage.json
    """

    def __init__(self, run_id: str, model_name: str) -> None:
        self._run_id = run_id[:MAX_RUN_ID_LENGTH]
        self._model_name = model_name[:MAX_MODEL_NAME_LENGTH]
        self._outputs: list[OutputTraceBuilder] = []
        self._output_names: set[str] = set()

    @classmethod
    def from_environment(cls, *, model_name: str) -> OutputLineageBuilder:
        """Build using the platform's run id from ``$BT_RUN_ID`` (bt-ay4we).

        The sandbox sets ``BT_RUN_ID`` to the run id ``run_output_lineage``
        validates ``output_lineage.json`` against, so model authors normally
        want this constructor instead of copying the env lookup themselves.
        Raises :class:`LineageBuildError` if the variable is unset -- e.g. the
        model was invoked outside the sandbox -- rather than silently writing
        an artifact that will fail run validation with an opaque mismatch.
        """
        run_id = os.environ.get("BT_RUN_ID", "")
        if not run_id:
            raise LineageBuildError(
                "missing_run_id",
                "$BT_RUN_ID is not set -- OutputLineageBuilder.from_environment() "
                "must run inside the model sandbox.",
            )
        return cls(run_id=run_id, model_name=model_name)

    def output(
        self,
        output_name: str,
        *,
        coverage: CoverageState = "traced",
        max_input_groups: int = MAX_INPUT_GROUPS,
    ) -> OutputTraceBuilder:
        """Start tracing a new model output; *output_name* matches the output filename."""
        bounded_output_name = output_name[:MAX_OUTPUT_NAME_LENGTH]
        if bounded_output_name in self._output_names:
            raise LineageBuildError(
                "duplicate_output", f"output {bounded_output_name!r} already registered"
            )
        if len(self._outputs) >= MAX_OUTPUTS:
            raise LineageBuildError(
                "limit_exceeded", f"run would exceed the {MAX_OUTPUTS}-output limit"
            )
        self._output_names.add(bounded_output_name)
        builder = OutputTraceBuilder(bounded_output_name, coverage, max_input_groups)
        self._outputs.append(builder)
        return builder

    def _build_unvalidated(self) -> dict[str, object]:
        if not self._outputs:
            raise LineageBuildError("missing_outputs", "no outputs registered on this run")
        return {
            "schema_version": SCHEMA_VERSION,
            "run": {"run_id": self._run_id, "model_name": self._model_name},
            "outputs": [output.to_dict() for output in self._outputs],
            "truncated": False,
        }

    def validate(self) -> dict[str, object]:
        """Validate and return the full artifact before it leaves author code.

        This is the standalone equivalent of the server's structural and
        index-ingestion validation. It intentionally cannot perform the
        server's database-backed authorization of canonical sheet ids.
        """
        artifact = self._build_unvalidated()
        validate_lineage_artifact(artifact)
        return artifact

    def build(self) -> dict[str, object]:
        """Validate and return the full ``OutputLineageArtifact``-shaped dict."""
        return self.validate()

    def write(self, path: str | os.PathLike[str] | None = None) -> pathlib.Path:
        """Write the artifact to *path* (default: ``$SANDBOX_OUTPUT_PATH/output_lineage.json``)."""
        artifact = self.validate()
        target = (
            pathlib.Path(path)
            if path is not None
            else pathlib.Path(os.environ.get("SANDBOX_OUTPUT_PATH", "/outputs"))
            / "output_lineage.json"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(artifact, indent=2))
        return target
