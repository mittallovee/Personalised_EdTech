// Request and trace IDs for the browser -> web -> API hop (ADR-0019). The same formats as the API:
// `X-Request-ID` is short and harmless (the API ignores anything else), `traceparent` is the W3C
// Trace Context header (version-traceid-spanid-flags).

const SAFE_REQUEST_ID = /^[A-Za-z0-9._-]{1,64}$/;
const TRACEPARENT = /^00-(?!0{32})([0-9a-f]{32})-(?!0{16})([0-9a-f]{16})-[0-9a-f]{2}$/;

function randomHex(bytes: number): string {
  const data = new Uint8Array(bytes);
  crypto.getRandomValues(data);
  return Array.from(data, (b) => b.toString(16).padStart(2, "0")).join("");
}

export type RequestIds = { requestId: string; traceparent: string; traceId: string };

/** Keep a caller's request ID and trace when they are well-formed; otherwise make new ones. */
export function requestIds(incomingRequestId: string | null, incomingTraceparent: string | null) {
  const requestId =
    incomingRequestId && SAFE_REQUEST_ID.test(incomingRequestId)
      ? incomingRequestId
      : `web_${randomHex(16)}`;
  const known = incomingTraceparent ? TRACEPARENT.exec(incomingTraceparent) : null;
  const traceId = known?.[1] ?? randomHex(16);
  // A new span ID for this hop; the trace ID stays the caller's so the whole journey is one trace.
  const traceparent = `00-${traceId}-${randomHex(8)}-01`;
  return { requestId, traceparent, traceId } satisfies RequestIds;
}

/** A path that is safe and low-cardinality to log: no query string, IDs replaced by `{id}`. */
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function routeForLog(pathname: string): string {
  return pathname
    .split("/")
    .map((part) => (UUID.test(part) || /^\d+$/.test(part) ? "{id}" : part))
    .join("/")
    .slice(0, 200);
}
