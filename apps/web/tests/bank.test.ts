import { describe, expect, it } from "vitest";

import { MAX_WORDS, NO_FILTERS, bankQuery, countLine, isFiltered } from "../src/lib/bank";

describe("bankQuery", () => {
  it("asks for the newest 50 when nothing is chosen, and pages with the cursor", () => {
    expect(bankQuery(NO_FILTERS, "me", null)).toEqual({ limit: 50 });
    expect(bankQuery(NO_FILTERS, "me", "c1")).toEqual({ limit: 50, cursor: "c1" });
  });

  it("sends each chosen filter once, in the API's form", () => {
    const query = bankQuery(
      {
        ...NO_FILTERS,
        subject: "s",
        chapter: "c",
        topic: "t",
        difficulty: "7",
        bloom: "APPLY",
        format: "SCQ",
        language: "hi",
        state: "PUBLISHED",
        pyq: true,
        solution: true,
        video: true,
        mine: true,
        archived: true,
      },
      "me",
      null,
    );
    expect(query).toEqual({
      limit: 50,
      subject_id: ["s"],
      chapter_id: ["c"],
      topic_id: ["t"],
      difficulty: [7],
      bloom_level: ["APPLY"],
      question_type: ["SCQ"],
      language: ["hi"],
      state: ["PUBLISHED"],
      author_id: ["me"],
      is_pyq: true,
      has_solution: true,
      has_video: true,
      archived: true,
    });
  });

  it("searches without a cursor, trimmed and within the API's length", () => {
    const query = bankQuery({ ...NO_FILTERS, words: "  velocity  " }, "me", "c1");
    expect(query).toEqual({ limit: 100, q: "velocity" });
    expect(bankQuery({ ...NO_FILTERS, words: "x".repeat(500) }, "me", null).q).toHaveLength(
      MAX_WORDS,
    );
    expect(bankQuery({ ...NO_FILTERS, words: "   " }, "me", null)).toEqual({ limit: 50 });
  });
});

describe("isFiltered", () => {
  it("is false only for the untouched filters", () => {
    expect(isFiltered(NO_FILTERS)).toBe(false);
    expect(isFiltered({ ...NO_FILTERS, words: "a" })).toBe(true);
    expect(isFiltered({ ...NO_FILTERS, archived: true })).toBe(true);
  });
});

describe("countLine", () => {
  it("says how many match, and when a search shows only the best", () => {
    expect(countLine(1, false, false)).toBe("1 question");
    expect(countLine(1234, false, false)).toBe("1234 questions");
    expect(countLine(3, true, false)).toBe("3 questions match");
    expect(countLine(100, true, true)).toMatch(/^The best 100 matches are shown/);
  });
});
