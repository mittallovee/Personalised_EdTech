"""M3 PR 2c-1: reading an uploaded syllabus file safely (C-03, T25). Synthetic files only."""

import io
import zipfile

import pytest
from openpyxl import Workbook

from qbank.modules.taxonomy import import_file
from qbank.modules.taxonomy.import_file import ImportFileInvalid, read_table


def xlsx(*rows: list[object], extra_sheet: bool = False) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    for row in rows:
        sheet.append(row)
    if extra_sheet:
        workbook.create_sheet("Other").append(["ignored"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def refused(data: bytes) -> str:
    with pytest.raises(ImportFileInvalid) as caught:
        read_table(data)
    assert caught.value.code == "IMPORT_INVALID"
    assert caught.value.status_code == 422
    return str(caught.value)


def test_a_spreadsheet_is_read_into_columns_and_rows() -> None:
    table = read_table(
        xlsx(
            ["Kind", "Path", "Sort"],
            ["CLASS", "Class 11", 1],
            ["SUBJECT", "Class 11 > Physics", 2.0],
        )
    )
    assert table.columns == ["kind", "path", "sort"]
    assert [(r.number, r.cells) for r in table.rows] == [
        (2, {"kind": "CLASS", "path": "Class 11", "sort": "1"}),
        (3, {"kind": "SUBJECT", "path": "Class 11 > Physics", "sort": "2"}),
    ]


def test_only_the_first_sheet_is_read() -> None:
    table = read_table(xlsx(["kind"], ["CLASS"], extra_sheet=True))
    assert [r.cells for r in table.rows] == [{"kind": "CLASS"}]


def test_a_csv_file_is_read_the_same_way_including_a_byte_order_mark() -> None:
    data = "﻿Kind,Path,label_hi\r\nCLASS,Class 11,कक्षा 11\r\n\r\nSUBJECT,Class 11 > Physics,\r\n"
    table = read_table(data.encode())
    assert table.columns == ["kind", "path", "label_hi"]
    # The blank line is skipped, but the row after it keeps the number the admin sees in the file.
    assert [(r.number, r.cells["path"], r.cells["label_hi"]) for r in table.rows] == [
        (2, "Class 11", "कक्षा 11"),
        (4, "Class 11 > Physics", ""),
    ]


def test_cells_are_trimmed_and_short_rows_are_filled_with_blanks() -> None:
    table = read_table(b"kind,path,sort\n  CLASS  ,Class 11\n")
    assert table.rows[0].cells == {"kind": "CLASS", "path": "Class 11", "sort": ""}


def test_a_spreadsheet_with_a_formula_is_refused() -> None:
    message = refused(xlsx(["kind", "path"], ["CLASS", '=CONCATENATE("Class", " 11")']))
    assert "formulas" in message


def test_the_file_is_judged_by_its_content_not_its_name() -> None:
    assert "UTF-8" in refused("kind,path\nCLASS,Cl\xe4ss".encode("latin-1"))
    assert "not a spreadsheet" in refused(b"\x89PNG\r\n\x1a\n\x00\x00\x00")
    assert "valid .xlsx" in refused(b"PK\x03\x04 this is not really an archive")
    assert ".xlsx" in refused(bytes.fromhex("D0CF11E0A1B11AE1") + b"\x00" * 100)  # old Excel
    refused(b"")


def test_a_zip_that_is_not_a_spreadsheet_is_refused() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("readme.txt", "hello")
    assert "valid .xlsx" in refused(buffer.getvalue())


def test_an_archive_that_expands_enormously_is_refused_without_unpacking_it() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", b"0" * (import_file.MAX_UNPACKED_BYTES + 1))
    assert len(buffer.getvalue()) < import_file.MAX_FILE_BYTES  # small to send, huge to unpack
    assert "too large once unpacked" in refused(buffer.getvalue())


def test_an_archive_with_very_many_parts_is_refused() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for number in range(import_file.MAX_ARCHIVE_MEMBERS + 1):
            archive.writestr(f"part{number}.xml", "")
    assert "too large once unpacked" in refused(buffer.getvalue())


def test_a_file_over_the_size_cap_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(import_file, "MAX_FILE_BYTES", 100)
    assert "larger than" in refused(b"kind\n" + b"CLASS\n" * 50)


def test_too_many_rows_are_refused_in_both_formats(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(import_file, "MAX_ROWS", 3)
    rows = [["kind"]] + [["CLASS"]] * 4
    assert "more than 3 rows" in refused(xlsx(*rows))
    assert "more than 3 rows" in refused(b"kind\n" + b"CLASS\n" * 4)
    read_table(xlsx(*rows[:4]))  # exactly three rows is fine


def test_a_spreadsheet_that_declares_a_huge_sheet_of_blank_rows_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(import_file, "MAX_ROWS", 10)
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet["A1"] = "kind"
    sheet["A500"] = "CLASS"  # nothing between: blank rows still count
    buffer = io.BytesIO()
    workbook.save(buffer)
    assert "more than 10 rows" in refused(buffer.getvalue())


def test_a_very_long_cell_is_refused_with_its_row_number() -> None:
    assert "Row 2" in refused(b"kind,path\nCLASS," + b"x" * 2001 + b"\n")


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        (b"\n\n", "no rows|first row"),
        (b",,\nCLASS\n", "first row"),
        (b"kind,Kind\nCLASS,CLASS\n", "same name"),
    ],
)
def test_a_file_without_a_usable_header_is_refused(data: bytes, reason: str) -> None:
    import re

    assert re.search(reason, refused(data))


def test_a_row_wider_than_the_header_is_refused_in_both_formats() -> None:
    # An unquoted comma inside a value would otherwise drop the end of the row without a word.
    assert "Row 2" in refused(b"kind,path\nCLASS,Class 11,extra\n")
    assert "Row 2" in refused(xlsx(["kind", "path"], ["CLASS", "Class 11", "extra"]))
    # Empty cells beyond the header are harmless.
    assert read_table(b"kind,path\nCLASS,Class 11,,\n").rows[0].cells == {
        "kind": "CLASS",
        "path": "Class 11",
    }


def test_content_in_columns_beyond_the_limit_is_refused_even_for_a_formula() -> None:
    far = [None] * import_file.MAX_COLUMNS  # the 41st column
    assert "Row 2" in refused(xlsx(["kind"], ["CLASS", *far[1:], "hidden"]))
    assert "formulas" in refused(xlsx(["kind"], ["CLASS", *far[1:], "=1+1"]))


def test_a_spreadsheet_whose_sheet_xml_is_damaged_is_refused_not_a_server_error() -> None:
    good = io.BytesIO(xlsx(["kind"], ["CLASS"]))
    damaged = io.BytesIO()
    with zipfile.ZipFile(good) as source, zipfile.ZipFile(damaged, "w") as target:
        for member in source.infolist():
            content = source.read(member)
            if member.filename == "xl/worksheets/sheet1.xml":
                content = b"<worksheet><sheetData><row><c r="  # cut off in the middle
            target.writestr(member, content)
    assert "valid .xlsx" in refused(damaged.getvalue())
