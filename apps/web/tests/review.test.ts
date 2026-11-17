import type { Me } from "@qbank/api-client";
import { describe as group, expect, it } from "vitest";

import {
  AGE_CHOICES,
  QUEUE_TABS,
  describe,
  showsNotifications,
  showsReview,
  waited,
  type Notification,
} from "../src/lib/review";

function me(role: string | null, grants: string[] = [], acting: string | null = null): Me {
  return {
    id: "u",
    display_name: "Someone",
    is_platform_admin: acting !== null,
    organization: role === null ? null : { id: "o", display_name: "C", role, grants },
    acting_organization_id: acting,
  };
}

function note(kind: string, data: Record<string, unknown>): Notification {
  return { id: "n", kind, data, created_at: "2026-11-17T00:00:00Z", read_at: null };
}

group("the queue", () => {
  it("has one tab per queue state, each with its count", () => {
    expect(QUEUE_TABS.map((t) => t.state)).toEqual([
      "IN_REVIEW",
      "QC_PASSED",
      "APPROVED",
      "CHANGES_REQUESTED",
    ]);
    expect(new Set(QUEUE_TABS.map((t) => t.count)).size).toBe(4);
  });

  it("is in the menu for review grants, admins, the Owner and an acting platform admin", () => {
    expect(showsReview(me("FACULTY"))).toBe(false);
    expect(showsReview(me("FACULTY", ["EDIT_OTHERS"]))).toBe(false);
    for (const grant of ["QC", "APPROVE", "PUBLISH"])
      expect(showsReview(me("FACULTY", [grant]))).toBe(true);
    expect(showsReview(me("ADMIN"))).toBe(true);
    expect(showsReview(me("OWNER"))).toBe(true);
    expect(showsReview(me(null))).toBe(false);
    expect(showsReview(me(null, [], "org"))).toBe(true);
  });

  it("says how long something waited", () => {
    const now = new Date("2026-11-17T12:00:00Z");
    expect(waited("2026-11-17T11:58:00Z", now)).toBe("a few minutes");
    expect(waited("2026-11-17T11:30:00Z", now)).toBe("30 minutes");
    expect(waited("2026-11-17T11:00:00Z", now)).toBe("1 hour");
    expect(waited("2026-11-17T02:00:00Z", now)).toBe("10 hours");
    expect(waited("2026-11-16T12:00:00Z", now)).toBe("1 day");
    expect(waited("2026-11-07T12:00:00Z", now)).toBe("10 days");
    expect(waited("2026-11-18T12:00:00Z", now)).toBe("a few minutes"); // a clock ahead is not negative
  });

  it("offers any time first for the waiting filter", () => {
    expect(AGE_CHOICES[0]!.days).toBeNull();
  });
});

group("notifications", () => {
  it("are for people in a coaching", () => {
    expect(showsNotifications(me("FACULTY"))).toBe(true);
    expect(showsNotifications(me(null))).toBe(false);
    expect(showsNotifications(me(null, [], "org"))).toBe(true);
  });

  it("say a question came back, with the reasons in words and the note", () => {
    const told = describe(
      note("REVIEW_RETURNED", {
        question_id: "q1",
        code: "7K2M9PQX",
        reasons: ["ANSWER_WRONG", "NOT_A_REASON"],
        note: "Check option B.",
      }),
    );
    expect(told.title).toBe("Question 7K2M9PQX was returned to you");
    expect(told.detail).toBe(
      "The answer is wrong or does not match the question. Note: Check option B.",
    );
    expect(told.questionId).toBe("q1");
  });

  it("say a question was published, and which version for a correction", () => {
    expect(
      describe(note("QUESTION_PUBLISHED", { code: "AB", version_number: 1 })).detail,
    ).toBeNull();
    const second = describe(note("QUESTION_PUBLISHED", { code: "AB", version_number: 2 }));
    expect(second.title).toBe("Question AB was published");
    expect(second.detail).toBe("Version 2 is now the one in use.");
  });

  it("never fail on facts they do not expect", () => {
    const odd = describe(note("SOMETHING_NEW", { code: 5, question_id: ["x"] }));
    expect(odd.title).toBe("An update about a question");
    expect(odd.questionId).toBeNull();
  });
});
