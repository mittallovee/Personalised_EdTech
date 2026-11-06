import { describe, expect, it } from "vitest";

import { readAllPages } from "../src/lib/use-all";

const response = new Response(null);
/** A fake catalogue of `total` numbered items served `size` at a time. */
function catalogue(total: number, size = 100) {
  let calls = 0;
  const fetchPage = async (cursor: string | null) => {
    calls++;
    const start = cursor === null ? 0 : Number(cursor);
    const end = Math.min(start + size, total);
    return {
      data: {
        data: Array.from({ length: end - start }, (_, i) => start + i),
        page: { next_cursor: end < total ? String(end) : null },
      },
      response,
    };
  };
  return { fetchPage, calls: () => calls };
}

describe("readAllPages", () => {
  it("reads every page, however many there are", async () => {
    const { fetchPage } = catalogue(2_350);
    const result = await readAllPages(fetchPage);
    expect(result.failed).toBe(false);
    expect(result.items).toHaveLength(2_350);
    expect(result.items[2_349]).toBe(2_349);
  });

  it("reports a failed page as a failure, keeping nothing half-read as complete", async () => {
    const result = await readAllPages(async () => ({ error: {}, response }));
    expect(result).toEqual({ items: [], failed: true });
  });

  it("reports a failure when the network breaks", async () => {
    const result = await readAllPages(async () => {
      throw new Error("offline");
    });
    expect(result.failed).toBe(true);
  });

  it("gives up with a failure, not a short list, if the cursor never ends", async () => {
    const stuck = async () => ({
      data: { data: [1], page: { next_cursor: "same" } },
      response,
    });
    const result = await readAllPages(stuck);
    expect(result.failed).toBe(true);
  });
});
