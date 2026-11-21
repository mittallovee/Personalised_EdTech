# ADR-0022: A built-in starter syllabus ships with the app and is loaded through the import preview
- Status: Proposed (owner asked for it on 2026-11-17; accepted by merging this PR) · Date: 2026-11-17 · Requirements: C-14 (C-01, C-02, C-03)
## Context
A new coaching starts with an empty syllabus. Until now the only quick way to fill it was to write an Excel/CSV file
and upload it (C-03). Every JEE coaching needs nearly the same tree (class, subject, chapter, topic, subtopic) and
the same concepts, so each one would write the same file. The owner asked for a ready-made JEE Physics, Chemistry
and Mathematics syllabus that is part of the product.

Two existing rules are touched:
- The M3 design note says *"Real coaching syllabus files are never committed."* That rule protects a coaching's own
  material. A starter syllabus is not a coaching's material: it is a list of chapter and topic names that follows the
  public JEE Main and JEE Advanced syllabuses, written for this product.
- The syllabus belongs to each coaching (tenant isolation, ADR-0005). There is no shared, platform-level syllabus.
## Decision
1. **The starter syllabuses are files in the repository**, in the import format, under
   `services/api/src/qbank/modules/taxonomy/starter/` (`jee-physics.csv`, `jee-chemistry.csv`,
   `jee-mathematics.csv`). They hold names only: no questions, no explanations, nothing from a coaching or a book.
2. **Loading one is an ordinary import.** `POST /taxonomy/starter-syllabuses/{key}/imports` makes the same preview
   as uploading that file; the admin then applies it with the existing `POST /taxonomy/imports/{id}/apply`. So the
   existing rules hold without new code: Owner and admins only, nothing changes before apply, all or nothing, one
   audit event, rows matched by path (loading twice changes nothing), nothing is ever removed or renamed.
3. **Each coaching gets its own copy.** After loading, the coaching edits, adds to or retires items as it likes. A
   later change to a starter file does not reach coachings that already loaded it, except that loading it again adds
   the items that are new.
4. **One starter per subject**, each under the 5,000-row limit of one import. Physics, Chemistry and Mathematics
   share the rows `Class 11` and `Class 12`.
5. **Starter previews count towards the upload limits** of ADR-0018 (K-10a, K-10b): the file is trusted, but a
   preview still stores its rows.
6. **Which exam asks what is not in the starter.** The import format has no exam column, and the exam catalogue
   (C-11) is separate. The tree is the union of JEE Main and JEE Advanced, and also keeps a few items that left both
   syllabuses, so that past-year questions have a place.
7. **A unit test checks every starter file** with the import's own reader and planner: no error rows, within the
   apply limit, both classes, all kinds of item present.
## Consequences
+ A new coaching has a full JEE syllabus in a few clicks, and every coaching starts from the same names, which
  helps later features that compare or share across coachings.
+ No new tables, migrations or permissions; the import's tests and limits cover the new path.
− **The content must be kept right by people.** The chapter split follows common coaching practice, not the exact
  unit list of NTA or JEE Advanced, and was written by an AI assistant from its knowledge of the syllabuses. **The
  owner (a subject expert) reviews the three files**; a wrong or missing name is fixed by editing the CSV in a pull
  request.
− When the official syllabuses change, someone must update the files. Coachings that already loaded a starter keep
  what they have.
− Names are in English only for now; the language columns can be added to the files later and loaded again.
− The repository grows by about 3,600 lines of CSV.
## Alternatives
- **Keep the files outside the repository** and upload them by hand for each coaching. No code, but every new
  coaching depends on someone having the files, and nothing tests them. Rejected.
- **Fill the syllabus automatically when a coaching is created.** Simpler for the user, but NEET or school-only
  coachings would get a syllabus they do not want and cannot delete (items can only be retired). Rejected: loading
  stays a deliberate, previewed action.
- **One shared platform-level syllabus that all coachings point to.** Removes copies, but breaks tenant isolation
  as designed (ADR-0005) and stops a coaching from changing its own tree. Rejected.
- **Store exam coverage (JEE Main or Advanced) on each item.** Useful for filtering, but needs a new link between
  syllabus items and exams and its own screens. Left for a later requirement.
