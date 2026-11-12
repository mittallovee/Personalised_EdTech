import { describe, expect, it } from "vitest";

import { moveToCheckpoint, pinOf } from "../src/lib/passage-pin";

const ID = "6f1c2a9e-0000-4000-8000-000000000009";
const NEWER = "6f1c2a9e-0000-4000-8000-00000000000a";

describe("pinOf", () => {
  it("reads the passage checkpoint a question is written under", () => {
    expect(pinOf({ context: { passage_revision_id: ID, ordinal: 2 } })).toBe(ID);
  });

  it("is null for a question with no passage", () => {
    expect(pinOf({})).toBeNull();
    expect(pinOf({ context: null })).toBeNull();
  });

  it("is null for anything that is not the standard spelling of an id", () => {
    for (const odd of [5, null, "", "nope", ID.toUpperCase(), ID.replaceAll("-", ""), ` ${ID}`]) {
      expect(pinOf({ context: { passage_revision_id: odd } })).toBeNull();
    }
    expect(pinOf({ context: "text" })).toBeNull();
    expect(pinOf({ context: [ID] })).toBeNull();
  });
});

describe("moveToCheckpoint", () => {
  it("points the question at another checkpoint and keeps its number and everything else", () => {
    const content = {
      stem: [],
      context: { passage_revision_id: ID, ordinal: 3 },
      answer: { option_id: "A" },
    };
    expect(moveToCheckpoint(content, NEWER)).toEqual({
      stem: [],
      context: { passage_revision_id: NEWER, ordinal: 3 },
      answer: { option_id: "A" },
    });
  });

  it("does not change the content it was given", () => {
    const content = { context: { passage_revision_id: ID, ordinal: 1 } };
    moveToCheckpoint(content, NEWER);
    expect(content.context.passage_revision_id).toBe(ID);
  });

  it("starts a context when there was none", () => {
    expect(moveToCheckpoint({ stem: [] }, NEWER)).toEqual({
      stem: [],
      context: { passage_revision_id: NEWER },
    });
  });
});
