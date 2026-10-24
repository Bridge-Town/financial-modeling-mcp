"""Compatibility imports for models still using ``lib.native_sheet_reader``.

This file is shipped only in the successor helper release. Earlier published
``native_sheet_reader.py`` files remain unchanged and keep reading historical
``.btsheet.json`` documents.
"""

from __future__ import annotations

from .bsheet_reader import (
    DEFAULT_MAX_READ_SET_ENTRIES,
    DEFAULT_READ_SET_FILENAME,
    MAX_READ_SET_ENTRIES,
    MAX_SHEET_BYTES,
    READ_SET_SCHEMA_VERSION,
    BSheetBlankCellError,
    BSheetCellMissingError,
    BSheetDocumentError,
    BSheetFormulaError,
    BSheetFormulaValueUnavailableError,
    BSheetNotFoundError,
    BSheetReader,
    BSheetReadError,
    BSheetTabNotFoundError,
    CellRead,
    CellReadStatus,
    CellScalar,
    NativeSheetBlankCellError,
    NativeSheetCellMissingError,
    NativeSheetDocumentError,
    NativeSheetFormulaError,
    NativeSheetFormulaValueUnavailableError,
    NativeSheetNotFoundError,
    NativeSheetReadError,
    NativeSheetTabNotFoundError,
)

NativeSheetReader = BSheetReader

__all__ = [
    "BSheetBlankCellError",
    "BSheetCellMissingError",
    "BSheetDocumentError",
    "BSheetFormulaError",
    "BSheetFormulaValueUnavailableError",
    "BSheetNotFoundError",
    "BSheetReadError",
    "BSheetReader",
    "BSheetTabNotFoundError",
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
