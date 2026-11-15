# M3 demo: check question authoring yourself

M3 ("Question authoring") is done when the [phase plan](../product/02-phase-plan.md) exit criterion holds:
**all nine formats save when valid and have invalid answers rejected** (the spec-v1 examples are the test
data). This page shows how to see that on your PC, then walks through everything M3 can do in about an
hour. Setup is in the [README](../../README.md#run-it-locally-windows-pc-with-docker-desktop); the design
is in the [M3 design note](../architecture/m3-design-note.md).

Use made-up questions and `@example.com` emails. Never type real coaching content while testing.

## 0. Start fresh

```bash
docker compose up --build -d
```

Sign in as the Owner of a test coaching (see the [M2 demo](./m2-demo.md), steps 1 and 2, if you do not have
one). Everything below is done as the **Owner or an admin**, except where it says faculty. The menu now has
**Syllabus, Concepts, Exams & sources, Bulk import, Answer limits, Questions** and **Passages**.

## 1. The lists a question refers to (C-01 to C-13)

| Step | Expected |
|---|---|
| Menu → **Syllabus**. Add a class ("Class 11"), then a subject under it ("Physics"), a chapter, a topic | Each level appears under its parent; a name you rename keeps its place; **Retire** hides it from new questions but old ones keep it |
| Menu → **Concepts**. Pick the subject, add "Velocity" with an alias | Searching the alias finds the concept |
| Menu → **Exams & sources**. Add an exam ("JEE Main") and a source (a book) | Both are listed; nothing is ever deleted, only retired |
| **Bulk import** → download the template, fill two rows, upload it | A preview table says what is new, changed or an error; **Apply** is refused while any row is an error; applying twice changes nothing |

## 2. Write a question (D-01, D-02, D-11, E-04)

| Step | Expected |
|---|---|
| Menu → **Questions**. Choose a format, press **Start question** | The editor opens with the permanent **code** (eight letters and digits). The **Findings** panel says what is still to do |
| Type in the question box and stop | After a moment the status says **All changes saved**. Reload the page: the text is still there |
| Fill in the options and mark the correct one | "Still to do" shrinks as you go. A format's answer rules are checked by the server: an integer of 1000, a digit of 10, a numerical range that is reversed, a matching option that uses one right item twice are named under **Mistakes** |
| **Labels**: class, subject, chapter, topic, concept, difficulty, Bloom level | The pickers go down one level at a time; a retired item cannot be chosen |
| **Preview** tab | The question as a student sees it, options labelled A to D. Nothing about the answer shows until you tick **Show the answer and solution** |
| **Save checkpoint** | "Checkpoint saved." The saved version is frozen for good; you keep editing a copy |
| **Archive**, then **Restore** | An archived question leaves the list; it keeps its code |

Try each of the nine formats: single correct, multiple correct, integer, single digit, numerical, matching,
assertion-reason, multiple statement, and a question under a passage (section 5).

## 3. Equations and pictures (D-04, D-05, D-07)

| Step | Expected |
|---|---|
| In a paragraph, type `\(v = u + at\)` | A preview appears under the box, drawn as a student will see it |
| **Add equation** | A box for a displayed equation; a mistake in it is flagged beside it |
| **Visual editor** on an equation | A box where `a/b` becomes a fraction; **Use this equation** writes the LaTeX back. **Insert equation** on a paragraph puts one at the cursor |
| **Add picture**, choose a PNG, JPEG or WebP | A crop screen with one slider per side and a preview; **Use this picture** uploads it |
| Write the **alt text** (a description in words) and a caption | The question stays "still to do" until the alt text is written. The student preview shows the picture, its description and its caption |
| Try a file that is not a picture (rename a text file to `.png`) | "This file could not be read as a picture." Nothing is uploaded |

## 4. Two people, one question (E-04)

Open the same question in two browser windows. Type in one and let it save. Type in the other: it says
**Someone else changed this** and offers **Reload**. Nothing is overwritten silently; **Save checkpoint** on a
stale screen offers **Reload** too.

## 5. Passages (D-14)

| Step | Expected |
|---|---|
| Menu → **Passages** → **Start a passage** | An editor with a title and the shared text |
| Write both, then **Save checkpoint** | "newest checkpoint: 1". Questions can only be written under a **saved** checkpoint |
| **Add question 1** (choose a format) | The question editor opens with the **passage shown above it**. The Preview tab shows the passage above the question |
| Change the passage and save a checkpoint | The passage page lists the question as "On checkpoint 1; newest is 2". The question still shows the text it was written with |
| In the question, press **Move to checkpoint 2** | It now shows the new text. Nothing moves by itself |

## 6. Answer limits (D-03)

| Step | Expected |
|---|---|
| Menu → **Answer limits** | The built-in values, with the widest range each may take |
| Set the integer **Highest key** to 9999 and **Save limits** | "Saved." A question with an integer key of 5000 stops showing a mistake |
| Lower it to 100 | The same saved question shows the mistake again, and its text is untouched: a changed limit only changes what the checks say |
| **Add limits for an exam** → JEE Main, highest key 99999 | Questions labelled with that exam use it; others keep the coaching's value |
| Type `12.5` in a whole-number box, or a lowest key above the highest | The box is named, or the server's reason is shown. Nothing is saved |

## 7. Who can do what (A-03, B-06, D-11)

*Second browser, signed in as faculty.* Faculty see **Questions** and **Passages**; they see and open only
their **own** drafts (a question of someone else says "does not exist, or you may not open it" so its
existence is not given away). A person with the **edit others** grant, and admins, see every draft. Faculty
have no **Answer limits** or **Users & grants** item.

## How M3 is checked on every pull request

Every change to `main` has to pass the same seven checks as before. For M3 they prove the exit criterion
and the test list (T23 to T32 in the design note):

| Test | Where it lives |
|---|---|
| T23 the nine formats: draft saves, ready fixture has no findings, invalid answers named | `services/api/tests/unit/test_question_content.py` and `test_question_content_properties.py` (Hypothesis) |
| T24 syllabus hierarchy | `services/api/tests/integration/test_taxonomy_nodes.py` |
| T25 Excel/CSV import | `test_catalogue_import.py`, `test_catalogue_import_apply.py` |
| T26 permissions | `services/api/tests/unit/test_permissions.py` and the API tests |
| T27 revisions and checkpoints | `test_question_revisions.py`, `test_questions_storage.py` |
| T28 passages | `test_passages.py`, `test_passage_children.py` |
| T29 pictures | `tests/unit/test_images.py`, `test_assets.py`, `test_question_pictures.py` |
| T30 isolation for every table | `test_tenant_isolation.py` and `test_every_tenant_table_is_isolated.py` (finds every table with an `organization_id` and requires forced row-level security) |
| T31 the renderer is safe | `packages/content-renderer/tests` |
| T32 the browser journeys | `apps/e2e/tests`: `m3-exit.spec.ts` runs **each of the nine formats** (draft, finished, preview, a wrong answer named, a checkpoint), plus the specs for questions, passages, answer limits, catalogues and import |

You can run part of this on your PC (`make check` in the README, and [apps/e2e/README.md](../../apps/e2e/README.md));
the breaking-change comparison, the secret scan and the dependency audits run only on GitHub.

## What M3 does not have

- Review, approval and publishing, the bank list with search and filters, version history screens (M4).
- AI of any kind: tagging, translation, solving, checking (M5).
- Uploading a paper or book and extracting questions from it (M6).
- Tables and lists inside a question can be stored and shown but are not edited on screen yet.
- Pictures are never deleted by the app; clean-up of unused uploads comes with M7.
- **Not backed up yet:** the uploaded pictures live in the Docker volume `assetdata`, which the database
  backup script does not copy. Real scheduled backups (K-16) must include it before real content is used.

## If something goes wrong

| Symptom | Fix |
|---|---|
| A picture will not upload | PNG, JPEG or WebP only, up to 10 MB and 40 megapixels; a very long list of uploads in a short time is limited (try again in a few minutes) |
| "Someone else changed this" | Press **Reload**; your last typing on that screen was not saved |
| The editor shows "Not saved" | The server could not be reached; **Try saving again** keeps what you typed |
| Docker stopped answering | Restart Docker Desktop, then `docker compose up -d` (your data is kept in volumes) |
| Anything else | `docker compose ps`, `docker compose logs --tail 100 api`, and send the output |
