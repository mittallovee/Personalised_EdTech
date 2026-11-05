import type { ReactNode } from "react";
import { Blocks, defaultAssetUrl, type AssetUrl } from "./blocks";

/** Options, statements and matching items shown at most (the server allows 10 of the last two). */
const MAX_ITEMS = 10;
const LETTERS = "ABCDEFGHIJ";
const LEFT_LABELS = "PQRSTUVWXY";

type Obj = Record<string, unknown>;
const isObject = (value: unknown): value is Obj =>
  typeof value === "object" && value !== null && !Array.isArray(value);
const list = (value: unknown): Obj[] =>
  Array.isArray(value) ? value.filter(isObject).slice(0, MAX_ITEMS) : [];

/**
 * A question as a student will see it (D-10): the stem, then what the format needs, with options
 * labelled A, B, C, D by position. Until `reveal` is set nothing about the answer or the solution
 * is in the output at all, so a preview can sit beside the editor without giving anything away.
 * It shows the last saved content and never throws, whatever it is given.
 */
export function QuestionPreview({
  content,
  reveal = false,
  assetUrl = defaultAssetUrl,
}: {
  content: unknown;
  reveal?: boolean;
  assetUrl?: AssetUrl;
}) {
  if (!isObject(content)) return <p className="qb-missing">[nothing to preview]</p>;
  const type = typeof content.question_type === "string" ? content.question_type : "";
  const answer = isObject(content.answer) ? content.answer : {};
  const blocks = (value: unknown) => <Blocks blocks={value} assetUrl={assetUrl} />;
  const solution = Array.isArray(content.solution) ? content.solution : [];

  let body: ReactNode;
  switch (type) {
    case "SCQ":
    case "MULTI_CORRECT":
      body = (
        <Options
          options={list(content.options)}
          correct={correctIds(type, answer)}
          reveal={reveal}
          assetUrl={assetUrl}
        />
      );
      break;
    case "ASSERTION_REASON":
      body = (
        <>
          <Part title="Assertion (A)">{blocks(content.assertion)}</Part>
          <Part title="Reason (R)">{blocks(content.reason)}</Part>
          <Options
            options={list(content.options)}
            correct={correctIds(type, answer)}
            reveal={reveal}
            assetUrl={assetUrl}
          />
        </>
      );
      break;
    case "MULTIPLE_STATEMENT":
      body = (
        <>
          {list(content.statements).map((statement, index) => (
            <Part key={index} title={`Statement ${index + 1}`}>
              {blocks(statement.content)}
            </Part>
          ))}
          <Options
            options={list(content.options)}
            correct={correctIds(type, answer)}
            reveal={reveal}
            assetUrl={assetUrl}
          />
        </>
      );
      break;
    case "MATCHING":
      body = (
        <Matching
          content={content}
          correct={correctIds(type, answer)}
          reveal={reveal}
          assetUrl={assetUrl}
        />
      );
      break;
    case "INTEGER":
    case "SINGLE_DIGIT":
    case "NUMERICAL":
      body = (
        <>
          <input
            type="text"
            className="qb-answer-box"
            aria-label="Your answer"
            placeholder="Your answer"
            maxLength={type === "SINGLE_DIGIT" ? 1 : undefined}
            disabled
          />
          {reveal && <TypedAnswer answer={answer} />}
        </>
      );
      break;
    default:
      body = <p className="qb-missing">[this format is not shown]</p>;
  }

  return (
    <article className="qb-question">
      <div className="qb-stem">{blocks(content.stem)}</div>
      {body}
      {reveal && solution.length > 0 && (
        <section className="qb-solution">
          <h4>Solution</h4>
          {blocks(solution)}
        </section>
      )}
    </article>
  );
}

/** The ids of the correct options, from an answer of the shape the format uses. */
function correctIds(type: string, answer: Obj): string[] {
  if (type === "MULTI_CORRECT") {
    const ids = answer.option_ids;
    return Array.isArray(ids) ? ids.filter((id): id is string => typeof id === "string") : [];
  }
  return typeof answer.option_id === "string" ? [answer.option_id] : [];
}

const Part = ({ title, children }: { title: string; children: ReactNode }) => (
  <section className="qb-part">
    <h4>{title}</h4>
    {children}
  </section>
);

function Choice({
  label,
  correct,
  children,
}: {
  label: string;
  correct: boolean;
  children: ReactNode;
}) {
  return (
    <li data-correct={correct ? "true" : undefined}>
      <span className="qb-label">{label}</span>
      <div>{children}</div>
      {correct && <span className="qb-correct-note">Correct answer</span>}
    </li>
  );
}

function Options({
  options,
  correct,
  reveal,
  assetUrl,
}: {
  options: Obj[];
  correct: string[];
  reveal: boolean;
  assetUrl: AssetUrl;
}) {
  return (
    <ul className="qb-options">
      {options.map((option, index) => (
        <Choice
          key={index}
          label={LETTERS[index] ?? ""}
          correct={reveal && typeof option.id === "string" && correct.includes(option.id)}
        >
          <Blocks blocks={option.content} assetUrl={assetUrl} />
        </Choice>
      ))}
    </ul>
  );
}

function Matching({
  content,
  correct,
  reveal,
  assetUrl,
}: {
  content: Obj;
  correct: string[];
  reveal: boolean;
  assetUrl: AssetUrl;
}) {
  const left = list(content.left);
  const right = list(content.right);
  const labelOf = (items: Obj[], labels: string[]) => {
    const found = new Map<string, string>();
    items.forEach((item, index) => {
      if (typeof item.id === "string") found.set(item.id, labels[index] ?? "");
    });
    return found;
  };
  const leftLabels = labelOf(left, [...LEFT_LABELS]);
  const rightLabels = labelOf(
    right,
    right.map((_, index) => String(index + 1)),
  );

  const describe = (mapping: unknown): string => {
    if (!isObject(mapping)) return "";
    const parts: string[] = [];
    for (const [leftId, rightIds] of Object.entries(mapping)) {
      const from = leftLabels.get(leftId);
      const to = Array.isArray(rightIds)
        ? rightIds.map((id) => (typeof id === "string" ? rightLabels.get(id) : undefined))
        : [];
      const labels = to.filter((label): label is string => Boolean(label));
      if (from && labels.length > 0) parts.push(`${from} → ${labels.join(", ")}`);
    }
    return parts.join("; ");
  };

  return (
    <>
      <div className="qb-columns">
        <Part title="List I">
          <ul>
            {left.map((item, index) => (
              <li key={index}>
                <span className="qb-label">{LEFT_LABELS[index]}</span>
                <div>
                  <Blocks blocks={item.content} assetUrl={assetUrl} />
                </div>
              </li>
            ))}
          </ul>
        </Part>
        <Part title="List II">
          <ul>
            {right.map((item, index) => (
              <li key={index}>
                <span className="qb-label">{index + 1}</span>
                <div>
                  <Blocks blocks={item.content} assetUrl={assetUrl} />
                </div>
              </li>
            ))}
          </ul>
        </Part>
      </div>
      <ul className="qb-options">
        {list(content.options).map((option, index) => (
          <Choice
            key={index}
            label={LETTERS[index] ?? ""}
            correct={reveal && typeof option.id === "string" && correct.includes(option.id)}
          >
            <p>{describe(option.mapping)}</p>
          </Choice>
        ))}
      </ul>
    </>
  );
}

/** The answer of an integer, single-digit or numerical question, shown only when revealed. */
function TypedAnswer({ answer }: { answer: Obj }) {
  let shown = "";
  if (typeof answer.value === "number" && Number.isInteger(answer.value)) {
    shown = String(answer.value);
  } else if (answer.mode === "exact" && typeof answer.value === "string") {
    shown = answer.value;
  } else if (
    answer.mode === "range" &&
    typeof answer.lower === "string" &&
    typeof answer.upper === "string"
  ) {
    shown = `${answer.lower} to ${answer.upper}`;
  }
  return shown ? <p className="qb-correct-note">Answer: {shown}</p> : null;
}
