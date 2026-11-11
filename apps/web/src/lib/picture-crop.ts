/**
 * Cropping a picture in the browser before it is uploaded (M3 design note §5.7): the server stores
 * only the final picture. The crop is set by how much to trim from each side, as a percentage, so
 * it works with the keyboard and with a screen reader as well as with a pointer.
 */

export type Trim = { left: number; top: number; right: number; bottom: number };
export type Side = keyof Trim;

export const NO_TRIM: Trim = { left: 0, top: 0, right: 0, bottom: 0 };

/** At least this percent of the picture stays between two opposite sides. */
export const MIN_KEPT = 10;

/** The longest side of an uploaded picture, in pixels (a larger one is shrunk first). */
export const MAX_SIDE = 2000;

const OPPOSITE: Record<Side, Side> = { left: "right", right: "left", top: "bottom", bottom: "top" };

/** Set the trim of one side, keeping it between 0 and what the opposite side leaves free. */
export function setTrim(trim: Trim, side: Side, value: number): Trim {
  const room = 100 - MIN_KEPT - trim[OPPOSITE[side]];
  const wanted = Number.isNaN(value) ? 0 : value;
  return { ...trim, [side]: Math.min(Math.max(wanted, 0), room) };
}

/** The part of a `width` × `height` picture that is kept, in whole pixels (at least one). */
export function cropRect(
  width: number,
  height: number,
  trim: Trim,
): { x: number; y: number; width: number; height: number } {
  const x = Math.min(Math.round((width * trim.left) / 100), width - 1);
  const y = Math.min(Math.round((height * trim.top) / 100), height - 1);
  const right = width - Math.round((width * trim.right) / 100);
  const bottom = height - Math.round((height * trim.bottom) / 100);
  return {
    x,
    y,
    width: Math.max(1, Math.min(right - x, width - x)),
    height: Math.max(1, Math.min(bottom - y, height - y)),
  };
}

/** The size to draw a picture at: unchanged, or shrunk (never enlarged) so the longest side fits. */
export function fitWithin(
  width: number,
  height: number,
  max: number = MAX_SIDE,
): { width: number; height: number } {
  const scale = Math.min(1, max / Math.max(width, height));
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  };
}

/** The kind of picture to write: the original's kind if the server takes it, otherwise PNG. */
export function outputType(fileType: string): "image/png" | "image/jpeg" | "image/webp" {
  return fileType === "image/jpeg" || fileType === "image/webp" ? fileType : "image/png";
}
