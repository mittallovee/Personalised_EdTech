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
| `VERIFY_QUESTION` (AI verification, the "QC prompt") | How the AI verifies the question: stem completeness, answer, options, solution, units/sign conventions, what to report | P1 |
| `SOLVE_MISSING_ANSWER` | How the AI solves and shows its working | P1 |
| `TAG_METADATA` | How chapter/topic/concepts/difficulty/Bloom are chosen | P1 |
| `EXTRACT_QUESTIONS` (ingestion) | How pages are split into questions and structured | P1 (edit marked "advanced") |
| `GENERATE_VARIANTS` | How variants are produced | P2 (with the feature) |
| `GENERATE_DIAGRAM` / `EDIT_DIAGRAM` | Diagram style and rules | P2 (with the feature) |

Note: in this app **"QC" means human review**. The AI equivalent is the *AI verification* operation above
(what the owner calls the "QC prompt"). Its results are advisory findings plus suggested corrections; they
never count as human QC.

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

1. **Platform default**: shipped and maintained by us, versioned (`verify v3`).
2. **Coaching default**: a coaching may create its own versions from the platform default; used by everyone
   in the coaching. Optionally per target language (e.g. a special Tamil translation prompt).
3. **Personal prompt** (owner decision, 18 Oct): any faculty may save **their own** prompt versions for an
   operation ("My strict verification prompt"). They're visible only to that faculty (admins can view them)
   and never change what others use.
4. **Per-run choice**: when running an AI action, the user picks which prompt to use: coaching default,
   one of their personal prompts, or a **one-off custom prompt** typed for this run only. They can also add
   short extra instructions. The run records exactly what was used.

The locked parts (output format, safety preamble, variables) apply at every level. That is what lets a
user's own prompt still produce results the app can read and validate.

## 4a. Model selection for every run

In the same dialog the user picks the **AI model** from the coaching's enabled models. That list comes from
the providers' **live model lists as of today** (see requirement H-17), not a list hard-coded by us.
Defaults: the coaching's default model for that operation.

```text
┌ Verify question Q7K2M9P ─────────────────────────────────────────┐
│ Prompt:  (•) Coaching default  "Verify v4"   [view]               │
│          ( ) My prompts        [Strict numeric check v2 ▾] [view] │
│          ( ) Custom for this run  [ edit box ]                    │
│ Extra instructions (optional): [ check sign conventions        ]  │
│ Model:   [ provider / model ▾ ]  (enabled, supports this task)    │
│ Estimated cost: ₹… · Budget left this month: ₹…                   │
│                                   [ Cancel ]  [ Run verification ]│
└───────────────────────────────────────────────────────────────────┘
```

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
| View coaching/platform prompts and history | ✅ | ✅ | ✅ | ✅ |
| Create/edit/test **personal** prompts; one-off custom prompt per run | ✅ | ✅ | ✅ | ✅ |
| Choose model per run (from enabled list) | ✅ | ✅ | ✅ | ✅ |
| Create/test/activate/rollback **coaching default** prompts | — | ✅ | ✅ | ✅ |
| View any faculty's personal prompts | — | — | ✅ | ✅ |
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
prompt_templates   (id, operation, scope: PLATFORM|COACHING|PERSONAL, organization_id NULL,
                    owner_user_id NULL, name, target_language NULL)
prompt_versions    (id, template_id, version_no, instructions, settings_json, change_note,
                    author_id, created_at, status: DRAFT|ACTIVE|RETIRED, content_hash)
prompt_activations (template_id, version_id, activated_by, activated_at)   -- history of switches
ai_runs.prompt_version_id NULL, ai_runs.custom_prompt_text NULL (one-off), ai_runs.rendered_prompt_hash,
ai_runs.extra_instructions, ai_runs.model_id
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
8. Faculty X's personal prompt is not visible to faculty Y and never used for Y's runs; an admin can view it.
9. A one-off custom prompt is stored on that run and shown in the question's AI history; it does not appear in the library.
10. The model dropdown shows only models that are enabled for the coaching **and** support the operation.
