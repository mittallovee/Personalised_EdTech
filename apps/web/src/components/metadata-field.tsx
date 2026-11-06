"use client";

import { useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import type { Content } from "@/lib/question-content";
import {
  LADDER,
  addOtherConcept,
  metadataOf,
  removeOtherConcept,
  setDifficulty,
  setMainConcept,
  setPastYear,
  setPickedLevel,
  setPlainText,
  setYear,
  type Level,
} from "@/lib/question-metadata";
import { useAll } from "@/lib/use-all";
import type { Answer, Page } from "@/lib/use-catalogue";

const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const LEVEL_TITLE: Record<Level, string> = {
  class_id: "Class",
  subject_id: "Subject",
  chapter_id: "Chapter",
  topic_id: "Topic",
  subtopic_id: "Subtopic (optional)",
};

type Choice = { id: string; name: string; retired?: boolean };
type Change = (next: Content) => void;

const text = (value: unknown): string =>
  typeof value === "string" ? value : typeof value === "number" ? String(value) : "";

/** A one-shot list (the Bloom levels, the difficulty guide) in the shape `useAll` reads. */
async function whole<T>(call: Promise<Answer<T[]>>): Promise<Answer<Page<T>>> {
  const result = await call;
  return result.data
    ? { data: { data: result.data, page: {} }, response: result.response }
    : { error: result.error, response: result.response };
}
const fetchBloom = () => whole(api().GET("/api/v1/catalogues/bloom"));
const fetchGuide = () => whole(api().GET("/api/v1/catalogues/difficulty-guide"));

/**
 * The labels of a question: where it sits in the syllabus (class down to topic), its concepts,
 * difficulty, Bloom level, past-year details and source. Every pick-list is read from this
 * coaching's catalogue; what is chosen is stored as ids. Whether the choice is consistent (the
 * topic is in the chapter, the concepts are of the subject) is the server's finding, shown beside.
 */
export function MetadataField({
  content,
  onChange,
  disabled = false,
}: {
  content: Content;
  onChange: Change;
  disabled?: boolean;
}) {
  return (
    <fieldset disabled={disabled} className="grid gap-5">
      <legend className="mb-1 text-sm font-medium">Labels</legend>
      <div className="grid gap-3 sm:grid-cols-2">
        {LADDER.map((level, index) => (
          <SyllabusLevel
            key={level}
            level={level}
            parent={index === 0 ? null : text(metadataOf(content)[LADDER[index - 1]!])}
            content={content}
            onChange={onChange}
          />
        ))}
      </div>
      <Concepts content={content} onChange={onChange} />
      <DifficultyAndBloom content={content} onChange={onChange} />
      <PastYear content={content} onChange={onChange} />
    </fieldset>
  );
}

function Pick({
  label,
  value,
  options,
  onChange,
  loading = false,
  failed = false,
  unavailable = false,
}: {
  label: string;
  value: string;
  options: Choice[];
  onChange: (id: string) => void;
  loading?: boolean;
  failed?: boolean;
  unavailable?: boolean;
}) {
  const shown = options.filter((option) => !option.retired || option.id === value);
  return (
    <label className="grid gap-1 text-sm">
      <span className="text-zinc-600 dark:text-zinc-400">{label}</span>
      <select
        className={FIELD}
        value={value}
        disabled={unavailable}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{loading ? "Loading…" : "Choose…"}</option>
        {shown.map((option) => (
          <option key={option.id} value={option.id}>
            {option.name}
            {option.retired ? " (retired)" : ""}
          </option>
        ))}
        {value !== "" && !loading && !options.some((option) => option.id === value) && (
          <option value={value}>Not in the list</option>
        )}
      </select>
      {failed && (
        <span role="alert" className="text-red-700 dark:text-red-300">
          The list could not be loaded. Reload the page to try again.
        </span>
      )}
    </label>
  );
}

function TextBox({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="text-zinc-600 dark:text-zinc-400">{label}</span>
      <input
        type={type}
        autoComplete="off"
        className={FIELD}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function SyllabusLevel({
  level,
  parent,
  content,
  onChange,
}: {
  level: Level;
  parent: string | null;
  content: Content;
  onChange: Change;
}) {
  const topLevel = parent === null;
  const fetchPage = (cursor: string | null) =>
    api().GET("/api/v1/taxonomy/nodes", {
      params: {
        query: {
          limit: 100,
          ...(topLevel ? { kind: "CLASS" as const } : { parent_id: parent }),
          ...(cursor ? { cursor } : {}),
        },
      },
    });
  const { items, loading, failed } = useAll(
    topLevel ? "classes" : parent ? `under:${parent}` : null,
    fetchPage,
  );
  const options = items.map((node) => ({
    id: node.id,
    name: node.name,
    retired: node.state === "DEPRECATED",
  }));
  return (
    <Pick
      label={LEVEL_TITLE[level]}
      value={text(metadataOf(content)[level])}
      options={options}
      loading={loading}
      failed={failed}
      unavailable={!topLevel && !parent}
      onChange={(id) => onChange(setPickedLevel(content, level, id))}
    />
  );
}

function Concepts({ content, onChange }: { content: Content; onChange: Change }) {
  const meta = metadataOf(content);
  const subject = text(meta.subject_id);
  const main = text(meta.primary_concept_id);
  const others = Array.isArray(meta.secondary_concept_ids)
    ? meta.secondary_concept_ids.filter((id): id is string => typeof id === "string")
    : [];

  const [typed, setTyped] = useState("");
  const [search, setSearch] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => setSearch(typed.trim()), 300);
    return () => clearTimeout(timer);
  }, [typed]);

  const fetchPage = (cursor: string | null) =>
    api().GET("/api/v1/taxonomy/concepts", {
      params: {
        query: {
          subject_id: subject,
          state: "ACTIVE" as const,
          limit: 100,
          ...(search ? { q: search } : {}),
          ...(cursor ? { cursor } : {}),
        },
      },
    });
  const { items, loading, failed } = useAll(
    subject ? `concepts:${subject}:${search}` : null,
    fetchPage,
  );

  // The name of a chosen concept that the search does not show (another search, or retired).
  const [known, setKnown] = useState<Record<string, string>>({});
  const asked = useRef(new Set<string>());
  const chosenKey = [main, ...others].filter(Boolean).join(",");
  useEffect(() => {
    for (const id of chosenKey ? chosenKey.split(",") : []) {
      if (asked.current.has(id) || items.some((concept) => concept.id === id)) continue;
      asked.current.add(id);
      api()
        .GET("/api/v1/taxonomy/concepts/{concept_id}", { params: { path: { concept_id: id } } })
        .then(({ data }) => {
          if (data) {
            const name = data.state === "DEPRECATED" ? `${data.name} (retired)` : data.name;
            setKnown((current) => ({ ...current, [id]: name }));
          }
        })
        .catch(() => asked.current.delete(id));
    }
  }, [chosenKey, items]);
  const nameOf = (id: string) =>
    items.find((concept) => concept.id === id)?.name ?? known[id] ?? "A chosen concept";

  const found: Choice[] = items.map((concept) => ({ id: concept.id, name: concept.name }));
  const mainOptions =
    main && !found.some((option) => option.id === main)
      ? [...found, { id: main, name: nameOf(main) }]
      : found;
  const addable = found.filter((option) => option.id !== main && !others.includes(option.id));

  return (
    <div className="grid gap-3">
      <TextBox label="Search concepts" value={typed} onChange={setTyped} />
      {!subject && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Choose the subject first: concepts belong to one subject.
        </p>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        <Pick
          label="Main concept"
          value={main}
          options={mainOptions}
          loading={loading}
          failed={failed}
          unavailable={!subject}
          onChange={(id) => onChange(setMainConcept(content, id))}
        />
        <Pick
          label="Add another concept"
          value=""
          options={addable}
          loading={loading}
          unavailable={!subject}
          onChange={(id) => onChange(addOtherConcept(content, id))}
        />
      </div>
      {others.length > 0 && (
        <ul aria-label="Other concepts" className="flex flex-wrap gap-2 text-sm">
          {others.map((id) => (
            <li
              key={id}
              className="flex items-center gap-2 rounded-md border border-zinc-300 px-2 py-1 dark:border-zinc-700"
            >
              {nameOf(id)}
              <button
                type="button"
                aria-label={`Remove ${nameOf(id)}`}
                className="underline"
                onClick={() => onChange(removeOtherConcept(content, id))}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function DifficultyAndBloom({ content, onChange }: { content: Content; onChange: Change }) {
  const meta = metadataOf(content);
  const guide = useAll("difficulty-guide", fetchGuide);
  const bloom = useAll("bloom", fetchBloom);
  const level = typeof meta.difficulty === "number" ? meta.difficulty : null;
  const meaning = guide.items.find((entry) => entry.level === level)?.meaning;

  return (
    <div className="grid gap-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1 text-sm">
          <span className="text-zinc-600 dark:text-zinc-400">
            Difficulty (1 easiest, 10 hardest)
          </span>
          <select
            className={FIELD}
            value={text(meta.difficulty)}
            onChange={(event) => onChange(setDifficulty(content, event.target.value))}
          >
            <option value="">Choose…</option>
            {Array.from({ length: 10 }, (_, index) => index + 1).map((number) => (
              <option key={number} value={number}>
                {number}
              </option>
            ))}
          </select>
        </label>
        <Pick
          label="Bloom level"
          value={text(meta.bloom_level)}
          options={bloom.items.map((entry) => ({ id: entry.key, name: entry.label }))}
          loading={bloom.loading}
          failed={bloom.failed}
          onChange={(id) => onChange(setPlainText(content, "bloom_level", id))}
        />
      </div>
      {meaning && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Difficulty {level}: {meaning}
        </p>
      )}
      {guide.items.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer">What the difficulty levels mean</summary>
          <ol className="mt-2 grid gap-1 text-zinc-600 dark:text-zinc-400">
            {guide.items.map((entry) => (
              <li key={entry.level}>
                {entry.level}: {entry.meaning}
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

function PastYear({ content, onChange }: { content: Content; onChange: Change }) {
  const meta = metadataOf(content);
  const isPyq = meta.is_pyq === true;
  const fetchExams = (cursor: string | null) =>
    api().GET("/api/v1/exams", {
      params: { query: { limit: 100, ...(cursor ? { cursor } : {}) } },
    });
  const fetchSources = (cursor: string | null) =>
    api().GET("/api/v1/sources", {
      params: { query: { limit: 100, ...(cursor ? { cursor } : {}) } },
    });
  const exams = useAll(isPyq ? "exams" : null, fetchExams);
  const sources = useAll("sources", fetchSources);
  const set = (field: string) => (value: string) => onChange(setPlainText(content, field, value));

  return (
    <div className="grid gap-3">
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={isPyq}
          onChange={(event) => onChange(setPastYear(content, event.target.checked))}
        />
        This question was asked in a past-year exam
      </label>
      {isPyq && (
        <div className="grid gap-3 sm:grid-cols-2">
          <Pick
            label="Exam"
            value={text(meta.exam_id)}
            options={exams.items.map((exam) => ({
              id: exam.id,
              name: exam.short_code ? `${exam.name} (${exam.short_code})` : exam.name,
              retired: exam.state === "DEPRECATED",
            }))}
            loading={exams.loading}
            failed={exams.failed}
            onChange={set("exam_id")}
          />
          <TextBox
            label="Year"
            value={text(meta.exam_year)}
            onChange={(value) => onChange(setYear(content, value))}
          />
          <TextBox
            label="Date of the exam (optional)"
            type="date"
            value={text(meta.exam_date)}
            onChange={set("exam_date")}
          />
          <TextBox
            label="Shift (optional)"
            value={text(meta.exam_shift)}
            onChange={set("exam_shift")}
          />
          <TextBox
            label="Paper code (optional)"
            value={text(meta.paper_code)}
            onChange={set("paper_code")}
          />
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        <Pick
          label="Source (optional)"
          value={text(meta.source_id)}
          options={sources.items.map((source) => ({
            id: source.id,
            name: source.name,
            retired: source.state === "DEPRECATED",
          }))}
          loading={sources.loading}
          failed={sources.failed}
          onChange={set("source_id")}
        />
        <TextBox
          label="Note about the source (optional)"
          value={text(meta.source_note)}
          onChange={set("source_note")}
        />
      </div>
    </div>
  );
}
