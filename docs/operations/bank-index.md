# The bank index (M4, F-01, F-02)

The question bank list, its filters and its counts do not read the questions themselves (a question's text
and labels live in JSON inside saved revisions, which cannot be filtered quickly over a lakh of questions). They
read **`bank_index`**: one small row per question with the labels pulled out into columns.

- It is **derived data**: a copy built from the questions, never the only copy of anything. Dropping every row
  loses nothing.
- It is kept **up to date automatically**: every change to a question (create, autosave, checkpoint, each review
  step, archive, restore, publish, start of a correction) updates its row in the same database transaction, so a
  change that fails leaves the list as it was.
- Each coaching sees only its own rows (row-level security), and a draft or returned question is listed, counted
  and found only for its author, admins and people with the edit-others grant.

## When to rebuild it

Normally never. Run the rebuild after:

- a bug fix in how a row is worked out (the fix does not change rows that already exist);
- an upgrade that adds something to the index (the release notes will say so: for example the text columns that
  come with search);
- restoring a backup taken before the index existed.

```bash
docker compose run --rm migrate qbank reindex-bank                       # every coaching
docker compose run --rm migrate qbank reindex-bank --organization <id>   # one coaching
```

It prints one line per coaching (`Coaching <id>: N questions indexed`). It is safe to run while the app is in use
and safe to repeat: it recomputes each row from the questions and writes it only if it changed. It works in
batches of 500 questions, one transaction per batch, so it never holds one open for long. It needs the table-owner
connection (`MIGRATION_DATABASE_URL`), like `create-platform-admin`, which the `migrate` service already has.

## How to tell the index is wrong

The automatic tests compare the rows written by every kind of change with the rows a rebuild writes. If a list
ever disagrees with a question you open, run the rebuild for that coaching, and tell the engineering side what you
did before it disagreed.
