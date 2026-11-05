import { describe, expect, it } from "vitest";

import {
  FORMATS,
  blocksOf,
  correctIds,
  emptyContent,
  formatLabel,
  optionsOf,
  paragraph,
  removeBlock,
  replaceBlock,
  setCorrect,
  setOptionContent,
  withField,
} from "../src/lib/question-content";

describe("emptyContent", () => {
  it("starts every format with schema version 1, its type, a language and an empty stem", () => {
    for (const { value } of FORMATS) {
      const content = emptyContent(value);
      expect(content.schema_version).toBe(1);
      expect(content.question_type).toBe(value);
      expect(content.language).toBe("en");
      expect(content.stem).toEqual([{ kind: "paragraph", text: "" }]);
      expect(content).not.toHaveProperty("answer"); // nothing is chosen for the author
    }
  });

  it("gives the formats with options four of them, labelled A to D", () => {
    for (const type of ["SCQ", "MULTI_CORRECT", "ASSERTION_REASON", "MULTIPLE_STATEMENT"]) {
      const options = emptyContent(type).options as { id: string }[];
      expect(options.map((o) => o.id)).toEqual(["A", "B", "C", "D"]);
    }
  });

  it("gives matching two items a side and four options with empty mappings", () => {
    const content = emptyContent("MATCHING");
    expect((content.left as unknown[]).length).toBe(2);
    expect((content.right as unknown[]).length).toBe(2);
    expect(content.options).toEqual(["A", "B", "C", "D"].map((id) => ({ id, mapping: {} })));
  });

  it("keeps ids different across the parts of one question", () => {
    const content = emptyContent("MATCHING");
    const ids = [content.left, content.right, content.options]
      .flatMap((part) => part as { id: string }[])
      .map((item) => item.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("gives typed-answer formats nothing besides the stem", () => {
    for (const type of ["INTEGER", "SINGLE_DIGIT", "NUMERICAL"]) {
      expect(Object.keys(emptyContent(type)).sort()).toEqual([
        "language",
        "question_type",
        "schema_version",
        "stem",
      ]);
    }
  });

  it("gives each content its own lists, never shared", () => {
    const a = emptyContent("SCQ");
    const b = emptyContent("SCQ");
    (a.stem as unknown[]).push(paragraph("x"));
    expect(b.stem).toHaveLength(1);
  });
});

describe("block helpers", () => {
  const blocks = [paragraph("a"), paragraph("b"), paragraph("c")];

  it("replace one block without changing the original", () => {
    const changed = replaceBlock(blocks, 1, paragraph("B"));
    expect(changed.map((b) => b.text)).toEqual(["a", "B", "c"]);
    expect(blocks.map((b) => b.text)).toEqual(["a", "b", "c"]);
  });

  it("leave the list alone when the index is outside it", () => {
    expect(replaceBlock(blocks, 3, paragraph("x"))).toBe(blocks);
    expect(replaceBlock(blocks, -1, paragraph("x"))).toBe(blocks);
  });

  it("remove one block", () => {
    expect(removeBlock(blocks, 0).map((b) => b.text)).toEqual(["b", "c"]);
    expect(removeBlock(blocks, 9)).toHaveLength(3);
  });

  it("read a field as blocks, whatever it holds", () => {
    expect(blocksOf(blocks)).toHaveLength(3);
    for (const junk of [undefined, null, "x", 5, {}, [1, "a", null, [2]]]) {
      expect(blocksOf(junk)).toEqual([]);
    }
  });

  it("set a field on a copy of the content", () => {
    const content = emptyContent("SCQ");
    const changed = withField(content, "language", "hi");
    expect(changed.language).toBe("hi");
    expect(content.language).toBe("en");
  });

  it("name the formats, and an unknown one plainly", () => {
    expect(formatLabel("SCQ")).toBe("Single correct");
    expect(formatLabel("NOPE")).toBe("Unknown format");
    expect(formatLabel(undefined)).toBe("Unknown format");
  });
});

describe("options and the answer", () => {
  const scq = () => emptyContent("SCQ");
  const multi = () => emptyContent("MULTI_CORRECT");

  it("reads the options of a content, leaving out anything that is not one", () => {
    expect(optionsOf(scq()).map((o) => o.id)).toEqual(["A", "B", "C", "D"]);
    expect(optionsOf({ options: [null, 3, {}, { id: 5 }, { id: "X", content: "no" }] })).toEqual([
      { id: "X", content: [] },
    ]);
    expect(optionsOf({})).toEqual([]);
  });

  it("changes one option's blocks and nothing else", () => {
    const content = scq();
    const changed = setOptionContent(content, 1, [paragraph("two")]);
    expect(optionsOf(changed).map((o) => o.content.length)).toEqual([1, 1, 1, 1]);
    expect(optionsOf(changed)[1]?.content[0]?.text).toBe("two");
    expect(optionsOf(content)[1]?.content[0]?.text).toBe("");
    expect(setOptionContent(content, 9, [])).toBe(content);
  });

  it("marks one option correct in a single-correct question, replacing the earlier one", () => {
    const first = setCorrect(scq(), "B", true);
    expect(first.answer).toEqual({ option_id: "B" });
    const second = setCorrect(first, "C", true);
    expect(second.answer).toEqual({ option_id: "C" });
    expect(correctIds(second)).toEqual(["C"]);
  });

  it("removes the answer when the marked option is unmarked, and ignores unmarking another", () => {
    const marked = setCorrect(scq(), "B", true);
    expect(marked).not.toBe(setCorrect(marked, "B", false));
    expect(setCorrect(marked, "B", false)).not.toHaveProperty("answer");
    expect(setCorrect(marked, "D", false)).toBe(marked);
  });

  it("marks several in a multiple-correct question, in the order of the options", () => {
    let content = setCorrect(multi(), "C", true);
    content = setCorrect(content, "A", true);
    expect(content.answer).toEqual({ option_ids: ["A", "C"] });
    content = setCorrect(content, "A", false);
    expect(content.answer).toEqual({ option_ids: ["C"] });
    content = setCorrect(content, "C", false);
    expect(content).not.toHaveProperty("answer");
  });

  it("never changes the content it was given", () => {
    const content = multi();
    const copy = JSON.stringify(content);
    setCorrect(content, "A", true);
    setCorrect(content, "Z", true);
    expect(JSON.stringify(content)).toBe(copy);
  });

  it("ignores an id that is not an option", () => {
    const content = scq();
    expect(setCorrect(content, "Z", true)).toBe(content);
  });

  it("reads the correct ids of either shape and of junk", () => {
    expect(correctIds({ answer: { option_id: "B" } })).toEqual(["B"]);
    expect(correctIds({ answer: { option_ids: ["A", 3, "C"] } })).toEqual(["A", "C"]);
    for (const junk of [undefined, null, 5, "x", [], {}, { option_ids: "A" }]) {
      expect(correctIds({ answer: junk })).toEqual([]);
    }
  });
});
