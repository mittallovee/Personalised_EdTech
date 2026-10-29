# Question findings

A **finding** says what is wrong with a question's content, in plain words (M3 design note §5.4). It has
a `path` (which field, like `options[2].content[0].text`), a stable `code` that clients branch on (never
the message) and a `level`:

- `error`: something supplied is malformed. A draft with errors can still be saved.
- `incomplete`: something needed for publishing is missing. A draft can still be saved.
- `warning`: allowed, but worth a look.

Findings are computed from the content each time and never stored. The code is in
`services/api/src/qbank/modules/questions/`; the limits are the defaults in `rules.py`, which an admin
will be able to change (PR 3i). A changed limit never rewrites old revisions; it only changes the findings.

Codes are stable: once published, a code keeps its meaning. This table covers what M3 PR 3a-1 checks
(the envelope, the five block kinds, and the formats SCQ, multiple correct, integer, single digit and
numerical). PR 3a-2 adds matching, assertion-reason, multiple-statement, passage context and metadata.

## The whole document

| Code | Level | Meaning |
|---|---|---|
| `CONTENT_NOT_OBJECT` / `CONTENT_NOT_JSON` | error | The content is not an object of plain data |
| `CONTENT_TOO_LARGE` | error | More than 256 KB; nothing else is checked |
| `SCHEMA_VERSION_UNSUPPORTED` | error | `schema_version` is not 1 |
| `QUESTION_TYPE_UNKNOWN` | error | Not one of the eight concrete formats |
| `FIELD_NOT_ALLOWED` | error | A field that belongs to another format (for example `options` on an integer question) |
| `LANGUAGE_MISSING` | incomplete | No language chosen |
| `LANGUAGE_INVALID` | error | Not a language code like `en` or `hi` |
| `STEM_EMPTY` | incomplete | The question has no text yet (blank paragraphs alone do not count) |
| `VIDEO_URL_INVALID` | error | The video link is not an `http(s)` address |

## Blocks

| Code | Level | Meaning |
|---|---|---|
| `BLOCKS_NOT_LIST` / `BLOCK_NOT_OBJECT` | error | Blocks must be a list of objects |
| `BLOCK_KIND_UNKNOWN` | error | Not paragraph, equation, image, table or list |
| `BLOCK_KIND_NOT_ALLOWED` | error | A kind that cannot be used here (an image inside a table cell) |
| `UNKNOWN_FIELD` | error | A field the block (or option) does not have |
| `TOO_MANY_BLOCKS` | error | More than 100 blocks in one list |
| `TEXT_NOT_STRING` | error | A text field is not text |
| `PARAGRAPH_TOO_LONG` | error | More than 10,000 characters |
| `PARAGRAPH_EMPTY` | warning | A blank paragraph |
| `INLINE_EQUATION_UNBALANCED` / `INLINE_EQUATION_NESTED` | error | `\(` and `\)` do not pair up (a literal backslash is written `\`) |
| `EQUATION_FORMAT_UNSUPPORTED` | error | Only `latex` is stored (MathML is Phase 2) |
| `EQUATION_SOURCE_NOT_STRING` | error | The equation source is not text |
| `EQUATION_EMPTY` | incomplete | An equation block with no content |
| `EQUATION_TOO_LONG` | error | More than 2,000 characters (also for an inline equation) |
| `IMAGE_ASSET_MISSING` | incomplete | No picture chosen yet |
| `IMAGE_ASSET_ID_INVALID` | error | The picture's id is not valid |
| `IMAGE_ALT_MISSING` | incomplete | No alt text (a description for people who cannot see the picture) |
| `TABLE_ROWS_NOT_LIST` / `TABLE_ROW_NOT_LIST` | error | Table shape is wrong |
| `TABLE_EMPTY` | incomplete | No rows yet |
| `TABLE_NOT_RECTANGULAR` | error | Rows have different numbers of cells |
| `TABLE_TOO_BIG` | error | More than 50 rows or 12 columns |
| `LIST_ITEMS_NOT_LIST` / `LIST_ORDERED_NOT_BOOLEAN` | error | List shape is wrong |
| `LIST_EMPTY` | incomplete | No items yet |
| `LIST_TOO_BIG` | error | More than 50 items |

## Options and answers

| Code | Level | Meaning |
|---|---|---|
| `OPTIONS_MISSING` | incomplete | No options yet (SCQ, multiple correct) |
| `OPTIONS_NOT_LIST` / `OPTION_NOT_OBJECT` | error | Options shape is wrong |
| `OPTIONS_COUNT` | incomplete (fewer) / error (more) | There must be exactly four options |
| `OPTION_ID_INVALID` / `OPTION_ID_DUPLICATE` | error | Ids are 1 to 20 letters, digits, `_` or `-`, and unique |
| `OPTION_EMPTY` | incomplete | An option with no content, or only blank paragraphs and empty equations |
| `ANSWER_MISSING` | incomplete | No answer chosen yet |
| `ANSWER_SHAPE` | error | The answer is not in the form the format needs |
| `ANSWER_FIELD_UNKNOWN` | error | A field the answer does not have |
| `ANSWER_OPTION_UNKNOWN` | error | The answer names an option that does not exist |
| `ANSWER_EMPTY` | error | Multiple correct with no option chosen (one is enough) |
| `ANSWER_OPTION_DUPLICATE` | error | The same option named twice |
| `ANSWER_NOT_INTEGER` | error | Integer / single-digit key is not a whole JSON number (a float, text or boolean) |
| `ANSWER_OUT_OF_RANGE` | error | Integer 0..999, single digit 0..9, numerical 0.00..999.00 (defaults) |
| `ANSWER_UNIT_NOT_ALLOWED` | error | A numerical answer has no unit field |
| `NUMERIC_NOT_TEXT` / `NUMERIC_FORMAT_INVALID` | error | A numerical key is written as text with exactly two decimals, like `"9.80"` |
| `NUMERIC_TOO_MANY_DECIMALS` | error | More than two decimals; the value is **kept as written, never rounded**, and blocks publishing |
| `NUMERIC_MODE_INVALID` | error | Mode must be `exact` or `range` |
| `NUMERIC_VALUE_MISSING` | incomplete | An exact value, or an end of a range, is missing |
| `NUMERIC_RANGE_REVERSED` | error | The lower end is above the upper end |
