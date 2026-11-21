import { describe, expect, it } from "vitest";

import {
  canEditCoaching,
  forOperation,
  inUse,
  lineStyle,
  parseTemperature,
} from "../src/lib/prompts";
import type { Template } from "../src/lib/prompts";

function template(over: Partial<Template>): Template {
  return {
    id: "t",
    scope: "PLATFORM",
    operation: "TAG",
    name: "Tag",
    target_language: null,
    owner_user_id: null,
    revision: 1,
    active_version: null,
    latest_version: null,
    update_available: null,
    ...over,
  };
}

const VERSION = {
  id: "v",
  version_no: 1,
  change_note: "",
  author_id: null,
  author_name: null,
  created_at: "2026-11-21T00:00:00Z",
  temperature: null,
  content_hash: "h",
};

describe("which prompt is in use", () => {
  it("lists a person's own first, then the coaching's, then the platform's", () => {
    const all = [
      template({ id: "p", scope: "PLATFORM", name: "B" }),
      template({ id: "c", scope: "COACHING", name: "A" }),
      template({ id: "m", scope: "PERSONAL", name: "Z" }),
      template({ id: "x", scope: "PLATFORM", operation: "SOLVE" }),
    ];
    expect(forOperation(all, "TAG").map((t) => t.id)).toEqual(["m", "c", "p"]);
  });

  it("uses the coaching's active prompt when it has one, else the platform's", () => {
    const platform = template({ id: "p", active_version: VERSION });
    const coachingOff = template({ id: "c", scope: "COACHING" });
    expect(inUse([platform, coachingOff], "TAG")?.id).toBe("p");
    const coachingOn = template({ id: "c", scope: "COACHING", active_version: VERSION });
    expect(inUse([platform, coachingOn], "TAG")?.id).toBe("c");
    expect(inUse([platform], "SOLVE")).toBeNull();
  });

  it("never offers a personal prompt as the default", () => {
    const mine = template({ id: "m", scope: "PERSONAL", active_version: VERSION });
    expect(inUse([mine], "TAG")).toBeNull();
  });
});

describe("who may edit", () => {
  const base = {
    id: "u",
    display_name: "Test",
    is_platform_admin: false,
    acting_organization_id: null,
    acting_organization_name: null,
  };
  it("needs the grant, or acting in the coaching", () => {
    const withGrant = {
      ...base,
      organization: { id: "o", display_name: "C", role: "FACULTY", grants: ["MANAGE_AI_PROMPTS"] },
    };
    const without = { ...withGrant, organization: { ...withGrant.organization, grants: [] } };
    expect(canEditCoaching(withGrant as never)).toBe(true);
    expect(canEditCoaching(without as never)).toBe(false);
    expect(canEditCoaching({ ...without, acting_organization_id: "o" } as never)).toBe(true);
    expect(canEditCoaching({ ...base, organization: null } as never)).toBe(false);
  });
});

describe("comparison lines and temperature", () => {
  it("marks added and removed lines", () => {
    expect(lineStyle({ op: "added", text: "x" }).mark).toBe("+");
    expect(lineStyle({ op: "removed", text: "x" }).mark).toBe("−");
    expect(lineStyle({ op: "same", text: "x" })).toEqual({ mark: " ", className: "" });
  });

  it("accepts 0 to 2 or nothing", () => {
    expect(parseTemperature("")).toEqual({ ok: true, value: null });
    expect(parseTemperature("0.2")).toEqual({ ok: true, value: "0.2" });
    expect(parseTemperature("2")).toEqual({ ok: true, value: "2" });
    for (const bad of ["2.5", "-1", "abc", "0.123", "3"]) {
      expect(parseTemperature(bad).ok).toBe(false);
    }
  });
});
