/**
 * The passage a question sits under (D-14). A question is written under one exact checkpoint of a
 * passage, named in its `context`; this reads that and moves it to another checkpoint. Ids are
 * accepted in their standard spelling only (lower case, with dashes), as the server does.
 */

type Content = Record<string, unknown>;

const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

const contextOf = (content: Content): Content | null => {
  const context = content.context;
  return typeof context === "object" && context !== null && !Array.isArray(context)
    ? (context as Content)
    : null;
};

/** The checkpoint a question is written under, or null when it has none (or an unusable id). */
export function pinOf(content: Content): string | null {
  const pinned = contextOf(content)?.passage_revision_id;
  return typeof pinned === "string" && ID.test(pinned) ? pinned : null;
}

/** The same question written under another checkpoint; its number is kept. */
export function moveToCheckpoint(content: Content, checkpointId: string): Content {
  return { ...content, context: { ...contextOf(content), passage_revision_id: checkpointId } };
}
