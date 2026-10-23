"""Reading an uploaded syllabus file (.xlsx or .csv) into a plain table (M3 design note §4.4, C-03).

The file is untrusted. The checks look at the content and not at the file name: a spreadsheet is a
ZIP archive, a CSV is UTF-8 text, anything else is refused. Limits keep one upload from using the
server up: the file size, the number of rows, and (against a "decompression bomb", a tiny archive
that expands to gigabytes) the total size the archive claims to expand to.

A spreadsheet is read by the small streaming reader below, not by a spreadsheet library: the
sheet is walked once, element by element, in constant memory, with every limit checked as it goes.
(A library builds the whole sheet in memory and reads parts the file points to, which a crafted
file can use to exhaust the server.)

Formulas are never evaluated. A spreadsheet that contains any is refused with a plain message,
because what the admin sees in the cell and what the import would read could differ.
"""

import csv
import io
import posixpath
import unicodedata
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from typing import IO
from xml.etree.ElementTree import Element

from defusedxml.ElementTree import iterparse

from qbank.core.errors import ValidationFailed

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 20_000
MAX_COLUMNS = 40
MAX_CELL_CHARS = 2_000
# What the archive may expand to in total. A syllabus of 20,000 rows is a few MB unpacked.
MAX_UNPACKED_BYTES = 20 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 200
MAX_PARTS_PER_ITEM = 2_000  # elements inside one cell or one shared text (runs of formatting)
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


def _local(tag: str) -> str:
    """An XML tag without its namespace."""
    return tag.rsplit("}", 1)[-1]


def _number(text: str | None) -> int:
    return int(text) if text is not None and text.isdigit() else 0


def _column_number(reference: str) -> int:
    """The column of a cell reference such as "XFD12" (A is 1); 0 if it has none."""
    number = 0
    for char in reference:
        if not char.isalpha():
            break
        number = number * 26 + ord(char.upper()) - 64
        if number > 1_000_000:  # not a real column; no need to count further
            break
    return number


def _stream(source: IO[bytes], keep_inside: str = "") -> Iterator[Element]:
    """Each element of an XML part, as it ends. After the caller has seen it, it is released, so a
    part with millions of elements is read in constant memory. Elements inside a ``keep_inside``
    element stay until that one ends, because its end is where they are read; there can be only so
    many of them, so one cell cannot hold the server's memory either."""
    stack: list[Element] = []
    inside = False
    kept = 0
    for event, element in iterparse(source, events=("start", "end")):
        if event == "start":
            stack.append(element)
            if not inside and _local(element.tag) == keep_inside:
                inside, kept = True, 0
            elif inside:
                kept += 1
                if kept > MAX_PARTS_PER_ITEM:
                    raise ImportFileInvalid("A cell or text of the file is too complex.")
            continue
        stack.pop()
        yield element
        if inside and _local(element.tag) == keep_inside:
            inside = False
        if not inside:
            element.clear()
            if stack:
                stack[-1].remove(element)


def _rich_text(item: Element) -> str:
    """The text of a shared or inline string: plain and formatted runs, not phonetic hints."""
    parts: list[str] = []
    for child in item:
        if _local(child.tag) == "t":
            parts.append(child.text or "")
        elif _local(child.tag) == "r":
            parts.extend((run.text or "") for run in child if _local(run.tag) == "t")
    return "".join(parts)


def _first_sheet_part(archive: zipfile.ZipFile) -> str:
    """Where the first sheet of the workbook is stored, found through the workbook's relationships
    (the sheet can be stored under any name)."""
    relationship_id = None
    with archive.open("xl/workbook.xml") as source:
        for element in _stream(source):
            if _local(element.tag) == "sheet":
                relationship_id = next(
                    (v for k, v in element.attrib.items() if k.endswith("}id")), None
                )
                break
    if relationship_id is None:
        raise ImportFileInvalid("The workbook has no sheet.")
    target = kind = None
    with archive.open("xl/_rels/workbook.xml.rels") as source:
        for element in _stream(source):
            if _local(element.tag) == "Relationship" and element.get("Id") == relationship_id:
                target, kind = element.get("Target"), element.get("Type", "")
                break
    if target is None or not (kind or "").endswith("/worksheet"):
        raise ImportFileInvalid("The first sheet of the workbook is not a worksheet.")
    part = posixpath.normpath(target.lstrip("/") if target.startswith("/") else f"xl/{target}")
    archive.getinfo(part)  # raises KeyError if the archive does not hold it
    return part


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        archive.getinfo("xl/sharedStrings.xml")
    except KeyError:
        return []
    strings: list[str] = []
    with archive.open("xl/sharedStrings.xml") as source:
        for element in _stream(source, keep_inside="si"):
            if _local(element.tag) == "si":
                if len(strings) >= MAX_ROWS * MAX_COLUMNS:
                    raise ImportFileInvalid("The file has too many different texts.")
                strings.append(_text(_rich_text(element)))
    return strings


def _cell_text(cell: Element, strings: list[str]) -> str:
    parts = {_local(child.tag): child for child in cell}
    if "f" in parts:
        raise ImportFileInvalid(_FORMULAS)
    kind = cell.get("t", "n")
    if kind == "inlineStr":
        inline = parts.get("is")
        return _text(_rich_text(inline)) if inline is not None else ""
    value = parts.get("v")
    raw = value.text if value is not None and value.text else ""
    if not raw:
        return ""
    if kind == "s":
        index = int(raw)
        if not 0 <= index < len(strings):  # a negative number would count from the end
            raise ImportFileInvalid("This is not a valid .xlsx file.")
        return strings[index]
    if kind == "b":
        return "TRUE" if raw == "1" else "FALSE"
    if kind == "n":
        try:
            number = float(raw)
        except ValueError:
            return _text(raw)
        return str(int(number)) if number.is_integer() and abs(number) < 1e15 else _text(raw)
    return _text(raw)


def _sheet_lines(source: IO[bytes], strings: list[str]) -> list[list[str]]:
    """The rows of a sheet as lists of text, read as a stream with every limit enforced as it goes.

    The size the sheet declares for itself is not used (it can lie), and the cells of a row are
    taken as they are stored, so empty styled cells at the far right of every row cost nothing.
    """
    lines: list[list[str]] = []
    last_row = cells_in_row = 0
    cells: dict[int, str] = {}
    for element in _stream(source, keep_inside="c"):
        tag = _local(element.tag)
        if tag == "c":
            cells_in_row += 1
            if cells_in_row > MAX_CELLS_PER_ROW:
                raise ImportFileInvalid("A row of the file has more cells than a sheet can hold.")
            text = _cell_text(element, strings)
            if text:
                column = _column_number(element.get("r", ""))
                if column < 1:
                    raise ImportFileInvalid("This is not a valid .xlsx file.")
                if column > MAX_COLUMNS:
                    raise ImportFileInvalid(f"The file has more than {MAX_COLUMNS} columns.")
                cells[column] = text
        elif tag == "row":
            number = _number(element.get("r")) or last_row + 1
            if number > MAX_ROWS + 1:  # the header is a row too
                raise ImportFileInvalid(f"The file has more than {MAX_ROWS:,} rows.")
            if number <= last_row:
                raise ImportFileInvalid("The rows of the file are not in order.")
            lines.extend([] for _ in range(number - last_row - 1))  # blank rows in between
            lines.append([cells.get(column, "") for column in range(1, max(cells, default=0) + 1)])
            last_row, cells_in_row, cells = number, 0, {}
    return lines


def _spreadsheet_lines(data: bytes) -> list[list[str]]:
    _check_archive(data)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            strings = _shared_strings(archive)
            with archive.open(_first_sheet_part(archive)) as source:
                return _sheet_lines(source, strings)
    except ImportFileInvalid:
        raise
    except Exception:
        # A damaged archive, XML that is not well formed, a missing part, a bad reference.
        raise ImportFileInvalid("This is not a valid .xlsx file.") from None


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
