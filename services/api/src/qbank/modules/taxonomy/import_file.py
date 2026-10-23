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
from typing import Any

from defusedxml.ElementTree import iterparse
from openpyxl import load_workbook

from qbank.core.errors import ValidationFailed

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 20_000
MAX_COLUMNS = 40
MAX_CELL_CHARS = 2_000
# What the archive may expand to in total. A syllabus of 20,000 rows is a few MB unpacked. The
# spreadsheet reader holds a multiple of this in memory while it works, so it is kept modest.
MAX_UNPACKED_BYTES = 20 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 200
MAX_CELLS_PER_ROW = 16_384  # the columns of a sheet (A to XFD); a row cannot hold more

_ZIP_MAGIC = b"PK\x03\x04"
_OLD_EXCEL_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")


_FORMULAS = (
    "The file has cells with formulas, which are not accepted. Copy the cells and paste them as"
    " values, then try again."
)


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
        for record in csv.reader(io.StringIO(content, newline=""), strict=True):
            lines.append([_text(cell) for cell in record])
            if len(lines) > MAX_ROWS + 1:
                raise ImportFileInvalid(f"The file has more than {MAX_ROWS:,} rows.")
    except csv.Error:
        raise ImportFileInvalid(
            "The CSV file has a quote that is not closed or not placed correctly."
        ) from None
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
    except Exception:
        # Whatever the library raises, the upload is simply unreadable.
        raise ImportFileInvalid("This is not a valid .xlsx file.") from None
    try:
        sheet = workbook.worksheets[0] if workbook.worksheets else None
        if sheet is None:
            raise ImportFileInvalid("The workbook has no sheet.")
        return _sheet_lines(sheet)
    except ImportFileInvalid:
        raise
    except Exception:
        # The sheet is parsed lazily, so damage in it shows up only here.
        raise ImportFileInvalid("This is not a valid .xlsx file.") from None
    finally:
        workbook.close()


def _column_number(reference: str) -> int:
    """The column of a cell reference such as "XFD12" (A is 1)."""
    number = 0
    for char in reference:
        if not char.isalpha():
            break
        number = number * 26 + ord(char.upper()) - 64
        if number > 1_000_000:  # not a real column; no need to count further
            break
    return number


def _check_far_cells(sheet: Any) -> None:
    """Refuse a populated cell past the column limit, without building the cells in between.

    The reader below stops at the limit, so it would never see such a cell. A spreadsheet can also
    hold empty, styled cells at the far right of every row; walking those (16,384 per row) would
    keep the server busy for minutes, which is why the cells are looked at here one by one as they
    are in the file, and only those with content are counted.
    """
    with sheet._get_source() as source:  # the sheet's XML, as stored in the archive
        row = None
        cells_in_row = 0
        for event, element in iterparse(source, events=("start", "end")):
            tag = element.tag.rsplit("}", 1)[-1]
            if event == "start":
                if tag == "row":
                    row, cells_in_row = element, 0
            elif tag == "c":
                cells_in_row += 1
                if cells_in_row > MAX_CELLS_PER_ROW:
                    raise ImportFileInvalid(
                        "A row of the file has more cells than a sheet can hold."
                    )
                parts = {child.tag.rsplit("}", 1)[-1]: child for child in element}
                if "f" in parts:
                    raise ImportFileInvalid(_FORMULAS)
                value, inline = parts.get("v"), parts.get("is")
                filled = inline is not None or (value is not None and bool(value.text))
                if filled and _column_number(element.get("r", "")) > MAX_COLUMNS:
                    raise ImportFileInvalid(f"The file has more than {MAX_COLUMNS} columns.")
                # Drop the cell at once: a row can hold hundreds of thousands of them, and
                # keeping them until the row ends would use memory in proportion.
                element.clear()
                if row is not None:
                    row.remove(element)


def _sheet_lines(sheet: Any) -> list[list[str]]:
    # The sheet's declared size is ignored: a file can declare it too small and hide rows or cells.
    sheet.reset_dimensions()
    _check_far_cells(sheet)
    lines: list[list[str]] = []
    # Blank rows count too: a file that declares a million empty rows is refused, not walked.
    for row in sheet.iter_rows(max_col=MAX_COLUMNS):
        if len(lines) > MAX_ROWS + 1:
            raise ImportFileInvalid(f"The file has more than {MAX_ROWS:,} rows.")
        for cell in row:
            if cell.data_type == "f":
                raise ImportFileInvalid(_FORMULAS)
        lines.append([_text(cell.value) for cell in row])
    return lines


def _from_lines(lines: list[list[str]]) -> Table:
    """Header names in lower case, blank rows dropped, over-long cells refused."""
    if not lines:
        raise ImportFileInvalid("The file has no rows.")
    if any(len(cell) > MAX_CELL_CHARS for cell in lines[0]):
        raise ImportFileInvalid(f"A column name is longer than {MAX_CELL_CHARS} characters.")
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
        if any(line[len(columns) :]):
            raise ImportFileInvalid(
                f"Row {number} has more values than the header has columns. A value that contains"
                " a comma must be put in quotes."
            )
        padded = (line + [""] * len(columns))[: len(columns)]
        if any(value for name, value in zip(columns, padded, strict=True) if not name):
            raise ImportFileInvalid(
                f"Row {number} has a value in a column that has no name in the header."
            )
        rows.append(
            TableRow(number=number, cells={c: v for c, v in zip(columns, padded, strict=True) if c})
        )
    if len(rows) > MAX_ROWS:
        raise ImportFileInvalid(f"The file has more than {MAX_ROWS:,} rows.")
    return Table(columns=named, rows=rows)
