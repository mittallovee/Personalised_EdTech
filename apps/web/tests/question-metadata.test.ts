import { describe, expect, it } from "vitest";

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
} from "../src/lib/question-metadata";

const id = (name: string): string => `00000000-0000-4000-8000-${name.padStart(12, "0")}`;
const [cls, subject, chapter, topic, subtopic] = ["1", "2", "3", "4", "5"].map(id) as [
  string,
  string,
  string,
  string,
  string,
];
const [c1, c2, c3, nine, ten] = ["6", "7", "8", "9", "a"].map(id) as [
  string,
  string,
  string,
  string,
  string,
];

const full = {
  schema_version: 1,
  stem: [],
  metadata: {
    class_id: cls,
    subject_id: subject,
    chapter_id: chapter,
    topic_id: topic,
    subtopic_id: subtopic,
    primary_concept_id: c1,
    secondary_concept_ids: [c2],
    difficulty: 4,
  },
};

describe("metadataOf", () => {
  it("is an empty object when there are no labels yet, or they are not an object", () => {
    expect(metadataOf({})).toEqual({});
    expect(metadataOf({ metadata: null })).toEqual({});
    expect(metadataOf({ metadata: [1] })).toEqual({});
    expect(metadataOf({ metadata: "x" })).toEqual({});
  });
});

describe("setPickedLevel", () => {
  it("lists the syllabus from the class down", () => {
    expect(LADDER).toEqual(["class_id", "subject_id", "chapter_id", "topic_id", "subtopic_id"]);
  });

  it("clears everything below a level that changes", () => {
    const next = setPickedLevel(full, "chapter_id", nine);
    expect(metadataOf(next)).toMatchObject({ class_id: cls, subject_id: subject });
    expect(metadataOf(next).chapter_id).toBe(nine);
    expect(metadataOf(next)).not.toHaveProperty("topic_id");
    expect(metadataOf(next)).not.toHaveProperty("subtopic_id");
  });

  it("a new subject also clears the concepts, which belong to one subject", () => {
    const next = metadataOf(setPickedLevel(full, "subject_id", nine));
    expect(next).not.toHaveProperty("chapter_id");
    expect(next).not.toHaveProperty("primary_concept_id");
    expect(next).not.toHaveProperty("secondary_concept_ids");
    expect(next.difficulty).toBe(4);
  });

  it("choosing the same one again changes nothing", () => {
    expect(setPickedLevel(full, "chapter_id", chapter)).toBe(full);
  });

  it("choosing nothing clears the level and those below it", () => {
    const next = metadataOf(setPickedLevel(full, "topic_id", ""));
    expect(next).not.toHaveProperty("topic_id");
    expect(next).not.toHaveProperty("subtopic_id");
    expect(next.chapter_id).toBe(chapter);
  });

  it("does not change the content it was given", () => {
    const before = JSON.stringify(full);
    setPickedLevel(full, "class_id", nine);
    expect(JSON.stringify(full)).toBe(before);
  });
});

describe("concepts", () => {
  it("the main concept is set, and leaves the other concepts if it was one of them", () => {
    const next = metadataOf(setMainConcept(full, c2));
    expect(next.primary_concept_id).toBe(c2);
    expect(next).not.toHaveProperty("secondary_concept_ids");
  });

  it("adds another concept once, never the main one", () => {
    let content = addOtherConcept(full, c3);
    content = addOtherConcept(content, c3);
    content = addOtherConcept(content, c1);
    expect(metadataOf(content).secondary_concept_ids).toEqual([c2, c3]);
  });

  it("removes another concept, and the list goes when it is empty", () => {
    const next = removeOtherConcept(full, c2);
    expect(metadataOf(next)).not.toHaveProperty("secondary_concept_ids");
    expect(metadataOf(removeOtherConcept(full, c3)).secondary_concept_ids).toEqual([c2]);
  });
});

describe("difficulty, Bloom and plain text", () => {
  it("difficulty is a whole number, or gone", () => {
    expect(metadataOf(setDifficulty(full, "7")).difficulty).toBe(7);
    expect(metadataOf(setDifficulty(full, "")).difficulty).toBeUndefined();
  });

  it("text is kept as typed, and empty text removes the label", () => {
    const next = setPlainText(full, "bloom_level", "APPLY");
    expect(metadataOf(next).bloom_level).toBe("APPLY");
    expect(metadataOf(setPlainText(next, "bloom_level", "")).bloom_level).toBeUndefined();
    expect(metadataOf(setPlainText(full, "source_note", "  kept  ")).source_note).toBe("  kept  ");
  });
});

describe("past-year details", () => {
  it("the year is a number when it is digits, otherwise kept as typed for the server to flag", () => {
    expect(metadataOf(setYear(full, "2024")).exam_year).toBe(2024);
    expect(metadataOf(setYear(full, "20x4")).exam_year).toBe("20x4");
    expect(metadataOf(setYear(full, "")).exam_year).toBeUndefined();
  });

  it("a year too long to be a safe number is kept as typed, not rounded", () => {
    expect(metadataOf(setYear(full, "99999999999999999999")).exam_year).toBe(
      "99999999999999999999",
    );
  });

  it("turning it on sets the flag; turning it off clears the exam details", () => {
    let content = setPastYear(full, true);
    content = setPlainText(content, "exam_id", ten);
    content = setYear(content, "2024");
    content = setPlainText(content, "exam_shift", "Shift 1");
    expect(metadataOf(content)).toMatchObject({ is_pyq: true, exam_year: 2024 });

    const off = metadataOf(setPastYear(content, false));
    expect(off.is_pyq).toBe(false);
    for (const field of ["exam_id", "exam_year", "exam_date", "exam_shift", "paper_code"]) {
      expect(off).not.toHaveProperty(field);
    }
    expect(off.class_id).toBe(cls);
  });
});
