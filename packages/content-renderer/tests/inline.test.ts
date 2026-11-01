import { describe, expect, it } from "vitest";
import { splitInline } from "../src/inline";

describe("splitInline", () => {
  it("keeps plain text as one text segment", () => {
    expect(splitInline("a body of mass")).toEqual([{ type: "text", text: "a body of mass" }]);
    expect(splitInline("")).toEqual([]);
  });

  it("finds inline equations between backslash-paren pairs", () => {
    expect(splitInline("mass \\(m\\) moves at \\(v = 2\\) m/s")).toEqual([
      { type: "text", text: "mass " },
      { type: "math", source: "m" },
      { type: "text", text: " moves at " },
      { type: "math", source: "v = 2" },
      { type: "text", text: " m/s" },
    ]);
  });

  it("reads a doubled backslash outside an equation as one literal backslash", () => {
    expect(splitInline("a \\\\(b\\\\) c")).toEqual([{ type: "text", text: "a \\(b\\) c" }]);
  });

  it("leaves a doubled backslash inside an equation alone: it is a LaTeX line break", () => {
    expect(splitInline("\\(a\\\\b\\)")).toEqual([{ type: "math", source: "a\\\\b" }]);
  });

  it("shows an unclosed equation as plain text instead of swallowing the rest", () => {
    expect(splitInline("x \\(y + z")).toEqual([{ type: "text", text: "x \\(y + z" }]);
  });

  it("shows a stray closing mark as plain text", () => {
    expect(splitInline("a \\) b")).toEqual([{ type: "text", text: "a \\) b" }]);
  });

  it("drops an empty equation", () => {
    expect(splitInline("a\\(\\)b\\(  \\)c")).toEqual([{ type: "text", text: "abc" }]);
  });

  it("takes everything up to the next closing mark as the source, even another opening mark", () => {
    expect(splitInline("\\(a \\( b\\)")).toEqual([{ type: "math", source: "a \\( b" }]);
  });

  it("keeps a lone trailing backslash and other backslashes as text", () => {
    expect(splitInline("abc\\")).toEqual([{ type: "text", text: "abc\\" }]);
    expect(splitInline("\\alpha is text here")).toEqual([
      { type: "text", text: "\\alpha is text here" },
    ]);
  });

  it("never treats markup as anything but text", () => {
    expect(splitInline("<b>bold</b> & <script>")).toEqual([
      { type: "text", text: "<b>bold</b> & <script>" },
    ]);
  });
});
