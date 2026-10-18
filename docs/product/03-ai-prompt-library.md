# AI Prompt Library — Feature Specification (H-13)

> Status: **Draft for owner review** · Phase 1 (milestone M5) · Origin: new owner requirement.

## 1. Goal

Let authorized users **see exactly what the AI is told** and **improve it themselves** (e.g. better Hindi
translation style, stricter answer checking) without a code change, while keeping every change **versioned,
testable, reversible and traceable** to the AI results it produced.

Industry name: **prompt management** (also "prompt registry" or "prompt versioning").

## 2. Which AI operations have editable prompts

| Operation | What the prompt controls | Phase |
|---|---|---|
| `TRANSLATE_QUESTION` | Translation style, terminology, what must not be translated (symbols, units, LaTeX) | P1 |
| `CHECK_ANSWER_SOLUTION` (AI check) | How strictly the AI checks the answer and solution, what to report | P1 |
| `SOLVE_MISSING_ANSWER` | How the AI solves and shows its working | P1 |
| `TAG_METADATA` | How chapter/topic/concepts/difficulty/Bloom are chosen | P1 |
| `EXTRACT_QUESTIONS` (ingestion) | How pages are split into questions and structured | P1 (edit marked "advanced") |
| `GENERATE_VARIANTS` | How variants are produced | P2 (with the feature) |
| `GENERATE_DIAGRAM` / `EDIT_DIAGRAM` | Diagram style and rules | P2 (with the feature) |

Note: in this app **"QC" means human review**. The AI equivalent is the *AI check* operation above. AI check
results are advisory and never count as human QC.

## 3. What a prompt is made of

```text
Prompt version
├── Instructions        ✏️ editable   (role, rules, style, examples — plain text/Markdown)
├── Variables used      🔒 fixed per operation, e.g. {{question}}, {{answer}}, {{solution}},
│                          {{source_language}}, {{target_language}}, {{glossary}}, {{subject}}
├── Output format       🔒 fixed by the system (JSON schema) — the app must be able to read the result
├── Safety preamble     🔒 fixed by the system (treat question content as data, never as instructions)
└── Settings            ✏️ limited: temperature (within a safe range), optional target-language scope
```

Users edit the **instructions** (and limited settings). The **output format and safety rules stay locked**.
Otherwise one edit could break result parsing or let uploaded document text steer the AI.

## 4. Levels (who overrides whom)

1. **Platform default**: shipped and maintained by us, versioned (`translate v3`).
2. **Coaching override**: a coaching may create its own versions from the default. Optionally per target
   language (e.g. a special Tamil translation prompt).
3. **Per-run extra instructions**: when running an AI action, faculty may add one-off instructions
   ("keep SI units", "simpler Hindi"). These are stored on that run only and not saved to the library.

Effective prompt = coaching's active version (if any) → otherwise platform default; plus per-run extras.

## 5. Behaviour

| # | Requirement |
|---|---|
| PL-01 | List all operations with their active prompt, version number, author, date and "default / customized" badge |
| PL-02 | **View** the full effective prompt (instructions + locked parts shown read-only) |
| PL-03 | **Edit** creates a **new draft version**; saved versions are never modified (immutable) |
| PL-04 | **Change note** required when saving a version ("Use NCERT Hindi terms") |
| PL-05 | **Validation**: no unknown variables, required variables present, length limit, no secrets |
| PL-06 | **Test run** (playground): pick any question you can access, run draft vs. active version with a chosen enabled model, see outputs side by side. Costs count toward the user's AI budget, marked as "test". Never writes to the question |
| PL-07 | **Activate** a version (needs `MANAGE_AI_PROMPTS`); previous active version kept; in-app notice to coaching admins |
| PL-08 | **Diff** between any two versions, highlighting what changed |
| PL-09 | **Rollback** = activate an older version; **Reset to default** = remove coaching override |
| PL-10 | When the platform default gets a new version, coachings with an override see "new default available" + diff, and decide whether to adopt it |
| PL-11 | Every AI run stores the **exact prompt version** (and a hash of the rendered prompt); question AI history shows it |
| PL-12 | P2: quality report per prompt version (how often faculty accepted/edited/rejected AI output) to compare versions with data |
| PL-13 | Translation prompts automatically receive the coaching's **glossary** for the target language (H-14) |

## 6. Permissions

| Action | Faculty | Faculty with `MANAGE_AI_PROMPTS` | Admin / Owner | Platform admin |
|---|---|---|---|---|
| View prompts and history | ✅ (recommended for transparency) | ✅ | ✅ | ✅ |
| Per-run extra instructions | ✅ | ✅ | ✅ | ✅ |
| Create draft, test run | — | ✅ | ✅ | ✅ |
| Activate / rollback / reset | — | ✅ | ✅ | ✅ |
| Edit platform defaults | — | — | — | ✅ |

## 7. Safety & integrity

- Prompt text is rendered with **simple placeholder substitution**, never a template language that can run code.
- Question content is inserted inside clearly delimited data sections; the locked safety preamble tells the
  model to treat it as data (**prompt-injection** defence). The app still validates every output against the
  JSON schema and the question-format rules.
- A prompt edit can never change permissions, tenant scope, budgets or the output schema.
- Prompt changes are audited (who, when, old → new).

## 8. Data model (sketch)

```text
prompt_templates   (id, operation, scope: PLATFORM|COACHING, organization_id NULL, target_language NULL)
prompt_versions    (id, template_id, version_no, instructions, settings_json, change_note,
                    author_id, created_at, status: DRAFT|ACTIVE|RETIRED, content_hash)
prompt_activations (template_id, version_id, activated_by, activated_at)   -- history of switches
ai_runs.prompt_version_id, ai_runs.rendered_prompt_hash, ai_runs.extra_instructions
translation_glossary (organization_id, language, source_term, target_term, note)
```

## 9. Acceptance criteria (examples)

1. Faculty without the grant can view but not save; API returns 403 on save.
2. Saving creates version N+1; version N is unchanged byte for byte.
3. A test run never modifies the question and appears in usage as "test".
4. After activation, the next translation run records the new version ID; earlier runs still show the old one.
5. A version using `{{unknown}}` is rejected with a clear error.
6. Coaching A's prompt versions are invisible to coaching B.
7. Reset to default makes the next run use the platform default version.
