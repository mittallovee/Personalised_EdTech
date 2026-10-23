# M3 Design Note — Question authoring

> Status: **Draft for owner approval** · Milestone M3 of Phase 1 ([phase plan](../product/02-phase-plan.md))
> Requirements: C-01 to C-04, C-10 to C-13, D-01 to D-05, D-07 to D-11, D-14, D-15, E-04 (revisions only), E-10 (drafts)
> · ADRs 0005, 0008, 0011, 0012 (to be accepted), **0016 (new)** · Builds on the [M2 design note](./m2-design-note.md)
> Reference input (never edited): `docs/spec-v1/docs/QUESTION_TYPES_SPECIFICATION.md`, `QUESTION_SCHEMA_EXAMPLES.md`,
> `PUBLICATION_REQUIREMENTS.md`, `TAXONOMY_AND_KNOWLEDGE_GRAPH.md`, `QUESTION_CONTENT_EDITOR.md`

## 1. Goal

Faculty can enter a Physics question by hand, in any of the nine formats, and the system refuses wrong
answers: you type equations (LaTeX or a visual editor), add images and passages, pick the syllabus
position from a catalogue your admin set up, and see the question exactly as a student will. Every
question gets its permanent 8-character code, and every saved change is kept as a revision.

**What M3 does not do:** review and publish (M4), search and the bank list (M4), AI (M5), uploading
whole papers (M6). A question made in M3 stays a **draft**. Drafts are complete, valid and ready for
M4's workflow; they cannot be published yet.

## 2. What you will be able to do at the end of M3

1. As admin: set up the **syllabus** by hand or by importing an Excel/CSV file (class → subject → chapter →
   topic → subtopic, plus concepts with aliases), and the **exams** (JEE Main, NEET…) and **sources** (a
   book, a test series…) that questions refer to. Retire an item without breaking old questions.
2. As faculty: start a question in one of the nine formats, write the stem, options and answer, with
   equations typed as LaTeX or built in a visual editor, images with alt text, tables and lists.
3. Pick class, subject, chapter, topic, concepts, difficulty (with the written 1–10 guide beside it), Bloom
   level and, for a past-year question, exam and year.
4. See the **findings** panel (what is still missing or wrong) update as you type, and see the
   **student-style preview**. A wrong answer, for example "999.01" or an option that does not exist, is
   named in plain words.
5. Close the browser and come back: the draft was **autosaved**. Save a **checkpoint** to keep a named
   point you can return to, and compare two checkpoints.
6. Build a **passage** (shared text) with several questions under it, each with its own code.
7. Archive a draft you do not want, without losing its code.

## 3. What is built where (modules)

| Module | Owns | Why separate |
|---|---|---|
| `taxonomy` | Syllabus nodes, concepts, labels/aliases, exams, sources, languages, Bloom, difficulty guide, Excel/CSV import | One admin-managed catalogue that questions *refer to*; other modules read it only through `taxonomy.public` |
| `questions` | Question masters, versions, revisions, passages, content blocks, the nine validators, answer limits | The heart of the product; its rules are pure code in `domain/` (no database), so they can be tested with the spec-v1 fixtures alone |
| `assets` | Image upload, checks, storage, serving | Files have different risks from rows (ADR-0012); M6 reuses it for documents |

Frontend: new package `packages/content-renderer` (KaTeX) is the **only** way question content reaches the
screen, in the editor, the preview and later the student apps (D-10; AGENTS.md "never render question
content as raw HTML").

## 4. Catalogues (taxonomy module)

### 4.1 The syllabus tree (C-01, C-03, C-04, C-10)
- One table of **nodes** with a `kind`: `CLASS`, `SUBJECT`, `CHAPTER`, `TOPIC`, `SUBTOPIC`. Each node has a
  parent of the next kind up (a class has none). The database itself enforces the pairing with a composite
  key, so a topic can never hang under a class.
- **Labels per language** (C-10): the seven catalogue languages (en, hi, gu, bn, mr, te, ta). A node needs
  a label in English; others are optional and shown when the question's language has one, else English
  (never blank).
- **Retire, don't delete.** A node can be *deprecated*: no one can pick it for a new question, but old
  questions keep pointing to it and still read correctly (C-04). **Syllabus items are never deleted at
  all** (the database role has no delete right on them), so a saved question can never point at
  nothing. Retiring a parent does not retire its children; nothing new can be added under a retired
  item, and an item cannot be restored while its parent is still retired.
- Admin and Owner (and a platform admin acting in the coaching) create, edit, reorder and deprecate nodes.
  Faculty only choose. Faculty never create syllabus items (spec-v1 taxonomy rule).

### 4.2 Concepts (C-02, C-03)
- A **concept** is a topic of understanding ("Newton's second law") that belongs to one **subject**, with
  labels in each language and any number of **aliases** ("Newton's 2nd law"). Aliases are matched after
  trimming, case-folding and Unicode normalisation; they never merge two concepts by themselves.
- A question has one **primary** concept and any number of **secondary** concepts, all of its subject.
  Secondary concepts may sit outside the primary topic (C-02).
- In M3 a concept is `ACTIVE` or `DEPRECATED`. "Provisional, added by AI" and alias-matching by AI arrive
  in M5 (C-05, C-06); the table is ready for them.

### 4.3 Exams, sources, Bloom, difficulty (C-11, C-12, C-13)
- **Exams** (admin-managed list): name, short code, active or retired. A past-year question (PYQ) names an
  exam and a year; date, shift and paper code are optional free values on the question.
- **Sources** (admin-managed): kind (book, module, test series, PYQ paper, other) and name. A question may
  name one source and a free "where in it" note (page, question number).
- **Bloom level** is a fixed catalogue: Remember, Understand, Apply, Analyze, Evaluate, Create, stored as
  stable keys with English labels now.
- **Difficulty 1–10** with a written guide shown beside the field (draft in the appendix). The guide
  text is a platform default for now; the owner approves its wording (§14).
- **Languages:** the seven initial languages are a fixed list in the code, the same for every coaching.
  Letting a coaching add or switch off languages is a later admin feature (M5, with translation);
  capability status (can the OCR or AI read it?) is not shown until then.

### 4.4 Excel / CSV import (C-03)
Importing is a **preview, then apply** flow, so nothing changes until the admin has seen the result.
- **Upload** an `.xlsx` or `.csv` file. The server checks the content, not the file name (a real
  spreadsheet or plain text), a size cap (5 MB), a row cap (20,000), and never evaluates formulas. The
  reader opens the file in read-only mode and refuses an archive that expands beyond a fixed limit
  (decompression-bomb guard).
- The app offers a **template** to download. One row per item: `kind, path (Class 11 > Physics > Kinematics …),
  label_en, label_hi …, aliases, sort`. A second sheet lists concepts: `subject path, label_en …, aliases`.
- The preview lists every row as *new*, *changed*, *unchanged* or *error* (with the row number and a
  plain reason), and totals. Rows are matched by their path in English, so uploading the same file twice
  changes nothing.
- **Apply** runs in one transaction on exactly the preview that was shown (the parsed rows are stored with
  the preview, not re-read from the file). Any error row blocks apply; the admin fixes the file and
  uploads again. An import never deletes or deprecates anything: removal is a deliberate click.
- Every apply is one audit event naming the counts. Real coaching syllabus files are never committed; tests
  use a small synthetic file.

## 5. Questions (questions module)

### 5.1 Identity: master, version, revision (D-11, D-12, E-04)

```text
master   one bank question: internal id + permanent 8-character CODE (never reused, never changes)
  └ version   a line of work under that master: version 1 now; a correction of a published question is
              version 2 (M4). One *working* version per master.
      └ revision   a saved snapshot of the content. The newest one is the *working revision*.
```

- The **code** is assigned when the question is first saved, using the existing global `public_codes`
  table (ADR-0011: Crockford Base32, random, unique across coachings). A draft that is archived keeps its
  code reserved. **Questions are never hard-deleted**, only archived, so a code printed or shared is never
  reused or dangling.
- **Autosave and checkpoints** (recommended; §14 asks you to confirm). Typing triggers an autosave every
  few seconds. Autosave **updates the working revision in place**, guarded by `If-Match` so two tabs
  cannot overwrite each other silently (a stale save gets `412 REVISION_STALE`, and the screen offers to
  reload). The user can press **Save checkpoint** (and M4's *Submit for review* does it automatically):
  the working revision is then **frozen**, with a content hash, who and when, and a new working revision
  starts as a copy. Frozen revisions never change. This keeps history meaningful (a checkpoint is a point
  someone chose, or a review point) without storing a new row every few seconds for lakhs of questions.
  Comparison of two revisions (E-08) arrives in M4; M3 lists checkpoints and lets you read any of them.
- Changing a question's format is allowed on a draft only if the whole new payload validates.
- **Idempotent create:** `POST /questions` takes an `Idempotency-Key` (like M2's invitations), so a retry
  after a network failure never makes two questions or burns a second code.

### 5.2 The content (ADR-0016, D-04, D-05)
A revision's content is a JSON document of schema version 1, as in spec-v1's fixtures:
`question_type`, `language`, `stem` (a list of **blocks**), the type's own parts (`options`, `left`/`right`,
`statements`, `assertion`/`reason`), `answer`, `solution` (optional blocks), `video_solution_url`
(optional), and `metadata`.

| Block | Content |
|---|---|
| `paragraph` | Unicode text. **Inline equations** are written between `\(` and `\)` (an extension we recommend, see below). Anything else is plain text: no HTML, ever |
| `equation` | A displayed equation: `format: "latex"` and the `source`. The visual editor produces LaTeX, so only LaTeX is stored |
| `image` | The `asset_id` of an uploaded image of this coaching, a caption and **alt text** |
| `table` | Rows of cells, each cell a list of paragraph/equation blocks |
| `list` | Ordered or unordered; each item a list of paragraph/equation blocks |

- **Why inline equations:** physics sentences mix words and symbols ("a body of mass \(m\) moves…").
  With block-level equations only, every symbol would break the line. spec-v1 does not forbid inline
  maths and the extraction work in M6 will produce it, so we store it from the start.
- **MathML** paste is Phase 2 (D-06); the schema leaves room (`format` can later be `"mathml"`).
- **Limits** keep storage and rendering safe: an equation source up to 2,000 characters, a paragraph up to
  10,000, a block list up to 100 blocks, a revision up to 256 KB. They are configuration, not hard-coded.
- Option, item and statement **ids** (`A`, `L1`, `S2`…) are stable inside a revision; answers refer to them.

### 5.3 The nine formats and their rules (D-01, D-02, D-03)
Rules are exactly spec-v1's `QUESTION_TYPES_SPECIFICATION.md`; the numbers below are **defaults** the
admin can change per format (D-03).

| Format | Parts | Valid answer |
|---|---|---|
| SCQ | exactly 4 options | one option id of the four |
| Multiple correct | exactly 4 options | one or more option ids; one id is valid |
| Integer | none | whole number 0 to 999 |
| Single digit | none | whole number 0 to 9 |
| Numerical | none | **exact** value or **one inclusive range**, 0.00 to 999.00, written as a decimal string with exactly two decimals; lower ≤ upper |
| Matching | left items, right items (any counts, 2 to 10 each by default), exactly 4 options, each a mapping from left to right items | one option id; in the **chosen** option no right item appears under two left items; unused right items are fine |
| Assertion–reason | assertion, reason, exactly 4 options (wording is the author's) | one option id |
| Multiple statement | 2 to 10 statements, exactly 4 options | one option id |
| Passage-based | a shared passage + child questions | each child is one of the eight formats above, with its own code and answer |

Further rules that matter:
- **No floats anywhere.** Integers are JSON integers (a boolean is rejected); numerical values are decimal
  strings. Extra decimals ("9.805", which could come from AI or an import later) are **kept and flagged**,
  never rounded: the draft saves, the findings panel says "more than two decimal places", and it blocks
  publication.
- **No unit field** on numerical answers. Units live in the stem, equations or solution.
- A one-sided or disjoint numerical range, an answer-unit attribute, negative values and 999.01 are rejected
  (the last two by the default limits; an owner who finds a past-year paper with negative answers changes
  the limit, §5.4).

### 5.4 Findings: what is wrong, in plain words
Validation returns a list of **findings**, each with a `path` (which field), a stable `code` and a
message, and one of three levels:
- `error`: the content is malformed (an unknown block, an answer that names an option that does not exist).
  A draft with errors **can still be saved** (people type incomplete things), but the findings show at once.
- `incomplete`: something needed is missing for publishing (no answer yet, no primary concept, no Bloom
  level, a PYQ without exam and year, an image without alt text).
- `warning`: allowed, but worth a look (a deprecated chapter, a very long stem).

The editor and the API show the same findings; M4's *Submit* and *Publish* will refuse while any `error` or
`incomplete` finding exists. Findings are **computed from the content and the catalogue each time**, never
stored, so a retired syllabus item or a changed limit shows up on the next look.

**Limits are settings.** `GET/PUT /settings/answer-rules` (admin): per format, defaults such as integer
maximum 999, numerical maximum 999.00, matching item counts; optionally overridden **per exam** (a
JEE Advanced PYQ may allow what JEE Main does not). A changed limit never rewrites old revisions; it only
changes what the findings say.

### 5.5 Metadata (D-15)
Class, subject, chapter, topic (one each), optional subtopic, primary concept, secondary concepts,
language, difficulty (1–10), Bloom, PYQ flag with exam, year and optional date/shift/paper code,
optional source and note. All catalogue ids are checked to be **this coaching's** and to form one valid
branch (the topic's chapter is the chosen chapter…); a retired item gives a warning on an existing draft
and cannot be newly picked. The metadata lives in the revision (so a checkpoint keeps the labels it was
written with). Filtering a bank of lakhs of questions by metadata (M4) uses columns added then.

### 5.6 Passages (D-14)
- A **passage** has its own master-like record and revisions, but **no public code**: it is only context.
- A child question points to an exact **passage revision** and an order number. Editing the passage
  freezes a new passage revision; existing children keep pointing at the one they were written with
  until their author moves them. The child list of a passage shows which children are on an older
  revision.
- A passage cannot contain another passage; children may be any of the eight concrete formats, mixed.
- Each child has its own code, its own answer rules and its own life (including archive).

### 5.7 Images (D-07), storage (ADR-0012)
- Upload one image at a time from the editor: **PNG, JPEG or WebP**, up to 10 MB and 40 megapixels.
  The server checks the bytes (not the extension), decodes the image, strips location and camera data,
  and **re-encodes** it, so a file that is half image and half something else cannot be stored as it came.
  SVG, GIF, HEIC and others are refused in M3 (HEIC arrives with document ingestion in M6).
- **Cropping** happens in the browser before upload; the server stores only the final picture.
- Stored as an opaque key `org/<organization>/image/<uuid>` through a storage interface (`core/storage.py`:
  put, get, delete). Locally a Docker volume; later S3 or Google Cloud storage (ADR-0012 becomes
  Accepted with this milestone). Checksum (SHA-256) and size are in the database. Files never change once
  written.
- Served only through `GET /api/v1/assets/{id}/content`, which checks the signed-in person's coaching on
  every request (another coaching's id answers 404), with `Content-Type` from our own record,
  `nosniff`, private caching and no inline script possibility.
- An image **referenced by a saved revision cannot be deleted** (so history renders). Unreferenced
  uploads are cleaned up by a scheduled job in M7.

### 5.8 Preview (D-10)
The same renderer shows a question as a **student** will see it: stem, options labelled A–D (or the
numeric box for integer/numerical), matching columns, the passage above its children, equations
typeset. The author has a toggle to reveal the answer and solution. The preview always shows the last
**saved** content, so what you preview is what was stored. There is no scoring in Phase 1.

## 6. Who may do what (extends the M2 table)

| Action | Faculty | Admin / Owner | Platform admin |
|---|---|---|---|
| Read catalogues (syllabus, exams, sources, Bloom, difficulty guide) | Yes | Yes | Acting |
| Create/edit/deprecate catalogue items, import Excel/CSV, change answer limits | No | Yes | Acting |
| Create a question or passage | Yes | Yes | Acting |
| Edit a draft | Own drafts | Any draft in the coaching | Acting |
| Edit another person's draft | Needs the `EDIT_OTHERS` grant | Yes | Acting |
| Read a draft | Own drafts (see below) | Any | Acting |
| Archive / restore a draft | Own | Any | Acting |
| Upload an image | Yes | Yes | Acting |

- **Drafts are private to their author** (and admins, and people with `EDIT_OTHERS`) until M4's review
  queue defines who else may read a submitted question. Recommended; §14.
- A **removed or suspended** member loses all of this on the next request (B-10), as in M2. Their drafts
  stay with the coaching; an admin can still edit or archive them.
- All permission rules extend `core/permissions.py` (new actions), still tested as a full table.
- Every create, checkpoint, archive/restore, catalogue change and import writes an **audit event**.
  Autosaves do not (they would bury the log); each revision row already records who and when.

## 7. Database (migrations 0013 onwards)

All tables carry `organization_id`, `FORCE ROW LEVEL SECURITY` with the tenant policy, composite
foreign keys `(organization_id, …)` (ADR-0005), and a two-coaching isolation test (T18 pattern).

| Migration | Change |
|---|---|
| 0013 | **Built (PR 2a):** `taxonomy_nodes` (kind, parent referenced together with its kind, state, sort order, revision; sibling names unique) and `taxonomy_labels` (names in the other languages). The languages and Bloom levels are fixed lists in code, not tables |
| 0014 | **Built (PR 2a follow-up):** the syllabus CHECK also requires the parent kind whenever there is a parent |
| 0015 | **Built (PR 2b):** `exams` (name, optional short code) and `sources` (kind, name); retired, never deleted |
| 0016 | `concepts` and their labels and aliases |
| 0017 | `catalogue_imports` (the stored preview that apply uses) |
| 0018 | `question_masters` (id, code, creator, type, archived_at, revision), `question_versions`, `question_revisions` (content and metadata JSONB, hash, frozen_at, author), `passage_masters`/`passage_revisions`, `answer_rule_settings`; codes use the existing `public_codes` |
| 0019 | `assets` (checksum, size, type, width, height, key, uploader) and `revision_assets` (which saved revision uses which image, so deletion is refused) |

## 8. API (all under `/api/v1`)

| Method & path | Purpose |
|---|---|
| `GET /languages` · `GET /catalogues/bloom` · `GET /catalogues/difficulty-guide` | Fixed lists (built in PR 2a) |
| `GET /taxonomy/nodes` (filter by kind, parent, state) · `GET /{id}` · `POST` · `PATCH /{id}` (`If-Match`) · `POST /{id}/deprecate` · `/restore` | Syllabus (built in PR 2a) |
| `GET/POST /taxonomy/concepts` · `PATCH /{id}` · `/deprecate` · `/restore` | Concepts and aliases |
| `GET /exams` · `GET /sources` (+ `?kind=`) · `GET /{id}` · `POST` (`Idempotency-Key`) · `PATCH /{id}` (`If-Match`) · `POST /{id}/deprecate` · `/restore` | Exams, sources (built in PR 2b) |
| `GET /taxonomy/import-template` · `POST /taxonomy/imports` (file; creates the preview) · `GET /taxonomy/imports/{id}` · `POST /taxonomy/imports/{id}/apply` | Excel/CSV import |
| `POST /questions` (`Idempotency-Key`) · `GET /questions` (mine, or all for admins; cursor pages) · `GET /questions/by-code/{code}` · `GET /questions/{id}` | Create and read; every read carries the findings |
| `PUT /questions/{id}/working-revision` (`If-Match`) | Autosave |
| `POST /questions/{id}/checkpoints` (`If-Match`) · `GET /questions/{id}/revisions` · `GET /questions/{id}/revisions/{n}` | Checkpoints and history |
| `POST /questions/{id}/archive` · `/restore` | Archive |
| `POST /passages` · `GET /passages/{id}` · `PUT /passages/{id}/working-revision` · `POST /passages/{id}/checkpoints` | Passages |
| `POST /assets/images` (multipart) · `GET /assets/{id}/content` | Images |
| `GET/PUT /settings/answer-rules` | Answer limits |

New error codes go in `error-codes.md` in the PR that introduces them: `HIERARCHY_INVALID`,
`DUPLICATE_NAME` and `PARENT_DEPRECATED` exist now; `IMPORT_INVALID`, `IMPORT_STALE`, `ASSET_INVALID`
and `CONTENT_TOO_LARGE` are planned. A save with
findings is **not** an error (it is 200 with the findings); only unreadable or oversize content is 422.

## 9. Web

| Screen | Content |
|---|---|
| Admin → Syllabus | Tree with add, rename, labels in each language, aliases, reorder, retire/restore; Import (template download, upload, preview table, apply) |
| Admin → Exams & sources | Two small lists |
| Admin → Answer limits | One card per format with its limits and optional per-exam overrides |
| Questions → My drafts | List with code, format, stem start, status of findings, updated time; "New question" |
| Question editor | Format chooser; blocks editor (paragraph, equation, image, table, list) for the stem, options, items and solution; answer controls that match the format; metadata pickers (cascading class → … → topic, concept search, difficulty with the guide beside it, Bloom, PYQ); **findings panel**; autosave status ("Saved 10:42"); **Save checkpoint**; Preview tab; Archive |
| Equation editing | Each equation block: LaTeX source box with live typeset preview, and a button to open the **visual editor** (MathLive) which writes LaTeX back |
| Passage editor | Passage text, then its list of child questions (add, reorder, open each in the editor) |

The browser holds no rules: the findings, limits and permissions come from the API. The visual editor
(MathLive) and KaTeX are loaded only on the editor pages.

## 10. Security and safety (what could go wrong)

| Risk | Control |
|---|---|
| Question text runs script in someone's browser (XSS) | Text is rendered as text; equations only through KaTeX with `trust: false` and size/expansion limits; no raw HTML anywhere; tests feed `<script>`, `\href{javascript:…}` and oversize macros through the renderer |
| Malicious or huge spreadsheet | Content checks, size and row caps, read-only parsing, no formulas, bomb guard, runs in the API process only for small files (M6 moves heavy parsing to workers) |
| Malicious image | Magic-byte check, decode and re-encode, pixel cap against decompression bombs, no SVG, `nosniff`, no public URLs |
| Reading another coaching's drafts or images | Row-level security plus service checks on every table; ids from other coachings answer 404; isolation tests for every new table |
| Editing someone else's draft | Permission table tests; removed members stop at once |
| Two people overwriting each other | `If-Match` on every write; stale writes get 412 and a reload prompt |
| Equation source as an attack on the preview/PDF later | Source is stored as inert text; the renderer is the only consumer |
| A third-party editor library (MathLive) | Loaded only in the editor; licence and security checked before adding (it must pass `pnpm audit`) |
| Spreadsheet/CSV formula injection when exporting later | Nothing is exported in M3 |

New dependencies, each reviewed for licence and known vulnerabilities and pinned: backend **Pillow**
(images), **openpyxl** (Excel, read-only), **python-multipart** (uploads); web **katex** and **mathlive**.

## 11. Tests that prove M3

| # | Test | Type |
|---|---|---|
| T23 | **The nine formats.** Every spec-v1 fixture: the incomplete draft saves, the content-ready fixture has no findings, the "invalid replacement answer" produces exactly the named finding; boundary cases (integer 0, 999, −1, 1000, fraction; digit 0, 9, 10; numerical 0.00, 999.00, 999.01, reversed or disjoint range, 9.805 kept and flagged; matching shared right item in the chosen option; multiple-correct empty set; boolean as integer) | unit (pure domain) |
| T24 | Syllabus hierarchy: wrong parent kinds refused by the database, retired nodes not selectable but still resolving, a used node cannot be deleted, labels fall back to English | integration |
| T25 | Excel/CSV import: preview equals what apply does, running twice changes nothing, error rows block apply, malformed/oversize/bomb/formula files refused, a changed preview is refused (`IMPORT_STALE`) | integration + api |
| T26 | Permissions table for catalogues and questions (faculty, admin, Owner, platform admin acting or not, another coaching's admin, removed or suspended member) | api |
| T27 | Revisions: autosave guarded by `If-Match` (412 on stale), checkpoint freezes (frozen content cannot be changed by any path), idempotent create (retry gives the same question and code), code generation collision retry and Crockford normalisation | integration + api |
| T28 | Passages: child pins a revision, a new passage revision leaves existing children unchanged, no nesting, cross-coaching pin refused | integration |
| T29 | Images: bytes not extension, SVG and polyglot files refused, size and pixel caps, metadata stripped, another coaching's id is 404, an image used by a revision cannot be deleted | integration + api |
| T30 | Isolation (T1–T4 pattern) for every new table | integration |
| T31 | Renderer safety and fidelity: hostile text and LaTeX are inert; the same saved content renders identically in editor preview and student preview | web unit (Vitest) |
| T32 | Browser tests: an admin imports a small syllabus; faculty create one question in **each of the nine formats**, see a wrong answer named, fix it, preview it, save a checkpoint, come back to find the autosaved draft; two tabs conflict and reload | e2e |

## 12. Work plan (pull requests)

| PR | Content |
|---|---|
| 1 | This design note + ADR-0016 (docs only) |
| 2a | **Done:** syllabus items (migration 0013), the fixed lists (languages, Bloom, difficulty guide), permissions, audit |
| 2b | **Exams and sources** (migration 0015), then concepts with labels and aliases (migration 0016), as two PRs |
| 2c | Taxonomy: Excel/CSV import (preview, apply; migration 0017) |
| 2d | Web: Admin → Syllabus and Exams & sources, with browser tests |
| 3a | Question content domain: blocks, the nine validators, answer limits, findings; spec-v1 fixtures as tests (no database yet) |
| 3b | Questions persistence: migration 0018, masters, versions, revisions, codes; create, read, autosave, checkpoint, archive; permissions; audit |
| 3c | `packages/content-renderer` (KaTeX) with Vitest safety tests; preview component |
| 3d | Web: editor for SCQ, multiple-correct, integer, single digit, numerical; metadata pickers; findings panel; autosave |
| 3e | Web: editor for matching, assertion–reason, multiple statement |
| 3f | Web: visual equation editor (MathLive), inline equations |
| 3g | Images: migration 0019, `core/storage.py`, upload, serving, crop, image blocks |
| 3h | Passages: API and editor |
| 3i | Answer limits settings (API and admin screen) |
| 4 | M3 demo notes and exit checks |

The order can change if a PR grows past ~400 lines; split rather than stretch (2a was split from 2b this way).

## 13. Out of scope for M3

- Submit, review, approve, publish, comments (M4) and the diff view (E-08, M4).
- Bank list with filters and counts, free-text search, code lookup page, duplicate check (M4).
- Notifications (M4/M5), AI of any kind (M5), uploading papers and extraction (M6).
- Translations and the "source updated" flag (D-13, M5), variants (P2), MathML paste (D-06, P2).
- Adding languages beyond the seven, a student-facing app, scoring.
- Per-coaching editing of the difficulty guide, and a full custom role builder.

## 14. Decisions for the owner

1. **Approve this note** (merge PR 1), or ask for changes.
2. **Autosave in place plus checkpoints** (§5.1) instead of a new revision on every save. I recommend yes:
   history stays meaningful and the database does not grow with every keystroke. The cost: between two
   checkpoints there is only the latest autosave to go back to.
3. **Inline equations inside paragraphs** written between `\(` and `\)` (§5.2). I recommend yes; without
   them every symbol in a sentence needs its own line.
4. **Draft privacy:** drafts are visible only to their author, admins and people with `EDIT_OTHERS` until
   M4 (§6). I recommend yes.
5. **The difficulty 1–10 guide** (appendix): you know the right wording best. Edit or approve the
   draft; it is shown in the editor next to the field.
6. **Drafts are archived, never deleted** (§5.1), so a code is never reused. I recommend yes.
7. **Images:** PNG, JPEG and WebP only in M3 (§5.7). I recommend yes; other formats come with M6.
8. **Your syllabus file:** bring (later, not in the repository) the Excel you want to import to try the
   template on your own PC. M3 ships with a small synthetic example only.

## Appendix: draft difficulty guide (platform default, for owner approval)

| Level | Meaning |
|---|---|
| 1 | Direct recall of a definition, unit or formula; no calculation |
| 2 | One formula, one step, numbers given directly |
| 3 | One concept, simple calculation, standard textbook example |
| 4 | One concept with a short derivation or unit conversion |
| 5 | Two linked ideas or a multi-step calculation; typical board-exam difficulty |
| 6 | Typical JEE Main / NEET question: two concepts, a diagram, some algebra |
| 7 | Hard JEE Main: three steps or a less familiar situation |
| 8 | Easy JEE Advanced: several concepts, careful reasoning or non-obvious setup |
| 9 | Hard JEE Advanced: long chain of reasoning, edge cases, heavy algebra or calculus |
| 10 | Olympiad level: novel situation, deep insight needed; very few students solve it |
