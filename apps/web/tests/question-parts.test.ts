import { describe, expect, it } from "vitest";

import { emptyContent, optionsOf, setCorrect } from "../src/lib/question-content";
import {
  MAX_ITEMS,
  MIN_ITEMS,
  addItem,
  itemsOf,
  mappingOf,
  removeItem,
  rightsOf,
  setItemContent,
  setMapping,
} from "../src/lib/question-parts";

const text = (value: string) => [{ kind: "paragraph", text: value }];

describe("itemsOf", () => {
  it("reads the items of a field, leaving out anything that is not an item", () => {
    const content = { left: [{ id: "L1", content: text("x") }, "junk", { content: [] }, null] };
    expect(itemsOf(content, "left")).toEqual([{ id: "L1", content: text("x") }]);
    expect(itemsOf({}, "left")).toEqual([]);
    expect(itemsOf({ left: "x" }, "left")).toEqual([]);
  });
});

describe("addItem", () => {
  it("adds an empty item with the next free id", () => {
    const next = itemsOf(
      addItem(emptyContent("MULTIPLE_STATEMENT"), "statements", "S"),
      "statements",
    );
    expect(next.map((item) => item.id)).toEqual(["S1", "S2", "S3"]);
    expect(next[2]?.content).toEqual(text(""));
  });

  it("never reuses an id that is used anywhere in the question, even by a removed gap", () => {
    // S2 was removed: S1 and S3 remain, the next one is S2 again, then S4.
    let content = emptyContent("MULTIPLE_STATEMENT");
    content = addItem(content, "statements", "S"); // S3
    content = removeItem(content, "statements", "S2");
    content = addItem(content, "statements", "S");
    expect(itemsOf(content, "statements").map((item) => item.id)).toEqual(["S1", "S3", "S2"]);
  });

  it("skips an id already taken by an option or another list (ids are unique across the question)", () => {
    const content = { ...emptyContent("MULTIPLE_STATEMENT"), options: [{ id: "S3", content: [] }] };
    const next = itemsOf(addItem(content, "statements", "S"), "statements");
    expect(next.map((item) => item.id)).toEqual(["S1", "S2", "S4"]);
  });

  it("stops at the most items allowed", () => {
    let content = emptyContent("MULTIPLE_STATEMENT");
    for (let i = 0; i < 20; i += 1) content = addItem(content, "statements", "S");
    expect(itemsOf(content, "statements")).toHaveLength(MAX_ITEMS);
    expect(addItem(content, "statements", "S")).toBe(content);
  });

  it("does not change the content it was given", () => {
    const before = emptyContent("MATCHING");
    const copy = JSON.stringify(before);
    addItem(before, "left", "L");
    expect(JSON.stringify(before)).toBe(copy);
  });
});

describe("removeItem", () => {
  it("keeps at least the fewest items a question needs", () => {
    const content = emptyContent("MULTIPLE_STATEMENT");
    expect(itemsOf(content, "statements")).toHaveLength(MIN_ITEMS);
    expect(removeItem(content, "statements", "S1")).toBe(content);
  });

  it("removing a left item takes it out of every option's mapping", () => {
    let content = addItem(emptyContent("MATCHING"), "left", "L"); // L1 L2 L3
    content = setMapping(content, "A", "L1", "R1", true);
    content = setMapping(content, "A", "L3", "R2", true);
    content = setMapping(content, "B", "L3", "R1", true);
    const next = removeItem(content, "left", "L3");
    expect(itemsOf(next, "left").map((item) => item.id)).toEqual(["L1", "L2"]);
    expect(mappingOf(next, "A")).toEqual({ L1: ["R1"] });
    expect(mappingOf(next, "B")).toEqual({});
  });

  it("removing a right item takes it out of every mapping, and an empty list goes", () => {
    let content = addItem(emptyContent("MATCHING"), "right", "R"); // R1 R2 R3
    content = setMapping(content, "A", "L1", "R3", true);
    content = setMapping(content, "A", "L2", "R1", true);
    content = setMapping(content, "A", "L2", "R3", true);
    const next = removeItem(content, "right", "R3");
    expect(mappingOf(next, "A")).toEqual({ L2: ["R1"] });
  });

  it("an id that is not in the list changes nothing", () => {
    const content = addItem(emptyContent("MULTIPLE_STATEMENT"), "statements", "S");
    expect(removeItem(content, "statements", "S9")).toBe(content);
  });
});

describe("setItemContent", () => {
  it("sets the blocks of one item, found by its id", () => {
    const next = setItemContent(emptyContent("MATCHING"), "right", "R2", text("two"));
    expect(itemsOf(next, "right").map((item) => item.content)).toEqual([text(""), text("two")]);
  });

  it("an unknown id changes nothing", () => {
    const content = emptyContent("MATCHING");
    expect(setItemContent(content, "right", "R9", text("x"))).toBe(content);
  });
});

describe("setMapping", () => {
  it("adds a right item to a left item of an option, in the order of the right list", () => {
    let content = emptyContent("MATCHING");
    content = setMapping(content, "B", "L1", "R2", true);
    content = setMapping(content, "B", "L1", "R1", true);
    expect(mappingOf(content, "B")).toEqual({ L1: ["R1", "R2"] });
  });

  it("removes it again, and the left item's entry goes when nothing is left", () => {
    let content = setMapping(emptyContent("MATCHING"), "B", "L1", "R2", true);
    content = setMapping(content, "B", "L1", "R2", false);
    expect(mappingOf(content, "B")).toEqual({});
  });

  it("leaves the other options alone", () => {
    const content = setMapping(emptyContent("MATCHING"), "B", "L1", "R1", true);
    expect(mappingOf(content, "A")).toEqual({});
  });

  it("an option, a left item or a right item that does not exist changes nothing", () => {
    const content = emptyContent("MATCHING");
    expect(setMapping(content, "Z", "L1", "R1", true)).toBe(content);
    expect(setMapping(content, "A", "L9", "R1", true)).toBe(content);
    expect(setMapping(content, "A", "L1", "R9", true)).toBe(content);
  });

  it("marking an option correct works for a matching question too", () => {
    const content = setCorrect(emptyContent("MATCHING"), "C", true);
    expect(content.answer).toEqual({ option_id: "C" });
    expect(optionsOf(content).map((option) => option.id)).toEqual(["A", "B", "C", "D"]);
  });
});

describe("mappingOf", () => {
  it("is empty for a missing or broken mapping", () => {
    expect(mappingOf({}, "A")).toEqual({});
    expect(mappingOf({ options: [{ id: "A", mapping: "x" }] }, "A")).toEqual({});
    expect(
      mappingOf({ options: [{ id: "A", mapping: { L1: "R1", L2: ["R1", 3] } }] }, "A"),
    ).toEqual({ L2: ["R1"] });
  });
});

describe("ids that are also names on every object", () => {
  // The server accepts any id of letters, digits, "_" and "-", so these can really be saved.
  const odd = (leftId: string) => ({
    question_type: "MATCHING",
    left: [
      { id: leftId, content: [] },
      { id: "L2", content: [] },
    ],
    right: [
      { id: "R1", content: [] },
      { id: "R2", content: [] },
    ],
    options: [{ id: "A", mapping: {} }],
  });

  it.each(["constructor", "toString", "__proto__", "hasOwnProperty"])(
    "%s as a left id reads as nothing matched, not as an inherited property",
    (leftId) => {
      const content = odd(leftId);
      expect(rightsOf(mappingOf(content, "A"), leftId)).toEqual([]);
    },
  );

  it.each(["constructor", "toString", "__proto__", "hasOwnProperty"])(
    "%s can be matched and unmatched like any other id",
    (leftId) => {
      const on = setMapping(odd(leftId), "A", leftId, "R2", true);
      expect(rightsOf(mappingOf(on, "A"), leftId)).toEqual(["R2"]);
      expect(Object.keys(mappingOf(on, "A"))).toEqual([leftId]);
      const off = setMapping(on, "A", leftId, "R2", false);
      expect(rightsOf(mappingOf(off, "A"), leftId)).toEqual([]);
      expect(Object.keys(mappingOf(off, "A"))).toEqual([]);
    },
  );

  it("removing such an item leaves the other mappings", () => {
    let content = setMapping(odd("constructor"), "A", "constructor", "R1", true);
    content = setMapping(content, "A", "L2", "R2", true);
    const next = removeItem(addItem(content, "left", "L"), "left", "constructor");
    expect(Object.keys(mappingOf(next, "A"))).toEqual(["L2"]);
  });
});
