import { describe, expect, it } from "vitest";

import { SETTINGS, formFrom, valuesFrom } from "../src/lib/answer-limits";

const BUILT_IN = {
  integer_min: 0,
  integer_max: 999,
  numeric_min: "0.00",
  numeric_max: "999.00",
};

describe("SETTINGS", () => {
  it("lists each setting once, with a kind and a label", () => {
    const names = SETTINGS.map((s) => s.name);
    expect(new Set(names).size).toBe(names.length);
    for (const setting of SETTINGS) {
      expect(["int", "decimal"]).toContain(setting.kind);
      expect(setting.label.length).toBeGreaterThan(0);
    }
    expect(names).toContain("integer_max");
    expect(names).toContain("numeric_max");
    expect(names).not.toContain("revision_bytes"); // the safety limits are not settings
  });
});

describe("formFrom", () => {
  it("shows the saved value, else the fallback, else nothing", () => {
    const form = formFrom({ integer_max: 5000 }, BUILT_IN);
    expect(form.integer_max).toBe("5000");
    expect(form.integer_min).toBe("0");
    expect(form.numeric_max).toBe("999.00");
    expect(form.digit_max).toBe("");
  });

  it("is blank everywhere when there is nothing to show", () => {
    const form = formFrom({});
    for (const setting of SETTINGS) expect(form[setting.name]).toBe("");
  });
});

describe("valuesFrom", () => {
  const blank = Object.fromEntries(SETTINGS.map((s) => [s.name, ""]));

  it("leaves out what is blank, so it keeps the value it would have had", () => {
    expect(valuesFrom({ ...blank, integer_max: "5000" })).toEqual({
      values: { integer_max: 5000 },
      problems: {},
    });
    expect(valuesFrom(blank)).toEqual({ values: {}, problems: {} });
  });

  it("leaves out a value equal to the built-in one: only what differs is sent", () => {
    const filled = { ...blank, integer_min: "0", integer_max: "999", numeric_max: "999" };
    expect(valuesFrom(filled, BUILT_IN)).toEqual({ values: {}, problems: {} });
    expect(valuesFrom({ ...filled, integer_max: "1000" }, BUILT_IN).values).toEqual({
      integer_max: 1000,
    });
  });

  it("writes a decimal as text with two decimals, never as a float", () => {
    const { values } = valuesFrom({ ...blank, numeric_max: "100.5", numeric_min: "-3" });
    expect(values).toEqual({ numeric_max: "100.50", numeric_min: "-3.00" });
    expect(typeof values.numeric_max).toBe("string");
  });

  it("tolerates spaces around a number", () => {
    expect(valuesFrom({ ...blank, integer_max: " 77 " }).values).toEqual({ integer_max: 77 });
  });

  it("names the settings that are not numbers instead of guessing", () => {
    const { values, problems } = valuesFrom({
      ...blank,
      integer_max: "12.5",
      integer_min: "abc",
      numeric_max: "1.234",
      numeric_min: "1e3",
      digit_max: "5",
    });
    expect(values).toEqual({ digit_max: 5 });
    expect(Object.keys(problems).sort()).toEqual([
      "integer_max",
      "integer_min",
      "numeric_max",
      "numeric_min",
    ]);
    expect(problems.integer_max).toMatch(/whole number/);
    expect(problems.numeric_max).toMatch(/two decimals/);
  });

  it("does not accept floats written with a comma or a plus sign", () => {
    const { problems } = valuesFrom({ ...blank, numeric_max: "1,5", integer_max: "+5" });
    expect(Object.keys(problems).sort()).toEqual(["integer_max", "numeric_max"]);
  });
});
