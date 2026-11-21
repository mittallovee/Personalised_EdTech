# Load tests of the bank (K-08, M4 exit criterion)

The bank list, its filters and counts, the lookup by code and the search must stay quick on a large
bank. This page says how the test is run and what it measured. Targets (M4 design note §7.3,
decision 7): **p95 under 300 ms** for list, filter + count and code lookup, **under 800 ms** for
search, with **5 people at once**, on the owner's PC. (p95 means 95 out of 100 requests were at
least this fast.)

## What is tested

- **The data:** one coaching with **100,000 made-up questions** (`services/api/tests/load/`):
  physics-like sentences from word lists, about one in ten in Hindi, four in ten with an equation, six
  in ten with a worked solution, labels over a syllabus of 2 classes, 6 subjects, 72 chapters, 288
  topics and 180 concepts. The states are like a working bank: 70% published, 13% drafts, 8% in
  review, 3% each returned, QC passed and approved; 2% archived. Nothing in it is real coaching
  content, and the generated data is never committed (it is made fresh from a seed).
- **The people:** an owner, an admin, an edit-others holder, a QC reviewer and four faculty, so
  some see drafts and some do not.
- **The mix** (`infra/load/bank.js`, a [k6](https://k6.io) script: k6 runs "virtual users" that send
  requests at the same time and reports how long they took): a quarter plain list (50 rows with the
  exact total), a quarter list with 1 to 4 filters and its total, a fifth lookup by code (codes that
  exist, some private to someone else), and three tenths search: common words ("the", "block"),
  rarer pairs, a quoted phrase, a left-out word, typos ("acceleratoin", "velocty", "pendulm",
  "frequncy"), Hindi words and LaTeX ("frac").

## How to run it

Everything runs in throwaway containers, against the PostgreSQL server of the local stack, in a
database of its own called `qbank_load` (the seeder refuses any database whose name does not end in
`_load`). Your own data is not touched. From the repository root, in Git Bash:

```bash
export LOAD_TEST_PASSWORD="make-up-a-password-here"   # 12+ characters, used only for the load-test members
mkdir -p "$HOME/qbank-load"
MSYS_NO_PATHCONV=1 docker run -d --name qbank-load-api -p 127.0.0.1:8090:8090 \
  --add-host host.docker.internal:host-gateway \
  -e LOAD_TEST_PASSWORD -e QBANK_TEST_ADMIN_URL="postgresql+psycopg://qbank_owner:change-me-local-only@host.docker.internal:5434/postgres" \
  -v "$PWD:/src:ro" -v "$HOME/qbank-load:/load" python:3.14-slim bash /src/infra/load/serve-load-api.sh
docker logs -f qbank-load-api      # wait for "--- serving on :8090" (about 15 minutes the first time)
```

```bash
MSYS_NO_PATHCONV=1 docker run --rm --add-host host.docker.internal:host-gateway \
  -v "$PWD/infra/load:/scripts" -v "$HOME/qbank-load:/load" -e LOAD_TEST_PASSWORD \
  -e DURATION=3m grafana/k6:1.0.0 run /scripts/bank.js
```

```bash
docker rm -f qbank-load-api        # stop the API; the qbank_load database stays for the next run
```

`VUS=10` runs ten people instead of five. `SKIP_SEED=1` on the first command keeps the existing
`qbank_load` database (it is only migrated), so a re-run starts in seconds. k6 exits with an error when
a target is missed. The per-person search limit is raised for the run, because it protects the server
from one person, not from a test.

## Results

Recorded on 2026-11-17 on the owner's PC (12 processor threads, 16 GB; Docker Desktop on Windows;
PostgreSQL 17.10; one API process, as in Phase 1). k6 on the same machine.

### Building the bank

| Step | Time |
|---|---|
| Insert 100,000 questions with their versions and revisions (100 batches) | 106 s |
| Rebuild the bank index for them (`qbank reindex-bank`'s code, batches of 500) | 743 s (about 135 questions a second) |
| Migration 0031 on the filled bank (fills the word list) | 1.9 s |

The rebuild is the slow part: it reads each question's tables one question at a time. It is a rare
admin job (`docs/operations/bank-index.md`) and runs while the app is in use, so 12 minutes per
lakh is acceptable for now; it can be made set-based if a coaching grows far beyond that.

### First run: the search target failed

| 5 people, 2 minutes | p95 |
|---|---|
| list | 103 ms |
| filter + count | 85 ms |
| code | 56 ms |
| **search** | **4,870 ms** (13 searches stopped at the 5-second limit) |

Exact-word searches took 80 to 140 ms each, even "the" (in every question). **Typos took 3.7 to
4.3 seconds**: comparing a typed word with the whole text of up to 100,000 questions (the trigram
index finds tens of thousands of candidates, and each must be compared).

**The fix (4f-2, migration 0031):** a typo is a misspelt word, so it is compared with the coaching's
**list of distinct words** (`bank_words`, kept by a database trigger; 178 words in this synthetic
bank, a few thousand in a real one), and the close words found are then searched with the word index
like any other search. This is the approach the PostgreSQL documentation gives for spelling
suggestions. The threshold became word-to-word similarity 0.45 (measured: typos 0.50 to 0.67, a plural
0.63, different words such as forest/force or block/black 0.25 to 0.33). Typo searches went from about
4 s to 0.16 to 0.30 s. Search stays inside PostgreSQL, as ADR-0008 says; no other engine is needed.

### After the fix

| 5 people, 3 minutes, 8,382 requests, all answered | median | p95 | p99 | target |
|---|---|---|---|---|
| list (50 rows and the exact total) | 102 ms | **131 ms** | 155 ms | 300 ms |
| filter + count | 85 ms | **119 ms** | 162 ms | 300 ms |
| code lookup | 56 ms | **81 ms** | 93 ms | 300 ms |
| search | 144 ms | **235 ms** | 273 ms | 800 ms |

All four targets are met. About 46 requests a second in total.

| 10 people, 90 seconds (twice the target load), all answered | p95 |
|---|---|
| list | 278 ms |
| filter + count | 258 ms |
| code lookup | 211 ms |
| search | 396 ms |

With ten people the server still answers about 43 requests a second, the same as with five, and each
waits about twice as long: **the limit is the one API process, not the database.** Inside PostgreSQL
the queries take: one page 0.2 ms, the total of the whole visible bank 38 ms (it reads every row; it
grows with the bank), a filtered total 16 ms, a ranked search for "the" 49 ms. The rest of each request
is the Python process (checking the session, building the rows). Running more API processes is part of
M7 (hosting), and this test is the one to repeat then.

### The duplicate check (4g-1, migration 0032)

Measured in PostgreSQL on the same 100,000 questions, after `qbank reindex-bank` filled the new columns
(834 s, a little longer than before because each row now also gets its duplicate key and match text):

| Query | Time |
|---|---|
| Exact duplicates (same key, through `bank_index_duplicate_key`) | 0.06 ms |
| Near duplicates of an English question (trigram similarity 0.75 or more, through `bank_index_match_trgm`) | 270 ms |
| Near duplicates of a Hindi question | 58 ms |

The near check runs only when someone opens Possible duplicates, so a quarter of a second is fine; it is
under the same 5-second limit as search. The synthetic bank has 48 pairs of exact duplicates (random
combinations that happened to repeat), which the check finds.

### Indexes kept

The starting indexes of migration 0029 are the ones the database uses and are kept: the listing order
(`bank_index_listing`, the page in 0.2 ms), the syllabus (`bank_index_syllabus`, filtered totals),
the concepts (GIN), the code (unique). Search uses the word index on `search_vector` (0030), and typo
search uses the trigram index on `bank_words` (0031). The trigram index on the full text
(`bank_index_stem_trgm`, 49 MB here) is no longer used by search; 4g-1 (migration 0032) replaced it
with one on `match_text`, the text without the solution, which the near-duplicate check compares (48 MB).

Sizes on this bank: `bank_index` 214 MB with its indexes (the full-text trigram index 49 MB, the word
index 15 MB); `question_revisions` 405 MB.

## When to run it again

- after a change to the bank queries, the index or the search (the numbers above are the baseline);
- before M7, on the hosted machine, with more than one API process;
- if someone reports the bank as slow: compare with the table above first.
