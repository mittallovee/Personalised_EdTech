import { describe, expect, it } from "vitest";

import {
  MAX_SIDE,
  MIN_KEPT,
  NO_TRIM,
  cropRect,
  fitWithin,
  outputType,
  setTrim,
} from "../src/lib/picture-crop";

describe("cropRect", () => {
  it("is the whole picture when nothing is trimmed", () => {
    expect(cropRect(400, 300, NO_TRIM)).toEqual({ x: 0, y: 0, width: 400, height: 300 });
  });

  it("cuts a percentage from each side", () => {
    expect(cropRect(400, 200, { left: 10, top: 25, right: 20, bottom: 0 })).toEqual({
      x: 40,
      y: 50,
      width: 280,
      height: 150,
    });
  });

  it("always keeps at least one pixel in each direction", () => {
    const rect = cropRect(3, 3, { left: 90, top: 90, right: 0, bottom: 0 });
    expect(rect.width).toBeGreaterThanOrEqual(1);
    expect(rect.height).toBeGreaterThanOrEqual(1);
    expect(rect.x + rect.width).toBeLessThanOrEqual(3);
    expect(rect.y + rect.height).toBeLessThanOrEqual(3);
  });

  it("uses whole pixels", () => {
    const rect = cropRect(101, 77, { left: 33, top: 12, right: 7, bottom: 41 });
    for (const value of Object.values(rect)) expect(Number.isInteger(value)).toBe(true);
  });
});

describe("setTrim", () => {
  it("changes one side", () => {
    expect(setTrim(NO_TRIM, "left", 30)).toEqual({ ...NO_TRIM, left: 30 });
  });

  it("never lets a side go below 0", () => {
    expect(setTrim(NO_TRIM, "top", -5).top).toBe(0);
  });

  it("keeps at least MIN_KEPT percent of the picture between two opposite sides", () => {
    const first = setTrim(NO_TRIM, "left", 70);
    const second = setTrim(first, "right", 90);
    expect(second.left).toBe(70);
    expect(second.right).toBe(100 - MIN_KEPT - 70);
    expect(100 - second.left - second.right).toBeGreaterThanOrEqual(MIN_KEPT);
  });

  it("treats anything that is not a number as 0", () => {
    expect(setTrim(NO_TRIM, "bottom", Number.NaN).bottom).toBe(0);
    expect(setTrim(NO_TRIM, "bottom", Number.POSITIVE_INFINITY).bottom).toBe(100 - MIN_KEPT);
  });
});

describe("fitWithin", () => {
  it("leaves a small picture as it is", () => {
    expect(fitWithin(800, 600)).toEqual({ width: 800, height: 600 });
  });

  it("shrinks a large picture so the longest side is MAX_SIDE, keeping its shape", () => {
    expect(fitWithin(MAX_SIDE * 2, MAX_SIDE)).toEqual({ width: MAX_SIDE, height: MAX_SIDE / 2 });
    expect(fitWithin(MAX_SIDE, MAX_SIDE * 4)).toEqual({ width: MAX_SIDE / 4, height: MAX_SIDE });
  });

  it("never returns less than one pixel", () => {
    expect(fitWithin(MAX_SIDE * 100, 1)).toEqual({ width: MAX_SIDE, height: 1 });
  });
});

describe("outputType", () => {
  it("keeps the three kinds the server accepts", () => {
    expect(outputType("image/png")).toBe("image/png");
    expect(outputType("image/jpeg")).toBe("image/jpeg");
    expect(outputType("image/webp")).toBe("image/webp");
  });

  it("turns anything else into PNG, which the browser can always write", () => {
    expect(outputType("image/gif")).toBe("image/png");
    expect(outputType("")).toBe("image/png");
  });
});
