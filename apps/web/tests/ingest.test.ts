import { describe, expect, it } from "vitest";

import {
  boxStyle,
  canCancel,
  canRead,
  canRetry,
  errorText,
  isActive,
  neighbour,
  nextOpen,
  shortcutOf,
  sizeProblem,
  stateText,
  tally,
  titleOf,
  warningText,
} from "../src/lib/ingest";

describe("a file's state", () => {
  it("is in words, and a state not known is shown as still going", () => {
    expect(stateText("EXTRACTING")).toBe("Reading the questions");
    expect(stateText("SOMETHING_NEW")).toBe("In progress");
    expect(isActive("SOMETHING_NEW")).toBe(true);
  });
  it("is going until it ends", () => {
    for (const state of ["UPLOADED", "RENDERING", "EXTRACTING"]) expect(isActive(state)).toBe(true);
    for (const state of ["READY", "DONE", "PARTIAL", "FAILED", "CANCELLED"]) {
      expect(isActive(state)).toBe(false);
    }
  });
  it("says what the person may do", () => {
    expect(canCancel("RENDERING")).toBe(true);
    expect(canCancel("DONE")).toBe(false);
    expect(canRetry("FAILED")).toBe(true);
    expect(canRetry("READY")).toBe(false);
    expect(canRead("READY")).toBe(true);
    expect(canRead("EXTRACTING")).toBe(false);
    expect(canRead("UPLOADED")).toBe(false);
  });
});

describe("failures in words", () => {
  it("never shows a bare code", () => {
    expect(errorText("TOO_SLOW")).toContain("try again");
    expect(errorText("AI_PROVIDER_TIMEOUT")).toContain("did not answer well");
    expect(errorText("SOMETHING_ODD")).toBe(
      "Something went wrong with this document. You can try again.",
    );
    expect(errorText(null)).toBeNull();
    expect(warningText("OVERPRECISE_ANSWER")).toContain("not rounded");
    expect(warningText("NEW_ONE")).toBe("Check this carefully");
  });
});

describe("a candidate's title", () => {
  it("is the first line of its question", () => {
    expect(titleOf({ stem: [{ kind: "paragraph", text: "  What is 2 + 3?  " }] })).toBe(
      "What is 2 + 3?",
    );
    expect(titleOf({ stem: [{ kind: "equation" }, { text: "second" }] })).toBe("second");
    expect(titleOf({})).toBe("(no text)");
    expect(titleOf({ stem: "x".repeat(10) })).toBe("(no text)");
    expect(titleOf({ stem: [{ text: "y".repeat(500) }] })).toHaveLength(120);
  });
});

describe("what can be picked", () => {
  it("is held to the limit of its kind", () => {
    expect(sizeProblem({ name: "a.pdf", size: 49 * 1024 * 1024 })).toBeNull();
    expect(sizeProblem({ name: "a.pdf", size: 51 * 1024 * 1024 })).toContain("50 MB");
    expect(sizeProblem({ name: "a.JPG", size: 11 * 1024 * 1024 })).toContain("10 MB");
    expect(sizeProblem({ name: "a.pdf", size: 0 })).toBe("The file is empty.");
  });
});

describe("the review list", () => {
  const list = [
    { id: "a", state: "NEW" as const },
    { id: "b", state: "ACCEPTED" as const },
    { id: "c", state: "NEW" as const },
  ];
  it("counts candidates by state", () => {
    expect(tally(list)).toEqual({ NEW: 2, ACCEPTED: 1, REJECTED: 0, DUPLICATE: 0 });
  });
  it("moves by one and stays at the ends", () => {
    expect(neighbour(list, "a", 1)).toBe("b");
    expect(neighbour(list, "c", 1)).toBe("c");
    expect(neighbour(list, "a", -1)).toBe("a");
    expect(neighbour(list, null, 1)).toBe("a");
    expect(neighbour([], null, 1)).toBeNull();
  });
  it("finds the next one still open, wrapping round", () => {
    expect(nextOpen(list, "a")).toBe("c");
    expect(nextOpen(list, "c")).toBe("a");
    expect(nextOpen([{ id: "x", state: "ACCEPTED" as const }], "x")).toBeNull();
    expect(nextOpen([], null)).toBeNull();
  });
});

describe("keyboard shortcuts", () => {
  const press = (key: string, extra: object = {}) => shortcutOf({ key, ...extra });
  it("work on the screen", () => {
    expect(press("j")).toBe("next");
    expect(press("ArrowUp")).toBe("previous");
    expect(press("a")).toBe("accept");
    expect(press("r")).toBe("reject");
    expect(press("s")).toBe("same");
    expect(press("n")).toBe("next-open");
    expect(press("x")).toBeNull();
  });
  it("never fire while typing or with a modifier", () => {
    expect(press("a", { target: { tagName: "TEXTAREA" } })).toBeNull();
    expect(press("a", { target: { tagName: "input" } })).toBeNull();
    expect(press("a", { target: { tagName: "DIV", isContentEditable: true } })).toBeNull();
    expect(press("a", { ctrlKey: true })).toBeNull();
    expect(press("a", { metaKey: true })).toBeNull();
    expect(press("a", { target: { tagName: "BUTTON" } })).toBe("accept");
  });
});

describe("a region on the page", () => {
  it("becomes percentages inside the page", () => {
    expect(boxStyle({ x: 0.1, y: 0.2, w: 0.5, h: 0.25 })).toEqual({
      left: "10%",
      top: "20%",
      width: "50%",
      height: "25%",
    });
  });
  it("is cut at the page edge and ignored when it is not a box", () => {
    expect(boxStyle({ x: 0.8, y: 0, w: 0.5, h: 1 })?.width).toBe("20%");
    expect(boxStyle(null)).toBeNull();
    expect(boxStyle({ x: 0, y: 0, w: 0, h: 1 })).toBeNull();
    expect(boxStyle({ x: "a" as unknown as number, y: 0, w: 1, h: 1 })).toBeNull();
  });
});
