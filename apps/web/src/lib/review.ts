import type { components, Me } from "@qbank/api-client";

import { RETURN_REASONS, type ReturnReason } from "./workflow";

/**
 * Words for the review queue and the notifications (M4 design note §6, §10.1, §11). What is in the
 * queue, who may see it and what each notification says all come from the API; this file only
 * names the tabs and turns a notification's facts into a sentence.
 */

export type QueueState = components["schemas"]["QueueState"];
export type QueueCounts = components["schemas"]["QueueCounts"];
export type Notification = components["schemas"]["NotificationOut"];

export const QUEUE_TABS: readonly { state: QueueState; label: string; count: keyof QueueCounts }[] =
  [
    { state: "IN_REVIEW", label: "Waiting for QC", count: "waiting_for_qc" },
    { state: "QC_PASSED", label: "Waiting for approval", count: "waiting_for_approval" },
    { state: "APPROVED", label: "Waiting to publish", count: "waiting_to_publish" },
    { state: "CHANGES_REQUESTED", label: "Returned to me", count: "returned_to_me" },
  ];

/**
 * Whether to show the Review link: people with a review grant, admins and the Owner (who hold them
 * all), and a platform admin acting in a coaching. A hint for the menu only: the API refuses
 * everyone else (403), and the page says so.
 */
export function showsReview(me: Me): boolean {
  if (me.acting_organization_id !== null) return true;
  const org = me.organization;
  if (org === null) return false;
  if (org.role === "OWNER" || org.role === "ADMIN") return true;
  return org.grants.some((grant) => grant === "QC" || grant === "APPROVE" || grant === "PUBLISH");
}

/** Notifications belong to a coaching: everyone in one, and a platform admin acting in one. */
export function showsNotifications(me: Me): boolean {
  return me.organization !== null || me.acting_organization_id !== null;
}

/** "3 days", "5 hours", "a few minutes": how long something has waited, for a list. */
export function waited(sinceIso: string, now: Date = new Date()): string {
  const minutes = Math.max(0, Math.floor((now.getTime() - new Date(sinceIso).getTime()) / 60000));
  if (minutes < 60) return minutes < 5 ? "a few minutes" : `${minutes} minutes`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return hours === 1 ? "1 hour" : `${hours} hours`;
  const days = Math.floor(hours / 24);
  return days === 1 ? "1 day" : `${days} days`;
}

/** Waiting-time filter choices (`older_than_days`). */
export const AGE_CHOICES: readonly { days: number | null; label: string }[] = [
  { days: null, label: "Any time" },
  { days: 1, label: "More than a day" },
  { days: 3, label: "More than 3 days" },
  { days: 7, label: "More than a week" },
  { days: 30, label: "More than a month" },
];

function text(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function reasonLabels(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((code) => RETURN_REASONS.find((r) => r.code === (code as ReturnReason))?.label)
    .filter((label): label is string => label !== undefined);
}

/** A notification as a sentence, and where it leads. Facts are shown as text, never as markup. */
export function describe(notification: Notification): {
  title: string;
  detail: string | null;
  questionId: string | null;
} {
  const data = notification.data as Record<string, unknown>;
  const code = text(data["code"]);
  const named = code === null ? "A question" : `Question ${code}`;
  const questionId = text(data["question_id"]);
  if (notification.kind === "REVIEW_RETURNED") {
    const reasons = reasonLabels(data["reasons"]);
    const note = text(data["note"]);
    const parts = [reasons.join("; "), note ? `Note: ${note}` : ""].filter((p) => p.length > 0);
    return {
      title: `${named} was returned to you`,
      detail: parts.length > 0 ? parts.join(". ") : null,
      questionId,
    };
  }
  if (notification.kind === "QUESTION_PUBLISHED") {
    const version = typeof data["version_number"] === "number" ? data["version_number"] : null;
    return {
      title: `${named} was published`,
      detail: version !== null && version > 1 ? `Version ${version} is now the one in use.` : null,
      questionId,
    };
  }
  return {
    title: code === null ? "An update about a question" : `An update about question ${code}`,
    detail: null,
    questionId,
  };
}
