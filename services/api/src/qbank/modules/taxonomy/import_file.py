"""Reading an uploaded syllabus file (.xlsx or .csv) into a plain table (M3 design note §4.4, C-03).

The file is untrusted. The checks look at the content and not at the file name: a spreadsheet is a
ZIP archive, a CSV is UTF-8 text, anything else is refused. Limits keep one upload from using the
server up: the file size, the number of rows, and (against a "decompression bomb", a tiny archive
that expands to gigabytes) the total size the archive claims to expand to.

Formulas are never evaluated. A spreadsheet that contains any is refused with a plain message,
because what the admin sees in the cell and what the import would read could differ.
"""

import csv
import io
import unicodedata
import zipfile
from dataclasses import dataclass

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from qbank.core.errors import ValidationFailed

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 20_000
MAX_COLUMNS = 40
MAX_CELL_CHARS = 2_000
# What the archive may expand to in total. A 5 MB spreadsheet of 20,000 rows is far below this.
MAX_UNPACKED_BYTES = 50 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 200

_ZIP_MAGIC = b"PK\x03\x04"
_OLD_EXCEL_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")


class ImportFileInvalid(ValidationFailed):
    code = "IMPORT_INVALID"


@dataclass(frozen=True)
class TableRow:
    number: int  # the row's number in the file, as the admin sees it (the header is row 1)
    cells: dict[str, str]


@dataclass(frozen=True)
class Table:
    columns: list[str]
    rows: list[TableRow]


def read_table(data: bytes) -> Table:
    """The first sheet of a spreadsheet, or a CSV file, as a header and rows of text."""
    if len(data) > MAX_FILE_BYTES:
        raise ImportFileInvalid(f"The file is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.")
    if not data:
        raise ImportFileInvalid("The file is empty.")
    if data.startswith(_ZIP_MAGIC):
        return _from_lines(_spreadsheet_lines(data))
    if data.startswith(_OLD_EXCEL_MAGIC):
        raise ImportFileInvalid("Old .xls files are not supported. Save it as .xlsx and try again.")
    return _from_lines(_csv_lines(data))


def _text(value: object) -> str:
    """One cell as plain text: whole numbers without ".0", spaces trimmed."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return unicodedata.normalize("NFC", str(value)).strip()


def _csv_lines(data: bytes) -> list[list[str]]:
    if b"\x00" in data:
        raise ImportFileInvalid("This is not a spreadsheet or a CSV text file.")
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportFileInvalid(
            "The CSV file must be saved as UTF-8 (in Excel: Save as > CSV UTF-8)."
        ) from None
    lines: list[list[str]] = []
    try:
        for record in csv.reader(io.StringIO(content, newline="")):
            lines.append([_text(cell) for cell in record])
            if len(lines) > MAX_ROWS + 1:
                raise ImportFileInvalid(f"The file has more than {MAX_ROWS:,} rows.")
    except csv.Error:
        raise ImportFileInvalid("The CSV file could not be read.") from None
    return lines


def _check_archive(data: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
    except zipfile.BadZipFile:
        raise ImportFileInvalid("This is not a valid .xlsx file.") from None
    if len(members) > MAX_ARCHIVE_MEMBERS or sum(m.file_size for m in members) > MAX_UNPACKED_BYTES:
        raise ImportFileInvalid("This file is too large once unpacked.")


def _spreadsheet_lines(data: bytes) -> list[list[str]]:
    _check_archive(data)
    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=False)
    except InvalidFileException, zipfile.BadZipFile, KeyError, ValueError, OSError:
        raise ImportFileInvalid("This is not a valid .xlsx file.") from None
    try:
        sheet = workbook.worksheets[0] if workbook.worksheets else None
        if sheet is None:
            raise ImportFileInvalid("The workbook has no sheet.")
        lines: list[list[str]] = []
        # Blank rows count too: a file that declares a million empty rows is refused, not walked.
        for row in sheet.iter_rows(max_col=MAX_COLUMNS):
            if len(lines) > MAX_ROWS + 1:
                raise ImportFileInvalid(f"The file has more than {MAX_ROWS:,} rows.")
            for cell in row:
                if cell.data_type == "f":
                    raise ImportFileInvalid(
                        "The file has cells with formulas, which are not accepted. Copy the cells"
                        " and paste them as values, then try again."
                    )
            lines.append([_text(cell.value) for cell in row])
        return lines
    finally:
        workbook.close()


def _from_lines(lines: list[list[str]]) -> Table:
    """Header names in lower case, blank rows dropped, over-long cells refused."""
    if not lines:
        raise ImportFileInvalid("The file has no rows.")
    columns = [name.lower() for name in lines[0]]
    while columns and not columns[-1]:
        columns.pop()
    if not columns:
        raise ImportFileInvalid("The first row must name the columns.")
    if len(columns) > MAX_COLUMNS:
        raise ImportFileInvalid(f"The file has more than {MAX_COLUMNS} columns.")
    named = [name for name in columns if name]
    if len(set(named)) != len(named):
        raise ImportFileInvalid("Two columns have the same name.")
    rows: list[TableRow] = []
    for number, line in enumerate(lines[1:], start=2):
        if not any(line):
            continue
        if any(len(cell) > MAX_CELL_CHARS for cell in line):
            raise ImportFileInvalid(
                f"Row {number} has a cell longer than {MAX_CELL_CHARS} characters."
            )
        padded = line + [""] * (len(columns) - len(line))
        rows.append(
            TableRow(
                number=number, cells={c: v for c, v in zip(columns, padded, strict=False) if c}
            )
        )
    if len(rows) > MAX_ROWS:
        raise ImportFileInvalid(f"The file has more than {MAX_ROWS:,} rows.")
    return Table(columns=named, rows=rows)
