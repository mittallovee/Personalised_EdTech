import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { QuestionPreview } from "../src/question";

const p = (text: string) => [{ kind: "paragraph", text }];
const opt = (id: string, text: string) => ({ id, content: p(text) });
const preview = (content: unknown, reveal = false) =>
  renderToStaticMarkup(<QuestionPreview content={content} reveal={reveal} />);
const text = (html: string) => html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ");

const SCQ = {
  question_type: "SCQ",
  stem: p("Which is even?"),
  options: [opt("a", "1"), opt("b", "2"), opt("c", "3"), opt("d", "5")],
  answer: { option_id: "b" },
  solution: p("Two is divisible by two."),
};

describe("single and multiple correct", () => {
  it("shows the stem and the options labelled A to D, in order", () => {
    const out = preview(SCQ);
    expect(out).toContain("Which is even?");
    expect(text(out)).toMatch(/A\s+1\s+B\s+2\s+C\s+3\s+D\s+5/);
  });

  it("gives nothing away until the answer is revealed", () => {
    const out = preview(SCQ);
    expect(out).not.toContain("qb-correct");
    expect(out).not.toContain("data-correct");
    expect(out).not.toContain("Two is divisible");
    expect(text(out)).not.toMatch(/correct/i);
    expect(out).not.toContain("Solution");
  });

  it("marks the correct option and shows the solution when revealed", () => {
    const out = preview(SCQ, true);
    expect(out.match(/data-correct="true"/g)).toHaveLength(1);
    expect(text(out)).toMatch(/B\s+2\s+Correct answer/);
    expect(out).toContain("Two is divisible by two.");
  });

  it("marks every correct option of a multiple-correct question", () => {
    const content = { ...SCQ, question_type: "MULTI_CORRECT", answer: { option_ids: ["a", "c"] } };
    expect(preview(content, true).match(/data-correct="true"/g)).toHaveLength(2);
    expect(preview(content)).not.toContain("data-correct");
  });

  it("labels options by position, whatever their ids are", () => {
    const content = {
      ...SCQ,
      options: [opt("x1", "p"), opt("x2", "q")],
      answer: { option_id: "x2" },
    };
    expect(text(preview(content, true))).toMatch(/A\s+p\s+B\s+q\s+Correct answer/);
  });
});

describe("assertion-reason and multiple statement", () => {
  it("shows the assertion and the reason before the options", () => {
    const content = {
      question_type: "ASSERTION_REASON",
      stem: p("Read both."),
      assertion: p("2 is even."),
      reason: p("2 is divisible by 2."),
      options: [opt("a", "Both true"), opt("b", "Both false")],
      answer: { option_id: "a" },
    };
    const t = text(preview(content));
    expect(t).toMatch(/Assertion.*2 is even\..*Reason.*2 is divisible by 2\..*A\s+Both true/);
  });

  it("numbers the statements", () => {
    const content = {
      question_type: "MULTIPLE_STATEMENT",
      stem: p("Which are true?"),
      statements: [
        { id: "s1", content: p("2 is prime.") },
        { id: "s2", content: p("4 is prime.") },
      ],
      options: [opt("a", "S1 only"), opt("b", "S2 only")],
      answer: { option_id: "a" },
    };
    expect(text(preview(content))).toMatch(/Statement 1.*2 is prime\..*Statement 2.*4 is prime\./);
  });
});

describe("matching", () => {
  const matching = {
    question_type: "MATCHING",
    stem: p("Match the lists."),
    left: [
      { id: "L1", content: p("1 + 1") },
      { id: "L2", content: p("1 + 2") },
    ],
    right: [
      { id: "R1", content: p("2") },
      { id: "R2", content: p("3") },
      { id: "R3", content: p("2.0") },
    ],
    options: [
      { id: "A", mapping: { L1: ["R1", "R3"], L2: ["R2"] } },
      { id: "B", mapping: { L1: ["R2"], L2: ["R1"] } },
    ],
    answer: { option_id: "A" },
  };

  it("shows the two lists, left by letter and right by number, and each option as its mapping", () => {
    const t = text(preview(matching));
    expect(t).toMatch(/P\s+1 \+ 1\s+Q\s+1 \+ 2/);
    expect(t).toMatch(/1\s+2\s+2\s+3\s+3\s+2\.0/);
    expect(t).toMatch(/A\s+P → 1, 3\s*;?\s*Q → 2/);
    expect(t).toMatch(/B\s+P → 2\s*;?\s*Q → 1/);
  });

  it("marks the correct mapping only when revealed", () => {
    expect(preview(matching)).not.toContain("data-correct");
    expect(preview(matching, true).match(/data-correct="true"/g)).toHaveLength(1);
  });

  it("ignores a mapping that names an item that is not there", () => {
    const content = { ...matching, options: [{ id: "A", mapping: { L1: ["R9"], L7: ["R1"] } }] };
    expect(() => preview(content)).not.toThrow();
    expect(text(preview(content))).not.toContain("R9");
  });
});

describe("answers typed in", () => {
  it("shows an empty answer box for an integer, a digit and a numerical question", () => {
    for (const type of ["INTEGER", "SINGLE_DIGIT", "NUMERICAL"]) {
      const out = preview({ question_type: type, stem: p("Enter it."), answer: { value: 3 } });
      expect(out).toContain("<input");
      expect(out).toContain("disabled");
      expect(out).not.toContain('value="3"');
    }
  });

  it("reveals the number, the exact value or the range", () => {
    const base = { stem: p("Enter it.") };
    expect(
      text(preview({ ...base, question_type: "INTEGER", answer: { value: 999 } }, true)),
    ).toContain("Answer: 999");
    expect(
      text(
        preview(
          { ...base, question_type: "NUMERICAL", answer: { mode: "exact", value: "9.81" } },
          true,
        ),
      ),
    ).toContain("Answer: 9.81");
    expect(
      text(
        preview(
          {
            ...base,
            question_type: "NUMERICAL",
            answer: { mode: "range", lower: "9.79", upper: "9.81" },
          },
          true,
        ),
      ),
    ).toContain("Answer: 9.79 to 9.81");
    expect(
      text(preview({ ...base, question_type: "INTEGER", answer: { value: 999 } })),
    ).not.toContain("999");
  });
});

describe("whatever it is given", () => {
  it("shows text as text", () => {
    const out = preview({ ...SCQ, stem: p("<script>alert(1)</script>") });
    expect(out).not.toContain("<script");
    expect(out).toContain("&lt;script&gt;");
  });

  it("never throws, and says there is nothing to show for something that is not a question", () => {
    const junk = [
      null,
      undefined,
      "x",
      5,
      [],
      {},
      { question_type: 7 },
      { question_type: "SCQ" },
      { question_type: "SCQ", options: "no", answer: 5 },
      { question_type: "MATCHING", left: 3, right: {}, options: [null, 1, { mapping: 5 }] },
      { question_type: "MULTI_CORRECT", options: [opt("a", "x")], answer: { option_ids: "a" } },
      { question_type: "NUMERICAL", answer: { mode: "range" } },
      { question_type: "SCQ", stem: 5, solution: { kind: "paragraph" } },
    ];
    for (const content of junk) {
      for (const reveal of [false, true]) expect(() => preview(content, reveal)).not.toThrow();
    }
    expect(preview(null)).toContain("nothing to preview");
  });

  it("shows the stem of a format it does not know, and says so", () => {
    const out = preview({ question_type: "ESSAY", stem: p("Discuss.") });
    expect(out).toContain("Discuss.");
    expect(out).toContain("not shown");
  });

  it("shows at most ten options", () => {
    const options = Array.from({ length: 30 }, (_, i) => opt(`o${i}`, `choice ${i}`));
    const out = preview({ ...SCQ, options, answer: { option_id: "o0" } });
    expect(out).toContain("choice 9");
    expect(out).not.toContain("choice 10");
  });
});

describe("a question under a passage", () => {
  const passage = { title: "Free fall", body: p("A stone is dropped from a tower.") };
  const withPassage = (value: unknown, reveal = false) =>
    renderToStaticMarkup(<QuestionPreview content={SCQ} passage={value} reveal={reveal} />);

  it("shows the passage above the question, with its title", () => {
    const out = withPassage(passage);
    expect(out).toContain("Free fall");
    expect(out).toContain("A stone is dropped from a tower.");
    expect(out.indexOf("A stone is dropped")).toBeLessThan(out.indexOf("Which is even?"));
    expect(out).toContain('class="qb-passage"');
  });

  it("shows nothing extra when there is no passage", () => {
    expect(preview(SCQ)).not.toContain("qb-passage");
    expect(withPassage(undefined)).not.toContain("qb-passage");
  });

  it("gives nothing away about the answer because of the passage", () => {
    const out = withPassage(passage);
    expect(out).not.toContain("data-correct");
    expect(text(out)).not.toMatch(/correct/i);
  });

  it("copes with a passage that is not what it should be", () => {
    for (const odd of [null, 5, "text", [], {}, { title: 7, body: "x" }, { body: [null, 3] }]) {
      expect(() => withPassage(odd)).not.toThrow();
    }
    expect(withPassage({ title: 7, body: "x" })).not.toContain("qb-passage");
  });

  it("draws a picture or an equation in the passage through the same safe renderer", () => {
    const out = withPassage({
      title: "T",
      body: [
        { kind: "paragraph", text: String.raw`Height \(h\) of the tower` },
        { kind: "image", asset_id: "00000000-0000-4000-8000-00000000000a", alt_text: "Tower" },
        { kind: "paragraph", text: "<script>alert(1)</script>" },
      ],
    });
    expect(out).toContain("katex");
    expect(out).toContain('alt="Tower"');
    expect(out).not.toContain("<script>");
  });
});
