import { describe, expect, it } from "vitest";

import { formatInr, parseAmount, priceSource, priceText, usagePercent } from "../src/lib/ai-admin";

const RATE = { maxDecimals: 4, max: 10000, allowEmpty: true };

describe("parseAmount", () => {
  it("keeps what was typed as text, trimmed", () => {
    expect(parseAmount(" 83.5 ", RATE)).toEqual({ ok: true, value: "83.5" });
    expect(parseAmount("0.0001", RATE)).toEqual({ ok: true, value: "0.0001" });
  });

  it("treats empty as nothing when that is allowed", () => {
    expect(parseAmount("  ", RATE)).toEqual({ ok: true, value: null });
    const result = parseAmount("", { ...RATE, allowEmpty: false });
    expect(result.ok).toBe(false);
  });

  it.each(["abc", "-1", "1e3", "1,5", "1.2.3", ".5", "5."])("refuses %s", (text) => {
    expect(parseAmount(text, RATE).ok).toBe(false);
  });

  it("refuses too many decimals and too large numbers, with a sentence", () => {
    const decimals = parseAmount("1.23456", RATE);
    expect(decimals).toEqual({ ok: false, message: "Use at most 4 decimal places." });
    const whole = parseAmount("1.5", { ...RATE, maxDecimals: 0 });
    expect(whole).toEqual({ ok: false, message: "Use a whole number." });
    const big = parseAmount("10001", RATE);
    expect(big).toEqual({ ok: false, message: "Use a number not above 10000." });
  });
});

describe("formatInr", () => {
  it("groups digits the Indian way and keeps the exact decimals", () => {
    expect(formatInr("0")).toBe("₹0");
    expect(formatInr("999")).toBe("₹999");
    expect(formatInr("1000")).toBe("₹1,000");
    expect(formatInr("123456.50")).toBe("₹1,23,456.50");
    expect(formatInr("12345678")).toBe("₹1,23,45,678");
  });

  it("says when nothing is set", () => {
    expect(formatInr(null)).toBe("not set");
    expect(formatInr(undefined)).toBe("not set");
  });
});

describe("price words", () => {
  it("never shows a guess", () => {
    expect(priceText(null)).toBe("unknown");
    expect(priceText("1.250000")).toBe("$1.250000");
    expect(priceSource("PROVIDER")).toBe("from the provider");
    expect(priceSource("ADMIN")).toBe("set by an admin");
    expect(priceSource("UNKNOWN")).toBe("unknown");
  });
});

describe("usagePercent", () => {
  it("is the share of the budget used, kept between 0 and 100", () => {
    expect(usagePercent("50.00", "200")).toBe(25);
    expect(usagePercent("0", "200")).toBe(0);
    expect(usagePercent("250", "200")).toBe(100);
    expect(usagePercent("1", null)).toBeNull();
  });

  it("treats a zero budget as used up", () => {
    expect(usagePercent("0", "0")).toBe(100);
  });
});
