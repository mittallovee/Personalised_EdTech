import type { ReactNode } from "react";
import { splitInline } from "./inline";
import { Math } from "./math";

/** The same limits as the server's (questions/rules.py): more is not shown. */
export const MAX_BLOCKS = 100;
export const MAX_PARAGRAPH_CHARS = 10_000;
export const MAX_TABLE_ROWS = 50;
export const MAX_TABLE_COLUMNS = 12;
export const MAX_LIST_ITEMS = 50;

export type AssetUrl = (assetId: string) => string;
export const defaultAssetUrl: AssetUrl = (id) => `/api/v1/assets/${id}/content`;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

type Obj = Record<string, unknown>;
const isObject = (value: unknown): value is Obj =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const Unsupported = () => <span className="qb-unsupported">[content not shown]</span>;
const Note = ({ children }: { children: string }) => <span className="qb-missing">{children}</span>;

/**
 * A list of content blocks (paragraph, equation, image, table, list), as stored in a question.
 * Whatever it is given, it renders without throwing: a block it does not understand becomes a
 * small notice, and text is always text, never markup. `inner` is for table cells and list items,
 * which hold only paragraphs and equations.
 */
export function Blocks({
  blocks,
  assetUrl = defaultAssetUrl,
  inner = false,
}: {
  blocks: unknown;
  assetUrl?: AssetUrl;
  inner?: boolean;
}) {
  if (!Array.isArray(blocks)) return null;
  return (
    <>
      {blocks.slice(0, MAX_BLOCKS).map((block, index) => (
        <Block key={index} block={block} assetUrl={assetUrl} inner={inner} />
      ))}
    </>
  );
}

function Block({ block, assetUrl, inner }: { block: unknown; assetUrl: AssetUrl; inner: boolean }) {
  if (!isObject(block) || typeof block.kind !== "string") return <Unsupported />;
  switch (block.kind) {
    case "paragraph":
      return typeof block.text === "string" ? <Paragraph text={block.text} /> : <Unsupported />;
    case "equation":
      return block.format === "latex" && typeof block.source === "string" ? (
        <Math source={block.source} display />
      ) : (
        <Unsupported />
      );
    case "image":
      return inner ? <Unsupported /> : <Picture block={block} assetUrl={assetUrl} />;
    case "table":
      return inner ? <Unsupported /> : <Table rows={block.rows} assetUrl={assetUrl} />;
    case "list":
      return inner ? (
        <Unsupported />
      ) : (
        <List ordered={block.ordered === true} items={block.items} assetUrl={assetUrl} />
      );
    default:
      return <Unsupported />;
  }
}

function Paragraph({ text }: { text: string }) {
  if (!text.trim()) return null;
  if (text.length > MAX_PARAGRAPH_CHARS) return <Note>[paragraph too long to show]</Note>;
  const parts: ReactNode[] = splitInline(text).map((segment, index) =>
    segment.type === "text" ? (
      segment.text
    ) : (
      <Math key={index} source={segment.source} display={false} />
    ),
  );
  return <p>{parts}</p>;
}

function Picture({ block, assetUrl }: { block: Obj; assetUrl: AssetUrl }) {
  const id = block.asset_id;
  // The address is built only from a real id, so nothing in the content can change where it points.
  if (typeof id !== "string" || !UUID.test(id)) return <Note>[picture unavailable]</Note>;
  const alt = typeof block.alt_text === "string" ? block.alt_text : "";
  const caption = typeof block.caption === "string" && block.caption ? block.caption : null;
  return (
    <figure>
      <img src={assetUrl(id)} alt={alt} loading="lazy" />
      {caption && <figcaption>{caption}</figcaption>}
    </figure>
  );
}

function Table({ rows, assetUrl }: { rows: unknown; assetUrl: AssetUrl }) {
  if (!Array.isArray(rows)) return <Unsupported />;
  const tooBig =
    rows.length > MAX_TABLE_ROWS ||
    rows.some((row) => Array.isArray(row) && row.length > MAX_TABLE_COLUMNS);
  if (tooBig) return <Note>[table too large to show]</Note>;
  return (
    <table>
      <tbody>
        {rows.map((row, r) => (
          <tr key={r}>
            {Array.isArray(row) ? (
              row.map((cell, c) => (
                <td key={c}>
                  <Blocks blocks={cell} assetUrl={assetUrl} inner />
                </td>
              ))
            ) : (
              <td>
                <Unsupported />
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function List({
  ordered,
  items,
  assetUrl,
}: {
  ordered: boolean;
  items: unknown;
  assetUrl: AssetUrl;
}) {
  if (!Array.isArray(items)) return <Unsupported />;
  if (items.length > MAX_LIST_ITEMS) return <Note>[list too large to show]</Note>;
  const Tag = ordered ? "ol" : "ul";
  return (
    <Tag>
      {items.map((item, index) => (
        <li key={index}>
          <Blocks blocks={item} assetUrl={assetUrl} inner />
        </li>
      ))}
    </Tag>
  );
}
