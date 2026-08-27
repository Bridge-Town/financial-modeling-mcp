"""Sandbox-safe Native Sheet reader for model authors.

This module is versioned for distribution in official model templates and is
copied into model repositories as ``lib/native_sheet_reader.py``. Keep it
standard-library only: it runs inside the restricted model sandbox and must not
import Bridge Town service code.

The reader deliberately preserves JSON presence semantics.  A missing cell, a
present blank cell, a formula without a cached value, a formula error, and a
numeric zero are five different states; none is silently coerced to another.
Successful reads can be emitted to ``/outputs/native_sheet_read_set.json`` as a
bounded, value-free set of canonical ``sheet_id``/``tab_id``/``cell_ref``
identities for later lineage reconciliation.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, NoReturn

CellScalar = bool | int | float | str
CellReadStatus = Literal["literal_value", "literal_blank", "formula_value"]

READ_SET_SCHEMA_VERSION = 1
DEFAULT_READ_SET_FILENAME = "native_sheet_read_set.json"
DEFAULT_MAX_READ_SET_ENTRIES = 1_000
MAX_READ_SET_ENTRIES = 1_000
MAX_SHEET_BYTES = 1_048_576

_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_A1_REF = re.compile(r"^([A-Z]{1,3})([1-9][0-9]{0,6})$")
_FORMULA_ERROR_LABELS = frozenset({"#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#NUM!", "#CYCLE!"})


class NativeSheetReadError(ValueError):
    """Base class for actionable, identity-bearing Native Sheet read errors."""

    def __init__(
        self,
        message: str,
        *,
        sheet_id: str,
        tab_id: str | None = None,
        cell_ref: str | None = None,
    ) -> None:
        super().__init__(message)
        self.sheet_id = sheet_id
        self.tab_id = tab_id
        self.cell_ref = cell_ref


class NativeSheetNotFoundError(NativeSheetReadError):
    """The requested sheet document does not exist at either supported path."""


class NativeSheetDocumentError(NativeSheetReadError):
    """The committed sheet document cannot be read safely."""


class NativeSheetTabNotFoundError(NativeSheetReadError):
    """The requested tab id or name does not exist in the sheet."""


class NativeSheetCellMissingError(NativeSheetReadError):
    """No cell object exists at the requested coordinate."""


class NativeSheetBlankCellError(NativeSheetReadError):
    """A scalar-only read encountered a present literal blank."""


class NativeSheetFormulaValueUnavailableError(NativeSheetReadError):
    """A formula exists but has no usable cached value."""


class NativeSheetFormulaError(NativeSheetReadError):
    """A formula's cached result is a spreadsheet error."""


@dataclass(frozen=True, slots=True)
class CellRead:
    """One successful read with its canonical identity and preserved status."""

    sheet_id: str
    tab_id: str
    cell_ref: str
    status: CellReadStatus
    value: CellScalar | None

    def require_value(self) -> CellScalar:
        """Return the scalar value, rejecting a literal blank without coercion."""
        if self.status == "literal_blank":
            raise NativeSheetBlankCellError(
                f"Native Sheet {self.sheet_id}/{self.tab_id}!{self.cell_ref} is a "
                "present literal blank; provide an explicit model default instead of "
                "coercing null to zero.",
                sheet_id=self.sheet_id,
                tab_id=self.tab_id,
                cell_ref=self.cell_ref,
            )
        # The status invariant guarantees that successful non-blank reads have
        # a scalar. Keep the explicit check so malformed future states fail closed.
        if self.value is None:
            raise NativeSheetDocumentError(
                f"Native Sheet {self.sheet_id}/{self.tab_id}!{self.cell_ref} has an "
                "invalid successful-read state with no value.",
                sheet_id=self.sheet_id,
                tab_id=self.tab_id,
                cell_ref=self.cell_ref,
            )
        return self.value


@dataclass(frozen=True, slots=True)
class _CellLocation:
    """Canonical identity plus parsed indexes for one requested cell."""

    sheet_id: str
    tab_id: str
    cell_ref: str
    row: int
    column: int


def _raise_document_error(
    message: str, *, sheet_id: str, tab_id: str | None = None, cell_ref: str | None = None
) -> NoReturn:
    raise NativeSheetDocumentError(
        message,
        sheet_id=sheet_id,
        tab_id=tab_id,
        cell_ref=cell_ref,
    )


def _canonical_a1(cell_ref: str) -> tuple[str, int, int]:
    canonical = cell_ref.strip().upper()
    match = _A1_REF.fullmatch(canonical)
    if match is None:
        raise ValueError(
            f"cell_ref must be one canonical A1 coordinate (for example 'B2'); got {cell_ref!r}."
        )
    letters, row_text = match.groups()
    column = 0
    for char in letters:
        column = column * 26 + ord(char) - ord("A") + 1
    return canonical, int(row_text), column


def _validated_scalar(
    value: object,
    *,
    location: _CellLocation,
    value_kind: Literal["cached formula", "literal"],
) -> CellScalar:
    """Return a finite JSON scalar or fail closed with canonical identity."""
    if not isinstance(value, bool | int | float | str):
        _raise_document_error(
            f"Native Sheet {location.sheet_id}/{location.tab_id}!{location.cell_ref} "
            f"has a non-scalar {value_kind} value.",
            sheet_id=location.sheet_id,
            tab_id=location.tab_id,
            cell_ref=location.cell_ref,
        )
    if isinstance(value, float) and not math.isfinite(value):
        _raise_document_error(
            f"Native Sheet {location.sheet_id}/{location.tab_id}!{location.cell_ref} "
            f"has a non-finite {value_kind} value.",
            sheet_id=location.sheet_id,
            tab_id=location.tab_id,
            cell_ref=location.cell_ref,
        )
    return value


class NativeSheetReader:
    """Read committed Native Sheet cells without collapsing distinct null states.

    ``repo_root`` defaults to ``SANDBOX_REPO_PATH`` (or ``/repo``) and
    ``output_root`` defaults to ``SANDBOX_OUTPUT_PATH`` (or ``/outputs``).
    The canonical ``sheets/`` location wins over the legacy
    ``.bridgetown/sheets/`` location when both exist.

    Use the reader as a context manager to emit telemetry after a successful
    block, or call :meth:`emit_read_set` explicitly.
    """

    def __init__(
        self,
        repo_root: str | Path | None = None,
        *,
        output_root: str | Path | None = None,
        max_read_set_entries: int = DEFAULT_MAX_READ_SET_ENTRIES,
    ) -> None:
        if not 1 <= max_read_set_entries <= MAX_READ_SET_ENTRIES:
            raise ValueError(
                "max_read_set_entries must be between 1 and "
                f"{MAX_READ_SET_ENTRIES}; got {max_read_set_entries}."
            )
        self.repo_root = Path(
            repo_root if repo_root is not None else os.environ.get("SANDBOX_REPO_PATH", "/repo")
        )
        self.output_root = Path(
            output_root
            if output_root is not None
            else os.environ.get("SANDBOX_OUTPUT_PATH", "/outputs")
        )
        self.max_read_set_entries = max_read_set_entries
        self._documents: dict[str, dict[str, Any]] = {}
        self._read_entries: dict[tuple[str, str, str], CellReadStatus] = {}
        self._read_count = 0
        self._omitted_count = 0

    def __enter__(self) -> NativeSheetReader:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc_type is None:
            self.emit_read_set()

    def _document_path(self, sheet_id: str) -> Path:
        if _SAFE_ID.fullmatch(sheet_id) is None:
            raise ValueError(
                "sheet_id must contain only ASCII letters, digits, underscores, and "
                f"hyphens (1-128 characters); got {sheet_id!r}."
            )
        candidates = (
            self.repo_root / "sheets" / f"{sheet_id}.btsheet.json",
            self.repo_root / ".bridgetown" / "sheets" / f"{sheet_id}.btsheet.json",
        )
        resolved_root = self.repo_root.resolve()
        for candidate in candidates:
            if candidate.is_file():
                try:
                    candidate.resolve(strict=True).relative_to(resolved_root)
                except (OSError, ValueError) as exc:
                    raise NativeSheetDocumentError(
                        f"Native Sheet {sheet_id!r} resolves outside the model repository; "
                        "replace the symlink with a committed sheet document.",
                        sheet_id=sheet_id,
                    ) from exc
                return candidate
        raise NativeSheetNotFoundError(
            f"Native Sheet {sheet_id!r} was not found under sheets/ or the legacy "
            ".bridgetown/sheets/ directory.",
            sheet_id=sheet_id,
        )

    def _load_document(self, sheet_id: str) -> dict[str, Any]:
        cached = self._documents.get(sheet_id)
        if cached is not None:
            return cached
        path = self._document_path(sheet_id)
        try:
            size_bytes = path.stat().st_size
            if size_bytes > MAX_SHEET_BYTES:
                raise NativeSheetDocumentError(
                    f"Native Sheet {sheet_id!r} is {size_bytes} bytes, exceeding the "
                    f"supported {MAX_SHEET_BYTES}-byte document limit.",
                    sheet_id=sheet_id,
                )
            raw = json.loads(path.read_text(encoding="utf-8"))
        except NativeSheetDocumentError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise NativeSheetDocumentError(
                f"Native Sheet {sheet_id!r} is unreadable or invalid JSON: {exc}.",
                sheet_id=sheet_id,
            ) from exc
        if not isinstance(raw, dict):
            _raise_document_error(
                f"Native Sheet {sheet_id!r} must contain a JSON object.", sheet_id=sheet_id
            )
        if raw.get("schema_version") != READ_SET_SCHEMA_VERSION:
            _raise_document_error(
                f"Native Sheet {sheet_id!r} has unsupported schema_version "
                f"{raw.get('schema_version')!r}; expected {READ_SET_SCHEMA_VERSION}.",
                sheet_id=sheet_id,
            )
        if raw.get("sheet_id") != sheet_id:
            _raise_document_error(
                f"Native Sheet path identity {sheet_id!r} does not match document "
                f"sheet_id {raw.get('sheet_id')!r}.",
                sheet_id=sheet_id,
            )
        tabs = raw.get("tabs")
        if not isinstance(tabs, list):
            _raise_document_error(
                f"Native Sheet {sheet_id!r} has an invalid tabs collection.", sheet_id=sheet_id
            )
        self._documents[sheet_id] = raw
        return raw

    def _select_tab(self, document: dict[str, Any], sheet_id: str, tab: str) -> dict[str, Any]:
        tabs = document["tabs"]
        id_matches: list[dict[str, Any]] = []
        name_matches: list[dict[str, Any]] = []
        for candidate in tabs:
            if not isinstance(candidate, dict):
                _raise_document_error(
                    f"Native Sheet {sheet_id!r} contains a non-object tab.", sheet_id=sheet_id
                )
            tab_id = candidate.get("tab_id")
            if not isinstance(tab_id, str) or _SAFE_ID.fullmatch(tab_id) is None:
                _raise_document_error(
                    f"Native Sheet {sheet_id!r} contains an invalid tab_id.",
                    sheet_id=sheet_id,
                )
            if tab_id == tab:
                id_matches.append(candidate)
            if candidate.get("name") == tab:
                name_matches.append(candidate)
        matches = id_matches if id_matches else name_matches
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            _raise_document_error(
                f"Native Sheet {sheet_id!r} has ambiguous duplicate tab identity {tab!r}.",
                sheet_id=sheet_id,
                tab_id=tab,
            )
        raise NativeSheetTabNotFoundError(
            f"Native Sheet {sheet_id!r} has no tab with id or exact name {tab!r}.",
            sheet_id=sheet_id,
            tab_id=tab,
        )

    @staticmethod
    def _cell_from_tab(tab: dict[str, Any], *, location: _CellLocation) -> dict[str, Any]:
        encoding = tab.get("cell_encoding", "sparse")
        cell: object
        if encoding == "sparse":
            cells = tab.get("cells", {})
            if not isinstance(cells, dict):
                _raise_document_error(
                    f"Native Sheet {location.sheet_id}/{location.tab_id} has an invalid "
                    "sparse cells map.",
                    sheet_id=location.sheet_id,
                    tab_id=location.tab_id,
                )
            cell = cells.get(location.cell_ref)
        elif encoding == "rows":
            rows = tab.get("rows", [])
            if not isinstance(rows, list):
                _raise_document_error(
                    f"Native Sheet {location.sheet_id}/{location.tab_id} has an invalid "
                    "rows collection.",
                    sheet_id=location.sheet_id,
                    tab_id=location.tab_id,
                )
            if location.row > len(rows):
                cell = None
            else:
                row_values = rows[location.row - 1]
                if not isinstance(row_values, list):
                    _raise_document_error(
                        f"Native Sheet {location.sheet_id}/{location.tab_id} row "
                        f"{location.row} is not an array.",
                        sheet_id=location.sheet_id,
                        tab_id=location.tab_id,
                    )
                cell = (
                    row_values[location.column - 1] if location.column <= len(row_values) else None
                )
        else:
            _raise_document_error(
                f"Native Sheet {location.sheet_id}/{location.tab_id} has unsupported "
                f"cell_encoding {encoding!r}.",
                sheet_id=location.sheet_id,
                tab_id=location.tab_id,
            )
        if cell is None:
            raise NativeSheetCellMissingError(
                f"Native Sheet {location.sheet_id}/{location.tab_id}!{location.cell_ref} "
                "is missing; add the cell or provide an explicit model default.",
                sheet_id=location.sheet_id,
                tab_id=location.tab_id,
                cell_ref=location.cell_ref,
            )
        if not isinstance(cell, dict):
            _raise_document_error(
                f"Native Sheet {location.sheet_id}/{location.tab_id}!{location.cell_ref} "
                "is not a cell object.",
                sheet_id=location.sheet_id,
                tab_id=location.tab_id,
                cell_ref=location.cell_ref,
            )
        return cell

    @staticmethod
    def _resolve_cell(
        cell: dict[str, Any], *, location: _CellLocation
    ) -> tuple[CellReadStatus, CellScalar | None]:
        formula = cell.get("formula")
        explicit_error = cell.get("error")
        if explicit_error is not None:
            raise NativeSheetFormulaError(
                f"Native Sheet {location.sheet_id}/{location.tab_id}!{location.cell_ref} "
                f"has formula error {explicit_error!r}; fix the formula and recalculate "
                "the sheet before running the model.",
                sheet_id=location.sheet_id,
                tab_id=location.tab_id,
                cell_ref=location.cell_ref,
            )

        if formula is not None:
            if not isinstance(formula, str):
                _raise_document_error(
                    f"Native Sheet {location.sheet_id}/{location.tab_id}!{location.cell_ref} "
                    "has a non-string formula.",
                    sheet_id=location.sheet_id,
                    tab_id=location.tab_id,
                    cell_ref=location.cell_ref,
                )
            if "value" not in cell or cell["value"] is None:
                raise NativeSheetFormulaValueUnavailableError(
                    f"Native Sheet {location.sheet_id}/{location.tab_id}!{location.cell_ref} "
                    "contains a formula but no cached value; recalculate the sheet before "
                    "running the model. Null is not numeric zero.",
                    sheet_id=location.sheet_id,
                    tab_id=location.tab_id,
                    cell_ref=location.cell_ref,
                )
            value = cell["value"]
            if isinstance(value, str) and value in _FORMULA_ERROR_LABELS:
                raise NativeSheetFormulaError(
                    f"Native Sheet {location.sheet_id}/{location.tab_id}!{location.cell_ref} "
                    f"has formula error {value}; fix the formula and recalculate the sheet "
                    "before running the model.",
                    sheet_id=location.sheet_id,
                    tab_id=location.tab_id,
                    cell_ref=location.cell_ref,
                )
            return "formula_value", _validated_scalar(
                value,
                location=location,
                value_kind="cached formula",
            )

        value = cell.get("value")
        if value is None:
            return "literal_blank", None
        return "literal_value", _validated_scalar(
            value,
            location=location,
            value_kind="literal",
        )

    def _record(self, read: CellRead) -> None:
        self._read_count += 1
        key = (read.sheet_id, read.tab_id, read.cell_ref)
        if key in self._read_entries:
            return
        if len(self._read_entries) >= self.max_read_set_entries:
            self._omitted_count += 1
            return
        self._read_entries[key] = read.status

    def read_cell(self, sheet_id: str, tab: str, cell_ref: str) -> CellRead:
        """Read one cell and return its canonical identity, status, and value.

        ``tab`` accepts either the canonical ``tab_id`` or the exact display
        name. Telemetry always records the canonical ``tab_id``.
        """
        canonical_ref, row, column = _canonical_a1(cell_ref)
        document = self._load_document(sheet_id)
        selected_tab = self._select_tab(document, sheet_id, tab)
        tab_id = selected_tab["tab_id"]
        location = _CellLocation(
            sheet_id=sheet_id,
            tab_id=tab_id,
            cell_ref=canonical_ref,
            row=row,
            column=column,
        )
        cell = self._cell_from_tab(selected_tab, location=location)
        status, value = self._resolve_cell(cell, location=location)
        read = CellRead(sheet_id, tab_id, canonical_ref, status, value)
        self._record(read)
        return read

    def read_value(self, sheet_id: str, tab: str, cell_ref: str) -> CellScalar:
        """Read one required scalar, rejecting missing, blank, or unsafe formulas."""
        return self.read_cell(sheet_id, tab, cell_ref).require_value()

    # Short convenience alias for model code.
    read = read_value

    def read_set_telemetry(self) -> dict[str, Any]:
        """Return bounded identity/status telemetry with no cell contents."""
        entries = [
            {
                "sheet_id": sheet_id,
                "tab_id": tab_id,
                "cell_ref": cell_ref,
                "status": status,
            }
            for (sheet_id, tab_id, cell_ref), status in self._read_entries.items()
        ]
        truncated = self._omitted_count > 0
        return {
            "schema_version": READ_SET_SCHEMA_VERSION,
            "instrumentation": "native_sheet_reader",
            "status": "truncated" if truncated else "complete",
            "read_count": self._read_count,
            "recorded_count": len(entries),
            "omitted_count": self._omitted_count,
            "truncated": truncated,
            "entries": entries,
        }

    def emit_read_set(self, path: str | Path | None = None) -> Path:
        """Write bounded read-set telemetry and return the artifact path."""
        destination = (
            Path(path) if path is not None else self.output_root / DEFAULT_READ_SET_FILENAME
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.read_set_telemetry(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return destination

    write_read_set = emit_read_set


__all__ = [
    "CellRead",
    "CellReadStatus",
    "CellScalar",
    "DEFAULT_MAX_READ_SET_ENTRIES",
    "DEFAULT_READ_SET_FILENAME",
    "MAX_READ_SET_ENTRIES",
    "MAX_SHEET_BYTES",
    "NativeSheetBlankCellError",
    "NativeSheetCellMissingError",
    "NativeSheetDocumentError",
    "NativeSheetFormulaError",
    "NativeSheetFormulaValueUnavailableError",
    "NativeSheetNotFoundError",
    "NativeSheetReadError",
    "NativeSheetReader",
    "NativeSheetTabNotFoundError",
    "READ_SET_SCHEMA_VERSION",
]
