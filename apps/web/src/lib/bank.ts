import type { paths } from "@qbank/api-client";

/**
 * The bank screen's filters, turned into the query the API reads (F-01, F-02, F-03). The API
 * decides what each person may see and counts the matches; this only says what was asked for.
 */

export type BankQuery = NonNullable<paths["/api/v1/bank/questions"]["get"]["parameters"]["query"]>;

export type BankFilters = {
  words: string; // free text (search)
  subject: string;
  chapter: string;
  topic: string;
  difficulty: string; // "" or "1" … "10"
  bloom: string;
  format: string;
  language: string;
  state: string;
  pyq: boolean;
  solution: boolean;
  video: boolean;
  mine: boolean;
  archived: boolean;
};

export const NO_FILTERS: BankFilters = {
  words: "",
  subject: "",
  chapter: "",
  topic: "",
  difficulty: "",
  bloom: "",
  format: "",
  language: "",
  state: "",
  pyq: false,
  solution: false,
  video: false,
  mine: false,
  archived: false,
};

export const BLOOM_LEVELS: readonly { value: string; label: string }[] = [
  { value: "REMEMBER", label: "Remember" },
  { value: "UNDERSTAND", label: "Understand" },
  { value: "APPLY", label: "Apply" },
  { value: "ANALYZE", label: "Analyse" },
  { value: "EVALUATE", label: "Evaluate" },
  { value: "CREATE", label: "Create" },
];

/** The longest search the API accepts. */
export const MAX_WORDS = 200;

/** Whether anything narrows the list (the search words included). */
export function isFiltered(filters: BankFilters): boolean {
  return (Object.keys(NO_FILTERS) as (keyof BankFilters)[]).some(
    (key) => filters[key] !== NO_FILTERS[key],
  );
}

/**
 * The query for these filters. "Only mine" is the signed-in person as the author. A search sends
 * no cursor (the API ranks and does not page it) and asks for the most it shows.
 */
export function bankQuery(filters: BankFilters, myId: string, cursor: string | null): BankQuery {
  const words = filters.words.trim().slice(0, MAX_WORDS);
  const query: BankQuery = { limit: words ? 100 : 50 };
  if (words) query.q = words;
  else if (cursor) query.cursor = cursor;
  if (filters.subject) query.subject_id = [filters.subject];
  if (filters.chapter) query.chapter_id = [filters.chapter];
  if (filters.topic) query.topic_id = [filters.topic];
  if (filters.difficulty) query.difficulty = [Number(filters.difficulty)];
  if (filters.bloom) query.bloom_level = [filters.bloom];
  if (filters.format) query.question_type = [filters.format];
  if (filters.language) query.language = [filters.language];
  if (filters.state) query.state = [filters.state];
  if (filters.mine) query.author_id = [myId];
  if (filters.pyq) query.is_pyq = true;
  if (filters.solution) query.has_solution = true;
  if (filters.video) query.has_video = true;
  if (filters.archived) query.archived = true;
  return query;
}

/** The line above the results: how many match, and for a search whether more matched. */
export function countLine(total: number, searching: boolean, truncated: boolean): string {
  const noun = total === 1 ? "question" : "questions";
  if (!searching) return `${total} ${noun}`;
  if (truncated) return `The best ${total} matches are shown. Add a word or a filter to narrow it.`;
  return total === 1 ? "1 question matches" : `${total} questions match`;
}
