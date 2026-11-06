import { describe, expect, it } from "vitest";

import { insertInlineEquation } from "../src/lib/inline-equation";

// String.raw keeps the backslashes: `\(` in an ordinary string is just `(`.
const eq = (before: string, latex: string, after: string) =>
  String.raw`${before}\(${latex}\)${after}`;

describe("insertInlineEquation", () => {
  it("puts the equation between the inline delimiters at the cursor", () => {
    expect(insertInlineEquation("Find  now", "x^2", 5, 5)).toBe(eq("Find ", "x^2", " now"));
    expect(eq("a", "b", "c")).toContain("\\(b\\)");
  });

  it("replaces the selected text", () => {
    expect(insertInlineEquation("Find X now", "x^2", 5, 6)).toBe(eq("Find ", "x^2", " now"));
  });

  it("works at the start and at the end", () => {
    expect(insertInlineEquation("tail", "a", 0, 0)).toBe(eq("", "a", "tail"));
    expect(insertInlineEquation("head", "a", 4, 4)).toBe(eq("head", "a", ""));
    expect(insertInlineEquation("", "a", 0, 0)).toBe(eq("", "a", ""));
  });

  it("keeps a cursor past the end, or a backwards selection, inside the text", () => {
    expect(insertInlineEquation("abc", "z", 99, 99)).toBe(eq("abc", "z", ""));
    expect(insertInlineEquation("abcdef", "z", 4, 2)).toBe(eq("ab", "z", "ef"));
  });

  it("trims the equation", () => {
    expect(insertInlineEquation("ab", "  z ", 1, 1)).toBe(eq("a", "z", "b"));
  });

  it("leaves the text alone when the equation is empty", () => {
    expect(insertInlineEquation("abc", "  ", 1, 1)).toBe("abc");
  });

  it("refuses LaTeX that would close the inline equation early", () => {
    expect(insertInlineEquation("abc", String.raw`a\)b`, 1, 1)).toBe("abc");
  });
});
