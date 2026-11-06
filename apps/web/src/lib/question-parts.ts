/**
 * The parts of a matching or multiple-statement question: lists of items (left and right columns,
 * statements) and, for matching, what each option maps. Like the other editor helpers these only
 * build JSON and never change what they are given; whether the question is right is the server's
 * findings. Ids are unique across the whole question (items and options), so a new id is one that
 * nothing in the question uses, and a removed item is also taken out of every mapping that named it.
 */
import { blocksOf, withField, type Block, type Content } from "./question-content";

/** Items allowed in one list (the server's default), and the fewest a finished question has. */
export const MAX_ITEMS = 10;
export const MIN_ITEMS = 2;

export type Item = { id: string; content: Block[] };
export type Mapping = Record<string, string[]>;

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const isItem = (value: unknown): value is { id: string; content?: unknown } =>
  isObject(value) && typeof value.id === "string";

/** The items of a list field (``left``, ``right``, ``statements``); anything else is left out. */
export function itemsOf(content: Content, field: string): Item[] {
  const raw = content[field];
  return Array.isArray(raw)
    ? raw.filter(isItem).map((item) => ({ id: item.id, content: blocksOf(item.content) }))
    : [];
}

/** Every id the question already uses, in any list. */
function usedIds(content: Content): Set<string> {
  const used = new Set<string>();
  for (const field of ["left", "right", "statements", "options"]) {
    const raw = content[field];
    if (Array.isArray(raw)) for (const entry of raw) if (isItem(entry)) used.add(entry.id);
  }
  return used;
}

/** Add an empty item to ``field``, with the lowest unused id made of ``prefix`` and a number. */
export function addItem(content: Content, field: string, prefix: string): Content {
  const items = itemsOf(content, field);
  if (items.length >= MAX_ITEMS) return content;
  const used = usedIds(content);
  let number = 1;
  while (used.has(`${prefix}${number}`)) number += 1;
  const raw = Array.isArray(content[field]) ? (content[field] as unknown[]) : [];
  const added = { id: `${prefix}${number}`, content: [{ kind: "paragraph", text: "" }] };
  return withField(content, field, [...raw, added]);
}

/** The options with their mapping read from each (a mapping that is not one reads as empty). */
function mapOptions(content: Content, change: (mapping: Mapping, optionId: string) => Mapping) {
  const raw = Array.isArray(content.options) ? content.options : [];
  return raw.map((option) =>
    isItem(option) ? { ...option, mapping: change(readMapping(option), option.id) } : option,
  );
}

function readMapping(option: unknown): Mapping {
  const raw = isObject(option) ? option.mapping : undefined;
  if (!isObject(raw)) return {};
  // Built with fromEntries so that an id like "__proto__" becomes a real entry, not a prototype.
  return Object.fromEntries(
    Object.entries(raw).flatMap(([left, rights]) => {
      const names = Array.isArray(rights)
        ? rights.filter((right): right is string => typeof right === "string")
        : [];
      return names.length > 0 ? [[left, names] as const] : [];
    }),
  );
}

/**
 * The right items a left item matches in a mapping. Only the mapping's own entries count: an id such
 * as `constructor` or `toString` (the server allows them) must read as "nothing matched", not as the
 * function every object inherits under that name.
 */
export function rightsOf(mapping: Mapping, leftId: string): string[] {
  return Object.hasOwn(mapping, leftId) ? (mapping[leftId] ?? []) : [];
}

/**
 * Remove an item. A question keeps at least ``MIN_ITEMS`` of them. For matching, the item is also
 * taken out of every option's mapping (a left item loses its entry; a right item leaves the lists it
 * was in, and a list that becomes empty goes). An id that is not in the list changes nothing.
 */
export function removeItem(content: Content, field: string, id: string): Content {
  const items = itemsOf(content, field);
  if (items.length <= MIN_ITEMS || !items.some((item) => item.id === id)) return content;
  const raw = (content[field] as unknown[]).filter((entry) => !(isItem(entry) && entry.id === id));
  const next = withField(content, field, raw);
  if (content.question_type !== "MATCHING" || !Array.isArray(content.options)) return next;
  return withField(
    next,
    "options",
    mapOptions(next, (mapping) =>
      Object.fromEntries(
        Object.entries(mapping).flatMap(([left, rights]) => {
          if (field === "left" && left === id) return [];
          const remaining = field === "right" ? rights.filter((right) => right !== id) : rights;
          return remaining.length > 0 ? [[left, remaining] as const] : [];
        }),
      ),
    ),
  );
}

/** Set the blocks of one item, found by its id (an unknown id changes nothing). */
export function setItemContent(
  content: Content,
  field: string,
  id: string,
  blocks: Block[],
): Content {
  const raw = content[field];
  if (!Array.isArray(raw) || !raw.some((entry) => isItem(entry) && entry.id === id)) return content;
  return withField(
    content,
    field,
    raw.map((entry) => (isItem(entry) && entry.id === id ? { ...entry, content: blocks } : entry)),
  );
}

/** The mapping of one option of a matching question: left id to its right ids. */
export function mappingOf(content: Content, optionId: string): Mapping {
  const option = (Array.isArray(content.options) ? content.options : []).find(
    (o) => isItem(o) && o.id === optionId,
  );
  return readMapping(option);
}

/**
 * Say whether a left item of an option maps to a right item. The right items of a left item stay in
 * the order of the right list; a left item with none left has no entry. An option, left item or
 * right item that is not in the question changes nothing.
 */
export function setMapping(
  content: Content,
  optionId: string,
  leftId: string,
  rightId: string,
  on: boolean,
): Content {
  const options = Array.isArray(content.options) ? content.options : [];
  const lefts = itemsOf(content, "left").map((item) => item.id);
  const rights = itemsOf(content, "right").map((item) => item.id);
  const known = options.some((o) => isItem(o) && o.id === optionId);
  if (!known || !lefts.includes(leftId) || !rights.includes(rightId)) return content;
  return withField(
    content,
    "options",
    mapOptions(content, (mapping, id) => {
      if (id !== optionId) return mapping;
      const chosen = new Set(rightsOf(mapping, leftId));
      if (on) chosen.add(rightId);
      else chosen.delete(rightId);
      const ordered = rights.filter((right) => chosen.has(right));
      const entries = Object.entries(mapping).filter(([left]) => left !== leftId);
      return Object.fromEntries(ordered.length > 0 ? [...entries, [leftId, ordered]] : entries);
    }),
  );
}
