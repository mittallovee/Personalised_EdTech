"use client";

import { useRef, useState } from "react";

import { PictureCropper } from "@/components/picture-cropper";
import { api, errorMessage } from "@/lib/api";
import type { Block } from "@/lib/question-content";
import { NETWORK } from "@/lib/use-catalogue";

const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON = "rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * A picture block: choose a file, crop it, and it is uploaded; then describe it in words (alt
 * text, so it can be understood without seeing it) and, if wanted, add a caption. The block keeps
 * only the picture's id; the picture itself is stored by the server (D-07).
 */
export function PictureField({
  block,
  where,
  onChange,
  onRemove,
}: {
  block: Block;
  where: string;
  onChange: (next: Block) => void;
  onRemove: () => void;
}) {
  const [chosen, setChosen] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const chooser = useRef<HTMLInputElement>(null);

  const assetId =
    typeof block.asset_id === "string" && UUID.test(block.asset_id) ? block.asset_id : null;
  const alt = typeof block.alt_text === "string" ? block.alt_text : "";
  const caption = typeof block.caption === "string" ? block.caption : "";

  async function upload(blob: Blob, contentType: string) {
    setUploading(true);
    setProblem(null);
    try {
      const { data, error, response } = await api().POST("/api/v1/assets/images", {
        // The picture itself is the request body, not JSON.
        body: blob as unknown as string,
        bodySerializer: (body: unknown) => body as BodyInit,
        headers: { "Content-Type": contentType },
      });
      if (data) {
        onChange({ ...block, asset_id: data.id });
        setChosen(null);
      } else {
        setProblem(errorMessage(error, response.status));
      }
    } catch {
      setProblem(NETWORK);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="grid gap-2 rounded-md border border-zinc-200 p-3 dark:border-zinc-800">
      {assetId && (
        // eslint-disable-next-line @next/next/no-img-element -- served by our own API, same origin
        <img
          src={`/api/v1/assets/${assetId}/content`}
          alt={alt}
          className="max-h-48 max-w-full justify-self-start rounded-md border border-zinc-200 dark:border-zinc-800"
        />
      )}
      {chosen ? (
        <PictureCropper
          file={chosen}
          busy={uploading}
          onUse={(blob, type) => void upload(blob, type)}
          onCancel={() => {
            setChosen(null);
            setProblem(null);
          }}
        />
      ) : (
        <label className="grid gap-1 text-sm">
          <span className="text-zinc-600 dark:text-zinc-400">
            {assetId ? "Replace the picture" : "Picture (PNG, JPEG or WebP, up to 10 MB)"}
          </span>
          <input
            ref={chooser}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            aria-label={`${where}: ${assetId ? "choose another picture" : "choose a picture"}`}
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              setProblem(null);
              setChosen(file);
              // Choosing the same file again later must still count as a choice.
              if (chooser.current) chooser.current.value = "";
            }}
          />
        </label>
      )}
      {problem && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {problem}
        </p>
      )}
      <label className="grid gap-1 text-sm">
        <span className="text-zinc-600 dark:text-zinc-400">
          Describe the picture in words (alt text)
        </span>
        <input
          type="text"
          value={alt}
          aria-label={`${where}: alt text`}
          className={FIELD}
          onChange={(event) => onChange({ ...block, alt_text: event.target.value })}
        />
      </label>
      <label className="grid gap-1 text-sm">
        <span className="text-zinc-600 dark:text-zinc-400">Caption (optional)</span>
        <input
          type="text"
          value={caption}
          aria-label={`${where}: caption`}
          className={FIELD}
          onChange={(event) => onChange({ ...block, caption: event.target.value })}
        />
      </label>
      <button
        type="button"
        className={`${BUTTON} justify-self-start`}
        aria-label={`Remove picture in ${where}`}
        onClick={onRemove}
      >
        Remove picture
      </button>
    </div>
  );
}
