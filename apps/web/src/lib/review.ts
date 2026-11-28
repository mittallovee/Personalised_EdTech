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
  /** Where the notification leads when it is not a question (an uploaded document). */
  href: string | null;
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
      href: null,
    };
  }
  if (notification.kind === "QUESTION_PUBLISHED") {
    const version = typeof data["version_number"] === "number" ? data["version_number"] : null;
    return {
      title: `${named} was published`,
      detail: version !== null && version > 1 ? `Version ${version} is now the one in use.` : null,
      questionId,
      href: null,
    };
  }
  const ai = describeAi(notification.kind, data, questionId);
  if (ai !== null) return ai;
  return {
    title: code === null ? "An update about a question" : `An update about question ${code}`,
    detail: null,
    questionId,
    href: null,
  };
}

const AI_WORK: Record<string, string> = {
  TAG: "tagging",
  SOLVE: "solving",
  VERIFY: "verification",
  TRANSLATE: "translation",
};

const AI_ENDING: Record<string, string> = {
  SUCCEEDED: "has finished",
  FAILED: "did not finish",
  CANCELLED: "was cancelled",
  EXPIRED: "ran out of time at the provider",
  SUBMISSION_UNKNOWN: "could not be confirmed by the provider",
};

/**
 * The AI notifications (M5): an Economy run that ended, a budget threshold, a prompt that was
 * changed, a run whose submission is unknown. Null for any other kind. Every fact is shown as text
 * and a missing or odd one only makes the sentence plainer.
 */
function describeAi(
  kind: string,
  data: Record<string, unknown>,
  questionId: string | null,
): { title: string; detail: string | null; questionId: string | null; href: string | null } | null {
  if (kind === "AI_RUN_FINISHED") {
    const operation = text(data["operation"]);
    const work = (operation && AI_WORK[operation]) || "run";
    const status = text(data["status"]);
    const ending = (status && AI_ENDING[status]) || "has ended";
    const applied = text(data["apply_status"]) === "APPLIED";
    return {
      title: `Your Economy ${work} ${ending}`,
      detail:
        status === "SUCCEEDED"
          ? applied
            ? "It was applied to the question."
            : "Open the question and its AI tab to see the result."
          : null,
      questionId,
      href: null,
    };
  }
  if (kind === "AI_BUDGET_WARNING" || kind === "AI_BUDGET_REACHED") {
    const spent = text(data["spent_inr"]);
    const limit = text(data["limit_inr"]);
    return {
      title:
        kind === "AI_BUDGET_WARNING"
          ? "You have used 80% of your monthly AI budget"
          : "You have reached your monthly AI budget",
      detail:
        (spent && limit ? `Spent ₹${spent} of ₹${limit}. ` : "") +
        (kind === "AI_BUDGET_REACHED"
          ? "New AI runs are refused until next month, or until an admin raises it."
          : "Runs continue until the budget is reached."),
      questionId: null,
      href: null,
    };
  }
  if (kind === "AI_PROMPT_ACTIVATED") {
    const operation = text(data["operation"]);
    const version = typeof data["version_no"] === "number" ? data["version_no"] : null;
    return {
      title: "A coaching prompt was changed",
      detail:
        operation && AI_WORK[operation] && version !== null
          ? `The ${AI_WORK[operation]} prompt is now version ${version}.`
          : null,
      questionId: null,
      href: null,
    };
  }
  if (kind === "AI_SUBMISSION_UNKNOWN") {
    return {
      title: "An Economy run could not be confirmed",
      detail:
        "The provider never confirmed it was received. Its cost stays reserved until an admin settles it.",
      questionId,
      href: null,
    };
  }
  if (kind === "INGEST_EXTRACTED") {
    const fileId = text(data["file_id"]);
    const found = typeof data["candidates"] === "number" ? data["candidates"] : null;
    const failed = typeof data["pages_failed"] === "number" ? data["pages_failed"] : 0;
    const state = text(data["state"]);
    return {
      title:
        state === "FAILED"
          ? "Reading your document did not finish"
          : found === null
            ? "Your document has been read"
            : `Your document has been read: ${found} ${found === 1 ? "question" : "questions"} found`,
      detail:
        state === "FAILED"
          ? "Open it to see why and to try again."
          : failed > 0
            ? `${failed} ${failed === 1 ? "page" : "pages"} could not be read. Open it to review what was found.`
            : "Open it to review them: nothing becomes a question until you accept it.",
      questionId: null,
      href: fileId ? `/uploads/${fileId}` : null,
    };
  }
  return null;
}
