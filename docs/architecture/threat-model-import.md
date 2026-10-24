# Threat model: the syllabus Excel/CSV import (K-10)

Requirement **K-10**, decision record [ADR-0018](./adr/0018-syllabus-import-parsing-stays-in-process.md). Written
24 Oct 2026, before the import screen (M3 PR 2d-3) is built. The import exists in the API already (PRs 2c-1 to
2c-3); this document asks: *what can a hostile or careless file, or a hostile or careless admin, do through it, and
is what we have enough?*

A threat model is a structured list of "what could go wrong, how, and what stops it". It is not a proof of
safety; it makes the gaps visible so they can be closed on purpose. Plain words are used on purpose: the owner
decides on it.

## 1. What is protected, and from whom

| We protect | Why it matters |
|---|---|
| **The API process stays responsive for every coaching** | One API process serves all coachings. A request that hogs it slows everyone down. |
| **The syllabus stays what the admin meant** | The import changes the catalogue every question is filed under. |
| **One coaching never sees or changes another's data** | The platform's central promise (ADR-0005). |
| **The server's files, network and memory** | A file parser is the classic way into a server. |
| **The database does not fill up** | Every preview is stored. |

**Who can upload:** only a signed-in **owner or admin of a coaching** (`MANAGE_CATALOGUES`). The permission is
checked **before the file is read** (`create_import` calls `require(...)` first), so a stranger or a faculty member
cannot make the server read a byte. That makes the realistic attackers:

1. an admin who is **careless** (uploads the wrong or a huge file, retries in a loop),
2. an admin whose **account has been taken over** (phished password), and
3. a **malicious or curious admin of one coaching** probing for a way into another's data or into the server.

Files from the public internet are out of scope until M6 (document uploads; see K-17).

## 2. How a file travels

```
browser ──► web app (same-origin proxy, ADR-0014) ──► POST /api/v1/taxonomy/imports?file_name=...
   1. permission check (owner/admin of this coaching)                        import_api.create_import
   2. read the body, stop at 5 MB                                            import_api._read_body
   3. read_table(bytes): spreadsheet (ZIP/XML) or CSV, with limits           import_file.py   (runs in a worker thread
   4. build_plan(table, syllabus snapshot): what each row would do            import_plan.py    of the API process)
   5. store the preview: file name, SHA-256, counts, the checked rows (JSON)  catalogue_imports (row-level security)
   --- later, a separate request ---
   6. apply: only if no row is an error and the syllabus has not changed     import_apply.py
```

The file itself is **never written to disk and never kept**: only its name, its checksum and the parsed rows are
stored. Nothing in the file is executed, evaluated or followed.

## 3. Threats, one by one

"Evidence" names the test or code that shows the control works. "Residual" is what is left after the control.

| # | Threat | How it would work | What stops it today (evidence) | Residual risk |
|---|---|---|---|---|
| T1 | **Zip bomb** | A tiny `.xlsx` that expands to gigabytes | File ≤ 5 MB; ≤ 200 parts; total declared unpacked size ≤ 20 MB, checked before anything is unpacked (`test_an_archive_that_expands_enormously_is_refused_without_unpacking_it`, `..._with_very_many_parts_...`) | Low |
| T2 | **Lying sizes in the archive** | The archive declares small sizes but holds more | The zip reader stops at the declared size and then fails its own check; a lie gives a refusal (`test_an_archive_that_understates_the_size_...`, added with this document) | Low |
| T3 | **XML "billion laughs"** | A sheet defines nested entities that expand to gigabytes | `defusedxml` refuses entity declarations. Added with this document: `test_xml_entities_are_refused_...` (3 variants, also in shared strings). The tests pin the behaviour; today the standard XML parser refuses these particular inputs as well, so they would also catch a future parser change that stopped refusing them | Low |
| T4 | **XML external entities (XXE)** | An entity points at `file:///etc/passwd` or a web address so the server reads or fetches it | Same: refused, nothing read or fetched; test checks the message holds no file content | Low |
| T5 | **Path traversal / reading other files** | A workbook relationship points at `../../etc/passwd`, an absolute path or a URL | The reader only looks a part up **by name inside the archive in memory**; it never opens a path or URL from the file. Added: `test_a_sheet_relationship_that_points_outside_the_archive_is_refused` (4 variants). Nothing is extracted to disk | Low |
| T6 | **Huge or deep XML** | Millions of elements, attributes, nesting levels, children in one cell | Constant-memory streaming reader with limits on depth, tag size, parts per cell, cells per row, rows, columns (`test_deeply_nested_xml_...`, `..._millions_of_attributes_...`, `..._hundreds_of_thousands_of_children_...` and about 15 more) | Low |
| T7 | **Formula injection / formulas that differ from what is shown** | A cell holds `=HYPERLINK(...)` or a macro-like formula | Formulas are **never evaluated**; a sheet with any is refused (`test_a_spreadsheet_with_a_formula_is_refused`) | Low. See T14 for export |
| T8 | **Pretending to be another file type** | A `.csv` that is really a ZIP, or the reverse | The file is judged by its **content**, not its name (`test_the_file_is_judged_by_its_content_not_its_name`) | Low |
| T9 | **Slow API for everyone (CPU)** | An admin (or a stolen admin account) uploads the largest allowed file again and again, or from many tabs | Size/row/cell limits cap **one** upload. **Measured cost of the worst allowed file: about 2.5 s of one CPU core** (section 4). **No limit on how often** an upload may be made and no cap on how many are parsed at once | **Medium: gap G1** |
| T10 | **Memory** | Many large uploads at once | One parse needs about 25 MB on top of the 5 MB body (section 4); ten at once is a few hundred MB | Low–medium, same gap G1 |
| T11 | **Database fills up** | Each preview stores every checked row as JSON: **6 to 8 MB for 20,000 rows** (7.9 MB with names in two languages). Previews are never deleted (design note §4.4) | None: no per-coaching count, size or age limit | **Medium: gap G2** (100 uploads is 600 to 800 MB) |
| T12 | **Cross-coaching access** | One coaching reads or applies another's preview, or the preview mixes snapshots | `catalogue_imports` has forced row-level security (migration 0017); the snapshot is read in one repeatable-read transaction; apply takes the syllabus lock and checks a fingerprint (`IMPORT_STALE`); tests T25 | Low |
| T13 | **A preview that differs from what is applied** | A change between preview and apply | Apply acts on the **stored rows** of the preview, not the file; refused if the syllabus changed; all-or-nothing; nothing is deleted or renamed by an import | Low |
| T14 | **Hostile text in names** | Control characters, HTML, very long or look-alike names; later exported to a spreadsheet and used for CSV/formula injection there | Names go through the same validator as the screens (no control characters, length caps, Unicode-normalised duplicate check); the web app shows names as text, never as HTML (AGENTS.md §3). **No export of catalogue names exists yet** | Low now. **Any future export must prefix cells starting with `=`, `+`, `-`, `@`** (note for the export feature) |
| T15 | **Replay / double submit** | The same upload sent twice | `Idempotency-Key` returns the same preview; applying twice changes nothing | Low |
| T16 | **Secrets or content in logs** | The file's content ends up in logs or error messages | The import code does no logging of content; the file name is validated as one line; refusal messages name a row number and a reason, not cell content (except the column or kind the admin typed) | Low |
| T17 | **Slow-upload connection hogging** | Many connections trickle a body | Not an import-specific problem; depends on server and proxy timeouts | **Not verified** (see section 6) |

## 4. Measurements

Measured on 24 Oct 2026 on the development container (one core, Python 3.14), with the real `read_table` and
`build_plan` and synthetic syllabus files, each case in a fresh process. Real timings on the owner's PC will differ;
the **shape** is what matters. Method: build the file with a spreadsheet writer, then time `read_table`, then time
`build_plan` on the result, and read the process's peak memory.

| File | Size | `read_table` | Memory added | `build_plan` | Stored preview |
|---|---|---|---|---|---|
| `.xlsx`, 20,000 rows × 10 columns | 0.6 MB | 1.2 s | about 14 MB | 0.4 s | 5.8 MB of JSON (bare rows) |
| `.xlsx`, 20,000 rows × 14 columns | 0.8 MB | 1.8 s | about 17 MB | 0.3 s | 5.8 MB |
| `.xlsx`, 20,000 rows × 17 columns | 0.9 MB | 2.3 s | about 18 MB | 0.4 s | 5.8 MB |
| `.xlsx`, 20,000 rows × 20 columns | 1.0 MB | **2.4 s** | about 19 MB | 0.4 s | 5.8 MB |
| `.xlsx`, wider than that | 1–2 MB | refused ("too large once unpacked") in under 10 ms | none | none | none |
| `.csv`, 20,000 rows × 40 columns | 2.4 MB | 0.3 s | about 23 MB | 0.3 s | 5.8 MB |

What this says:

- **One allowed upload costs at most about 3 seconds of one core and about 25 MB.** The limits do their job: there
  is no input that costs much more (the unpacked-size cap refuses wider spreadsheets instantly).
- The parse holds the interpreter's global lock, so while it runs **other requests of the same API process are
  slower**. With one API process (what runs today) that is every coaching.
- The stored preview is **large relative to the file** (6 MB for a 0.6 MB file; 7.9 MB for a fully filled-in
  20,000-row syllabus with labels in two languages), because every checked row is saved with its status, names
  and labels.

### 4a. Two uploads at once against a third request (measured for K-10a, 24 Oct 2026)

Same container; the largest spreadsheet the limits allow (20,000 rows, 20 columns), uploaded by one or two signed-in
sessions at once while a third client asks the health endpoint 40 to 60 times in a row.

| Running | The third request: median / worst | Time each upload took |
|---|---|---|
| Nothing | 3.4 ms / 11 ms | n/a |
| 1 worst-case upload | 3.6 ms / **1.3 s** | 2.5 s |
| 2 worst-case uploads (the cap) | 3.7 ms / **1.1 s** | **5.8 s** each |

What this says: the API **stays responsive** for other requests (the median does not move), but each read causes
a stall of **about a second** for whoever's request lands in it, and two reads at once each take more than twice
as long because they share one interpreter. That is why the cap is 2 and not higher, and why the rate limit
matters: a loop of uploads from one account is a loop of one-second stalls for everybody. (The upload "failed"
with a 422 here because the generated labels are not template columns, after the file had been read in full: the
cost measured is the read.)

## 5. Gaps found, and how they are closed

| Gap | Problem | Proposed fix | Where it goes |
|---|---|---|---|
| **G1** | No limit on how often an admin may upload, and no cap on parses running at once (T9, T10) | A per-user limit on `POST /taxonomy/imports` (for example 10 per 10 minutes, using the limiter that already protects login) and a cap of **2 parses at the same time** in the process; an upload over the cap is refused at once with a clear "busy, try again in a moment" message and a `Retry-After` header | **K-10a: built** (settings `IMPORT_UPLOADS_PER_USER`, `IMPORT_UPLOAD_WINDOW_SECONDS`, `IMPORT_PARSES_AT_ONCE`; tests in `test_catalogue_import.py`) |
| **G2** | Previews are stored forever (T11) | Keep at most **20 unapplied previews per coaching** (the oldest is dropped when a 21st is made) and drop the stored rows of an unapplied preview after **30 days**. Applied previews keep their rows (they are the record of what was imported). This changes the design note's "never deleted" for previews that were never applied | **K-10b: built** (migration 0018: `catalogue_imports_expire`, state `EXPIRED`; tests in `test_catalogue_import.py`). The owner agreed by merging PR #56 |
| **G3** | Several attacks were stopped by a library but had no test (T2 to T5) | Tests that pin the behaviour | **Done in this pull request** |

Not gaps, decided: no virus scanning (the file is never stored or opened by anything but our parser), password-protected
spreadsheets are refused (they start like an old `.xls` file and get the "Old .xls files are not supported" message).

## 6. Not verified

- **Proxy and server timeouts and body limits** (T17, and how large a body the web app's same-origin proxy
  accepts). The API reads at most 5 MB itself, but I did not test the web app's proxy with a 5 MB upload or a
  trickling one. Check it when the import screen is built (2d-3), in its browser test.
- **Timings on the owner's PC and on the cloud host.** The numbers above are from a development container.
- **Concurrent uploads on a real host.** Measured once, in the development container (section 4a); repeat it on the
  owner's PC and on the cloud host.

## 7. When this decision should be reopened

The decision in ADR-0018 (keep the parse in the API process, with the controls above) is right while all of these
hold; reopen it if one stops:

- uploads are only syllabus files from owners and admins, and no larger than today's limits;
- one parse stays under about 5 seconds and 50 MB;
- the document-upload worker for M6 (K-17) does not exist yet. **When it does, move the syllabus import onto it**:
  the reader and the planner are already pure functions (`read_table`, `build_plan`), so the move is the API
  storing the bytes and the worker calling them.
