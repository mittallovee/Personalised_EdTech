import { describe, expect, it } from "vitest";
import { MAX_EQUATION_CHARS, typeset } from "../src/math";

describe("typeset", () => {
  it("typesets a valid formula", () => {
    const result = typeset("\\frac{1}{2}", false);
    expect(result.ok).toBe(true);
    expect(result.html).toContain("katex");
  });

  it("shows a broken formula's source in an error style instead of throwing", () => {
    const result = typeset("\\frac{1", false);
    expect(result.ok).toBe(false);
    expect(result.html).toContain("katex-error");
    expect(result.html).toContain("\\frac{1");
  });

  it("treats a command KaTeX does not know as an error, and still shows something", () => {
    const result = typeset("\\notacommand", false);
    expect(result.ok).toBe(false);
    expect(result.html).toContain("notacommand");
  });

  it("uses display mode only when asked", () => {
    expect(typeset("x", true).html).toContain("katex-display");
    expect(typeset("x", false).html).not.toContain("katex-display");
  });

  it("refuses a formula longer than the limit without trying to typeset it", () => {
    const result = typeset("x".repeat(MAX_EQUATION_CHARS + 1), false);
    expect(result.ok).toBe(false);
    expect(result.html).not.toContain("xxxx");
  });
});

// A small reader for the HTML KaTeX gives back, so the checks below look at real tags and
// attributes and not at text that merely mentions them (the source is kept, escaped, in a title and
// in the MathML annotation).
const TAG =
  /<\/?([a-zA-Z][\w:-]*)((?:\s+[^\s"'<>/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'<>=`]+))?)*)\s*\/?>/g;
const ATTRIBUTE = /([^\s"'<>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'<>=`]+)))?/g;
const FORBIDDEN_TAGS = new Set([
  "a",
  "script",
  "img",
  "iframe",
  "object",
  "embed",
  "form",
  "input",
  "button",
  "link",
  "style",
  "base",
  "meta",
  "video",
  "audio",
  "source",
  "template",
  "use",
  "foreignobject",
  "image",
]);
const FORBIDDEN_ATTRIBUTES = new Set(["href", "src", "srcset", "action", "formaction", "srcdoc"]);

function problems(html: string): string[] {
  const found: string[] = [];
  for (const tag of html.matchAll(TAG)) {
    const name = (tag[1] ?? "").toLowerCase();
    if (FORBIDDEN_TAGS.has(name)) found.push(`tag <${name}>`);
    for (const attribute of (tag[2] ?? "").matchAll(ATTRIBUTE)) {
      const key = (attribute[1] ?? "").toLowerCase();
      const value = attribute[2] ?? attribute[3] ?? attribute[4] ?? "";
      if (key.startsWith("on") || FORBIDDEN_ATTRIBUTES.has(key) || key.endsWith(":href")) {
        found.push(`attribute ${key}`);
      }
      if (key === "style" && /url\(|expression\(|javascript:/i.test(value)) {
        found.push("style with a link");
      }
      if ((key === "class" || key === "id") && /evil/i.test(value)) found.push(`${key}=${value}`);
      if (key.startsWith("data-")) found.push(`attribute ${key}`);
    }
  }
  // Every "<" that is left after the tags are taken out would be an unreadable or hidden tag.
  if (html.replace(TAG, "").includes("<")) found.push("a < that is not a tag");
  return found;
}

// Question text is untrusted (AI output, extracted documents), so hostile LaTeX must never become
// a link, a script, an image, a style or an attribute we did not choose (ADR-0016, AGENTS.md).
const HOSTILE = [
  "\\href{javascript:alert(1)}{click}",
  "\\url{javascript:alert(1)}",
  "\\href{https://evil.example}{click}",
  "\\htmlClass{evil}{x}",
  "\\htmlId{evil}{x}",
  "\\htmlStyle{color:red;background:url(https://evil.example/x)}{x}",
  "\\htmlData{evil=1}{x}",
  "\\includegraphics[height=1em]{https://evil.example/x.png}",
  "\\text{<img src=x onerror=alert(1)>}",
  "\\text{</span><script>alert(1)</script>}",
  "\\text{<script>alert(1)</script>",
  '\\mathrm{" onmouseover="alert(1)}',
  "\\unknowncommand{<img src=x onerror=alert(1)>}",
  '\\color{red" onclick="alert(1)}{x}',
  '\\text{"><img src=x onerror=alert(1)>}',
];

describe("typeset: hostile input", () => {
  it("the reader above does catch what it should", () => {
    expect(problems('<span><img src="x" onerror="alert(1)"></span>')).toEqual([
      "tag <img>",
      "attribute src",
      "attribute onerror",
    ]);
    expect(problems('<a href="javascript:alert(1)">x</a>')).toContain("attribute href");
    expect(problems('<span style="background:url(x)">x</span>')).toContain("style with a link");
    expect(problems("<span>1 < 2</span>")).toContain("a < that is not a tag");
  });

  it.each(HOSTILE)("neutralises %s", (source) => {
    for (const display of [false, true]) {
      expect(problems(typeset(source, display).html)).toEqual([]);
    }
  });

  it("stops a macro that expands forever", () => {
    const result = typeset("\\def\\a{\\a\\a}\\a", false);
    expect(result.ok).toBe(false);
  });

  it("does not let a huge size through", () => {
    const { html } = typeset("\\rule{99999em}{99999em}", false);
    // The source is kept in the MathML annotation; what is drawn must be clamped.
    expect(html.replace(/<annotation[\s\S]*?<\/annotation>/g, "")).not.toContain("99999");
  });

  it("does not leak a macro defined in one formula into the next", () => {
    expect(typeset("\\gdef\\q{5}\\q", false).ok).toBe(true);
    expect(typeset("\\q", false).ok).toBe(false);
  });
});
