# @qbank/content-renderer

The only code that turns question content into screen output (ADR-0016, AGENTS.md "never render
question content as raw HTML"). No business rules and no network calls, so student apps can reuse it.

```tsx
import { Blocks } from "@qbank/content-renderer";

<Blocks blocks={question.content.stem} />;
```

- **Text is always text.** A paragraph becomes React text nodes. Inline equations sit between `\(` and
  `\)` (`\` outside an equation is one literal backslash).
- **Equations** go through KaTeX with `trust: false` (no links, images or attributes from a formula),
  a size and macro-expansion limit, and `throwOnError: false`: a broken formula shows its source in
  an error style. `src/math.tsx` is the only file that puts HTML on the page, and that HTML is
  KaTeX's output. A test checks that no other file uses raw HTML.
- **Images** are `<img>` pointing at the asset endpoint (`/api/v1/assets/{id}/content`, or what the
  host's `assetUrl` returns), built only from a real id, with the alt text.
- **Never throws.** Whatever it is given, an unknown or oversize block becomes a short notice. The
  limits match the server's (`questions/rules.py`).

Needs KaTeX's stylesheet (`katex/dist/katex.min.css`) on the page that shows it.

```bash
pnpm --filter @qbank/content-renderer test
```
