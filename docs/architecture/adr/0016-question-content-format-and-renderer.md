# ADR-0016: Question content as typed blocks, LaTeX equations, one shared renderer
- Status: Proposed · Date: 2026-10-22 · Milestone M3

## Context
Questions mix words, symbols and pictures in seven languages (D-04, D-05). The same content will be shown
in the faculty editor, the student-style preview (D-10) and, in later phases, student web and mobile apps,
tests and exported papers. It also arrives from outside: AI output and extracted documents (M5, M6).
Anything that reaches a screen as HTML is a cross-site-scripting risk, and question text is untrusted
data (AGENTS.md: "never render question content as raw HTML").

## Decision
- **Stored form.** A question revision is a JSON document, schema version 1, built from typed **blocks**:
  `paragraph`, `equation`, `image`, `table`, `list`. There is no HTML, Markdown or rich-text format in
  storage. Option, item and statement ids are stable strings inside a revision, and answers refer to them.
  The shape follows spec-v1's fixtures (`QUESTION_SCHEMA_EXAMPLES.md`), validated by Pydantic models in the
  `questions` module; unknown fields and block kinds are rejected, and size limits are configuration.
- **Equations are stored as LaTeX source.** A displayed `equation` block holds `format: "latex"` and the
  `source`. **Inline equations** live inside paragraph text between `\(` and `\)`; a literal backslash-paren
  is written `\\(`. The visual editor (MathLive) only helps to *write* LaTeX; what it produces is what is
  stored, so there is one canonical form to search, diff, translate and render. MathML is deferred to
  Phase 2 (D-06) and would be a new `format` value, not a second storage model.
- **One renderer.** `packages/content-renderer` is the only code that turns content into screen output.
  - Text always becomes text nodes, never parsed as markup.
  - Equations go through **KaTeX** with `trust: false` (no links, no raw HTML or style injection), a
    bounded `maxSize` and `maxExpand`, and `throwOnError: false` so a broken formula shows its source in
    an error style instead of breaking the page.
  - Images are `<img>` pointing at the authorised asset endpoint, with the alt text.
  - The package has no business rules and no network calls, so student apps can reuse it.
- **The server validates structure, not typesetting.** Python cannot run KaTeX, so the API checks length,
  allowed block kinds and balanced `\(`…`\)` pairs, not that the LaTeX typesets. A formula that KaTeX
  cannot parse is shown as an error by the editor and the preview. M4 decides whether publication needs a
  stronger server-side check (for example an allow-list of commands) once real content shows what is needed.
- **Images** are separate assets (ADR-0012) referenced by id; a saved revision that references one keeps it
  alive.

## Consequences
+ One canonical, inspectable form; safe by construction (no HTML path to the DOM); AI and extraction output
  can be validated against the same schema; the renderer is reusable for student apps.
+ Inline maths in sentences works from the first release.
− Authors cannot paste formatted text with bold or italics (not required by D-04); can be added later as a
  new inline span kind without changing existing content, because the schema is versioned.
− Typesetting problems are visible only in a browser, not in server-side checks.
− KaTeX does not support every LaTeX command; unsupported ones show an error and the source is kept.

## Alternatives considered
- **Markdown + `$…$`:** familiar, but ambiguous around `$` and needs a parser we would have to harden; no
  structure for options, tables or images.
- **HTML sanitised on save/display:** flexible, but any sanitiser bug becomes a vulnerability and content
  could not be diffed or validated field by field.
- **MathML as storage:** verbose, harder for people and AI to write, and conversion to and from LaTeX is
  not lossless.
- **Rich-text editor state (ProseMirror/Slate JSON):** ties storage to one editor library.
