"use client";

import { useEffect, useRef, useState } from "react";

import {
  NO_TRIM,
  cropRect,
  fitWithin,
  outputType,
  setTrim,
  type Side,
  type Trim,
} from "@/lib/picture-crop";

const BUTTON = "rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700";
/** The longest side of the preview shown while cropping, in pixels. */
const PREVIEW_SIDE = 480;

const SIDES: { side: Side; label: string }[] = [
  { side: "left", label: "Trim from the left (%)" },
  { side: "top", label: "Trim from the top (%)" },
  { side: "right", label: "Trim from the right (%)" },
  { side: "bottom", label: "Trim from the bottom (%)" },
];

/**
 * Crop a chosen picture before it is uploaded: the server stores only the final picture. The crop
 * is set with one slider per side, so it works with a keyboard and a screen reader; the preview is
 * what will be uploaded. The picture is read in the browser and never leaves it until "Use this
 * picture" is pressed. A picture larger than 2,000 pixels on its longest side is shrunk.
 */
export function PictureCropper({
  file,
  busy,
  onUse,
  onCancel,
}: {
  file: File;
  busy: boolean;
  onUse: (blob: Blob, contentType: string) => void;
  onCancel: () => void;
}) {
  const [bitmap, setBitmap] = useState<ImageBitmap | null>(null);
  const [unreadable, setUnreadable] = useState(false);
  const [trim, setTrimValue] = useState<Trim>(NO_TRIM);
  const preview = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let closed = false;
    let opened: ImageBitmap | null = null;
    createImageBitmap(file)
      .then((decoded) => {
        if (closed) {
          decoded.close();
          return;
        }
        opened = decoded;
        setBitmap(decoded);
      })
      .catch(() => {
        if (!closed) setUnreadable(true);
      });
    return () => {
      closed = true;
      opened?.close();
    };
  }, [file]);

  useEffect(() => {
    const canvas = preview.current;
    if (!bitmap || !canvas) return;
    const rect = cropRect(bitmap.width, bitmap.height, trim);
    const size = fitWithin(rect.width, rect.height, PREVIEW_SIDE);
    canvas.width = size.width;
    canvas.height = size.height;
    canvas
      .getContext("2d")
      ?.drawImage(bitmap, rect.x, rect.y, rect.width, rect.height, 0, 0, size.width, size.height);
  }, [bitmap, trim]);

  function use() {
    if (!bitmap) return;
    const rect = cropRect(bitmap.width, bitmap.height, trim);
    const size = fitWithin(rect.width, rect.height);
    const out = document.createElement("canvas");
    out.width = size.width;
    out.height = size.height;
    out
      .getContext("2d")
      ?.drawImage(bitmap, rect.x, rect.y, rect.width, rect.height, 0, 0, size.width, size.height);
    const type = outputType(file.type);
    out.toBlob(
      (blob) => {
        if (blob) onUse(blob, type);
        else setUnreadable(true);
      },
      type,
      0.9,
    );
  }

  return (
    <fieldset className="grid gap-3 rounded-md border border-zinc-300 p-3 dark:border-zinc-700">
      <legend className="px-1 text-sm font-medium">Crop the picture</legend>
      {unreadable ? (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          This file could not be read as a picture. Use a PNG, JPEG or WebP file.
        </p>
      ) : (
        <>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Trim away what is not needed. The preview is the picture that will be uploaded.
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {SIDES.map(({ side, label }) => (
              <label key={side} className="grid gap-1 text-sm">
                <span>
                  {label}: {trim[side]}
                </span>
                <input
                  type="range"
                  min={0}
                  max={90}
                  step={1}
                  value={trim[side]}
                  aria-label={label}
                  onChange={(event) =>
                    setTrimValue((current) => setTrim(current, side, Number(event.target.value)))
                  }
                />
              </label>
            ))}
          </div>
          {bitmap ? (
            <canvas
              ref={preview}
              role="img"
              aria-label="Preview of the cropped picture"
              className="max-w-full rounded-md border border-zinc-200 dark:border-zinc-800"
            />
          ) : (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">Reading the picture…</p>
          )}
        </>
      )}
      <div className="flex gap-2">
        <button
          type="button"
          className={BUTTON}
          disabled={!bitmap || unreadable || busy}
          onClick={use}
        >
          {busy ? "Uploading…" : "Use this picture"}
        </button>
        <button type="button" className={BUTTON} disabled={busy} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </fieldset>
  );
}
