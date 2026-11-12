"use client";

import type { components } from "@qbank/api-client";
import { useCallback, useEffect, useRef, useState } from "react";

import { api, errorMessage, ifMatch } from "@/lib/api";
import { NETWORK } from "@/lib/use-catalogue";
import type { Content } from "@/lib/question-content";

/** What the editor needs of a question or a passage read from the server. */
export type Draft = {
  id: string;
  content: Content;
  findings: Finding[];
  revision: number;
  archived?: boolean;
};
type Finding = components["schemas"]["FindingOut"];

/** How long to wait after the last keystroke before saving (ms). */
export const SAVE_DELAY = 1500;

export type SaveState =
  | "saved" // what is on screen is what the server has
  | "dirty" // changed, waiting to be saved
  | "saving"
  | "failed" // could not reach the server or it refused; the changes are still here
  | "conflict" // someone else changed the question: reload it
  | "archived"; // the question is archived: restore it to change it

/**
 * Autosave for the question editor (M3 design note §5.1). Typing changes `content` at once; a
 * save follows after a pause, replacing the working revision under `If-Match`, so a second tab
 * cannot overwrite silently (412 → "conflict"). One save is in flight at a time and the next one
 * sends whatever was typed meanwhile. `flush` saves now (before a checkpoint); `adopt` takes a
 * question read from the server (after a checkpoint, a restore or a reload). The same hook saves a
 * passage (`kind`), which works the same way.
 */
export function useAutosave(initial: Draft, kind: "questions" | "passages" = "questions") {
  const [content, setContentState] = useState<Content>(initial.content);
  const [findings, setFindings] = useState<Finding[]>(initial.findings);
  const [state, setState] = useState<SaveState>(initial.archived === true ? "archived" : "saved");
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const latest = useRef<Content>(initial.content);
  const revision = useRef(initial.revision);
  const dirty = useRef(false);
  const blocked = useRef(initial.archived === true); // conflict or archived: no more saves
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const running = useRef<Promise<boolean> | null>(null);
  const id = initial.id;

  /** One request. True when it went through. */
  const send = useCallback(
    async (sent: Content): Promise<boolean> => {
      setState("saving");
      let result;
      try {
        result =
          kind === "passages"
            ? await api().PUT("/api/v1/passages/{passage_id}/working-revision", {
                params: {
                  path: { passage_id: id },
                  header: { "If-Match": ifMatch(revision.current) },
                },
                body: { content: sent },
              })
            : await api().PUT("/api/v1/questions/{question_id}/working-revision", {
                params: {
                  path: { question_id: id },
                  header: { "If-Match": ifMatch(revision.current) },
                },
                body: { content: sent },
              });
      } catch {
        setState("failed");
        setMessage(NETWORK);
        return false;
      }
      const { data, error, response } = result;
      if (data) {
        revision.current = data.revision;
        setFindings(data.findings);
        setMessage(null);
        if (latest.current === sent) {
          dirty.current = false;
          setState("saved");
          setSavedAt(new Date());
        }
        return true;
      }
      if (response.status === 412) {
        blocked.current = true;
        setState("conflict");
        setMessage("Someone else changed this question. Reload it to see their version.");
      } else if (response.status === 409) {
        blocked.current = true;
        setState("archived");
        setMessage("This question is archived. Restore it to change it.");
      } else {
        setState("failed");
        setMessage(errorMessage(error as never, response.status));
      }
      return false;
    },
    [id, kind],
  );

  /** Save until nothing is waiting. False if it could not (the changes stay on screen). */
  const flush = useCallback(async (): Promise<boolean> => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    if (running.current) await running.current;
    const run = (async () => {
      while (dirty.current && !blocked.current) {
        if (!(await send(latest.current))) return false;
      }
      // Nothing waiting counts as saved, even when saving is blocked (an archived question has to
      // be restorable); only changes that could not be sent are a failure.
      return !dirty.current;
    })();
    running.current = run;
    try {
      return await run;
    } finally {
      if (running.current === run) running.current = null;
    }
  }, [send]);

  const setContent = useCallback(
    (next: Content) => {
      if (blocked.current) return;
      latest.current = next;
      dirty.current = true;
      setContentState(next);
      setState("dirty");
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => void flush(), SAVE_DELAY);
    },
    [flush],
  );

  /**
   * Take a question read from the server, dropping whatever was waiting to be saved. With
   * `keepEdits` the typing that could not be saved (the question was archived elsewhere, and has
   * just been restored) stays on screen and is saved again under the new revision.
   */
  const adopt = useCallback(
    (question: Draft, keepEdits = false) => {
      if (timer.current) clearTimeout(timer.current);
      timer.current = null;
      revision.current = question.revision;
      blocked.current = question.archived === true;
      setFindings(question.findings);
      setMessage(null);
      if (keepEdits && dirty.current && question.archived !== true) {
        setState("dirty");
        timer.current = setTimeout(() => void flush(), 0);
        return;
      }
      latest.current = question.content;
      dirty.current = false;
      setContentState(question.content);
      setState(question.archived === true ? "archived" : "saved");
    },
    [flush],
  );

  /** Whether typing is waiting to be saved (or could not be). */
  const unsaved = useCallback(() => dirty.current, []);

  // Closing the tab with unsaved typing: the browser asks first.
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (dirty.current) event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, []);

  // Leaving the editor inside the app (a link, Back) does not fire the browser's warning, so the
  // typing that is still waiting for its pause is sent now instead of being dropped.
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
      if (dirty.current && !blocked.current) void flush();
    },
    [flush],
  );

  return {
    content,
    setContent,
    findings,
    state,
    savedAt,
    message,
    flush,
    adopt,
    unsaved,
    revision,
  };
}
