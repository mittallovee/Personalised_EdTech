"use client";

import { useEffect, useRef, useState } from "react";

const BUTTON = "rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700";

/**
 * The visual equation editor: a box where a formula is built with the keyboard (type `a/b` for a
 * fraction) or an on-screen keypad, instead of writing LaTeX. It starts from the LaTeX it is given
 * and hands LaTeX back when "Use this equation" is pressed; nothing else is stored, so what is
 * saved is always the LaTeX source, which the same renderer draws everywhere (ADR-0016).
 *
 * MathLive is a large library, so it is loaded only when this editor is opened (the component is
 * only rendered then), never with the rest of the page.
 */
export function EquationVisualEditor({
  initial,
  onUse,
  onCancel,
}: {
  initial: string;
  onUse: (latex: string) => void;
  onCancel: () => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const field = useRef<{ value: string } | null>(null);
  const [start] = useState(initial);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let closed = false;
    let element: HTMLElement | null = null;
    import("mathlive")
      .then(({ MathfieldElement }) => {
        if (closed || !host.current) return;
        // Fonts come from the page's own KaTeX stylesheet; MathLive fetches nothing else.
        MathfieldElement.fontsDirectory = null;
        MathfieldElement.soundsDirectory = null;
        const math = new MathfieldElement();
        // The keypad opens when asked for (the keyboard button in the box), not by itself.
        math.setAttribute("math-virtual-keyboard-policy", "manual");
        math.value = start;
        math.setAttribute("aria-label", "Equation");
        host.current.append(math);
        math.mathVirtualKeyboardPolicy = "manual";
        element = math;
        field.current = math;
        math.focus();
      })
      .catch(() => {
        if (!closed) setFailed(true);
      });
    return () => {
      closed = true;
      element?.remove();
      field.current = null;
    };
  }, [start]);

  return (
    <div
      role="group"
      aria-label="Visual equation editor"
      className="grid gap-3 rounded-md border border-zinc-300 p-3 dark:border-zinc-700"
    >
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        Type the equation; for a fraction type a slash, like a/b. The LaTeX is written back when you
        press Use this equation.
      </p>
      {failed ? (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          The visual editor could not be loaded. You can still write the LaTeX in the box above.
        </p>
      ) : (
        <div ref={host} className="text-xl" />
      )}
      <div className="flex gap-2">
        <button
          type="button"
          className={BUTTON}
          disabled={failed}
          onClick={() => onUse(field.current?.value ?? start)}
        >
          Use this equation
        </button>
        <button type="button" className={BUTTON} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}
