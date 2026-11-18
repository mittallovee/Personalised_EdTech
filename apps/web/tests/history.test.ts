import { describe, expect, it } from "vitest";

import {
  actorText,
  comparable,
  defaultPair,
  entryText,
  opText,
  pathText,
  reasonTexts,
  segmentsOf,
  valueText,
  type Change,
  type HistoryEntry,
} from "../src/lib/history";

function entry(change: Partial<HistoryEntry>): HistoryEntry {
  return {
    kind: "CHECKPOINT",
    at: "2026-11-17T10:00:00Z",
    actor_id: "me",
    version_number: 1,
    revision_id: null,
    reasons: [],
    note: null,
    ...change,
  };
}

describe("the history", () => {
  it("says who did it: you, a colleague, or someone when it is not known", () => {
    expect(actorText("me", "me")).toBe("you");
    expect(actorText("other", "me")).toBe("a colleague");
    expect(actorText(null, "me")).toBe("someone");
  });

  it("words each entry with its version", () => {
    expect(entryText(entry({ kind: "SUBMIT" }), "me")).toBe(
      "Submitted for review by you · version 1",
    );
    expect(entryText(entry({ kind: "ARCHIVED", version_number: null, actor_id: "x" }), "me")).toBe(
      "Archived by a colleague",
    );
  });

  it("names the reasons of a return, and keeps a code it does not know", () => {
    expect(reasonTexts(["ANSWER_WRONG"])).toEqual([
      "The answer is wrong or does not match the question",
    ]);
    expect(reasonTexts(["SOMETHING_NEW"])).toEqual(["Something new"]);
  });
});

describe("the texts that can be compared", () => {
  const entries = [
    entry({ kind: "CREATED" }),
    entry({ kind: "SUBMIT", revision_id: "a", at: "2026-11-17T11:00:00Z" }),
    entry({ kind: "RETURN" }),
    entry({ kind: "CHECKPOINT", revision_id: "b", at: "2026-11-17T12:00:00Z" }),
    entry({ kind: "PUBLISH", revision_id: "b", at: "2026-11-17T13:00:00Z", version_number: 2 }),
  ];

  it("lists each saved text once, oldest first, from the entries that name one", () => {
    const choices = comparable(entries);
    expect(choices.map((c) => c.id)).toEqual(["a", "b"]);
    expect(choices[0]!.label).toMatch(/^Version 1: Submitted for review, /);
    expect(choices[1]!.label).toMatch(/^Version 1: Saved a checkpoint, /);
  });

  it("starts with the two newest, older first, and has none to offer below two", () => {
    expect(defaultPair(comparable(entries))).toEqual({ from: "a", to: "b" });
    expect(defaultPair(comparable(entries.slice(0, 2)))).toBeNull();
    expect(defaultPair([])).toBeNull();
  });
});

describe("a change", () => {
  it("says where it is, in words", () => {
    expect(pathText([])).toBe("The whole question");
    expect(pathText(["stem", 0, "text"])).toBe("Question › 1 › Text");
    expect(pathText(["options", 2])).toBe("Options › 3");
    expect(pathText(["question_type"])).toBe("Format");
    expect(pathText(["something_else"])).toBe("Something else");
  });

  it("words what it did", () => {
    expect(opText("add")).toBe("Added");
    expect(opText("remove")).toBe("Removed");
    expect(opText("replace")).toBe("Changed");
  });

  it("shows values as text, shortened, and a missing value as a dash", () => {
    expect(valueText("plain")).toBe("plain");
    expect(valueText(null)).toBe("—");
    expect(valueText(undefined)).toBe("—");
    expect(valueText("")).toBe("(empty)");
    expect(valueText({ kind: "equation", latex: "x^2" })).toBe('{"kind":"equation","latex":"x^2"}');
    expect(valueText("a".repeat(500))).toBe(`${"a".repeat(400)}…`);
  });

  it("has marks only when the API gave some", () => {
    const base: Change = { op: "replace", path: ["stem"], before: "a", after: "b" };
    expect(segmentsOf(base)).toBeNull();
    expect(segmentsOf({ ...base, segments: [] })).toBeNull();
    const marked = { ...base, segments: [{ kind: "insert" as const, text: "b" }] };
    expect(segmentsOf(marked)).toEqual([{ kind: "insert", text: "b" }]);
  });
});
