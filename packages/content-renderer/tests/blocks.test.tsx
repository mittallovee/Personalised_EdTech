import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Blocks, MAX_BLOCKS } from "../src/blocks";

const ID = "00000000-0000-4000-8000-000000000abc";
const html = (blocks: unknown, props: Partial<Parameters<typeof Blocks>[0]> = {}) =>
  renderToStaticMarkup(<Blocks blocks={blocks} {...props} />);
const p = (text: string) => ({ kind: "paragraph", text });

describe("paragraphs", () => {
  it("writes text as text, never as markup", () => {
    const out = html([p("<script>alert(1)</script> & <b>bold</b>")]);
    expect(out).toContain("&lt;script&gt;alert(1)&lt;/script&gt; &amp; &lt;b&gt;bold&lt;/b&gt;");
    expect(out).not.toContain("<script");
    expect(out).not.toContain("<b>");
  });

  it("typesets inline equations inside a sentence", () => {
    const out = html([p("a body of mass \\(m\\) moves")]);
    expect(out).toContain("a body of mass ");
    expect(out).toContain("katex");
    expect(out).toContain(" moves");
  });

  it("renders nothing for a blank paragraph", () => {
    expect(html([p("   ")])).toBe("");
  });

  it("does not render a paragraph longer than the limit", () => {
    const out = html([p("x".repeat(10_001))]);
    expect(out).not.toContain("xxxx");
    expect(out).toContain("too long");
  });
});

describe("equations", () => {
  it("typesets a displayed equation", () => {
    const out = html([{ kind: "equation", format: "latex", source: "E = mc^2" }]);
    expect(out).toContain("katex-display");
  });

  it("only understands latex, and says so for anything else", () => {
    const out = html([{ kind: "equation", format: "mathml", source: "<math></math>" }]);
    expect(out).not.toContain("<math");
    expect(out).toContain("unsupported");
  });

  it("shows a broken equation's source instead of failing", () => {
    expect(html([{ kind: "equation", format: "latex", source: "\\frac{1" }])).toContain(
      "katex-error",
    );
  });
});

describe("images", () => {
  const image = (extra: object = {}) => ({
    kind: "image",
    asset_id: ID,
    alt_text: "A ball on a slope",
    ...extra,
  });

  it("points at the authorised asset endpoint and carries the alt text and caption", () => {
    const out = html([image({ caption: "Figure 1" })]);
    expect(out).toContain(`src="/api/v1/assets/${ID}/content"`);
    expect(out).toContain('alt="A ball on a slope"');
    expect(out).toContain("<figcaption>Figure 1</figcaption>");
  });

  it("lets the host choose the address", () => {
    expect(html([image()], { assetUrl: (id) => `/files/${id}` })).toContain(`src="/files/${ID}"`);
  });

  it("builds an address only from a real id, so no id can inject anything", () => {
    for (const bad of ['x" onerror="alert(1)', "javascript:alert(1)", "../../etc", "", 5, null]) {
      const out = html([image({ asset_id: bad })]);
      expect(out).not.toContain("<img");
      expect(out).not.toContain("onerror");
      expect(out).toContain("unavailable");
    }
  });

  it("escapes the alt text", () => {
    const out = html([image({ alt_text: '"><script>alert(1)</script>' })]);
    expect(out).not.toContain("<script");
  });
});

describe("tables and lists", () => {
  it("renders rows of cells made of text and equations", () => {
    const rows = [
      [[p("a")], [p("b \\(x\\)")]],
      [[p("c")], [p("d")]],
    ];
    const out = html([{ kind: "table", rows }]);
    expect(out.match(/<tr>/g)).toHaveLength(2);
    expect(out.match(/<td>/g)).toHaveLength(4);
    expect(out).toContain("katex");
  });

  it("renders ordered and unordered lists", () => {
    const items = [[p("one")], [p("two")]];
    expect(html([{ kind: "list", ordered: true, items }])).toMatch(/^<ol>.*<\/ol>$/);
    expect(html([{ kind: "list", ordered: false, items }])).toMatch(/^<ul>.*<\/ul>$/);
  });

  it("allows only text and equations inside a cell or an item", () => {
    const nested = { kind: "table", rows: [[[p("a")]]] };
    const out = html([{ kind: "list", ordered: false, items: [[nested]] }]);
    expect(out).toContain("unsupported");
    expect(out).not.toContain("<table");
  });

  it("stops at the size limits", () => {
    const wide = [Array.from({ length: 13 }, () => [p("c")])];
    expect(html([{ kind: "table", rows: wide }])).toContain("too large");
    const tall = Array.from({ length: 51 }, () => [[p("c")]]);
    expect(html([{ kind: "table", rows: tall }])).toContain("too large");
    const items = Array.from({ length: 51 }, () => [p("i")]);
    expect(html([{ kind: "list", ordered: false, items }])).toContain("too large");
  });
});

describe("anything unexpected", () => {
  it("renders nothing for a missing or non-list value", () => {
    for (const value of [undefined, null, "text", 5, {}, true]) expect(html(value)).toBe("");
  });

  it("marks an unknown kind, a non-object or a block with the wrong fields as unsupported", () => {
    const out = html([{ kind: "video", url: "x" }, "text", null, { kind: "paragraph", text: 5 }]);
    expect(out.match(/unsupported/g)).toHaveLength(4);
  });

  it("renders only the first blocks of an enormous list", () => {
    const out = html(Array.from({ length: MAX_BLOCKS + 50 }, (_, i) => p(`para ${i}.`)));
    expect(out).toContain(`para ${MAX_BLOCKS - 1}.`);
    expect(out).not.toContain(`para ${MAX_BLOCKS}.`);
  });

  it("does not choke on deeply nested junk", () => {
    let junk: unknown = [p("x")];
    for (let i = 0; i < 5000; i++) junk = [{ kind: "list", items: [junk] }];
    expect(() => html(junk)).not.toThrow();
  });
});

describe("the one way in", () => {
  it("keeps raw HTML out of every file except the one that holds KaTeX's output", () => {
    const dir = join(__dirname, "..", "src");
    const using = readdirSync(dir).filter((file) =>
      /dangerouslySetInnerHTML|innerHTML/.test(readFileSync(join(dir, file), "utf8")),
    );
    expect(using).toEqual(["math.tsx"]);
  });
});
