/**
 * Activation and password-reset links share one page, `/activate#<token>` (ADR-0015). The part after
 * `#` is never sent to a server by the browser. A reset link adds `.reset` after the token, because
 * the page offers Google only for activation, and cannot tell the two apart from a token alone
 * (tokens are URL-safe base64, so they never contain a dot). A link without the mark is treated as
 * an activation link; the API refuses Google for any other kind, so nothing depends on this for
 * safety, only for not offering a button that cannot work.
 */
const RESET_MARK = ".reset";

export function linkFragment(token: string, kind: "activation" | "reset"): string {
  return kind === "reset" ? `${token}${RESET_MARK}` : token;
}

export interface ParsedLink {
  token: string;
  kind: "activation" | "reset";
}

export function parseLinkFragment(fragment: string): ParsedLink {
  return fragment.endsWith(RESET_MARK)
    ? { token: fragment.slice(0, -RESET_MARK.length), kind: "reset" }
    : { token: fragment, kind: "activation" };
}
