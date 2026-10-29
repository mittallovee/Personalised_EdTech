import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { requestIds, routeForLog } from "@/lib/trace";

// Gives every call to the API a request ID and a trace ID, so a problem can be followed from the
// browser through this server into the API, the database and the worker (ADR-0019). It changes only
// these two headers and writes one log line; no business logic runs here (ADR-0014).
export function proxy(request: NextRequest) {
  const { requestId, traceparent, traceId } = requestIds(
    request.headers.get("x-request-id"),
    request.headers.get("traceparent"),
  );
  const headers = new Headers(request.headers);
  headers.set("x-request-id", requestId);
  headers.set("traceparent", traceparent);

  // One JSON line in the same shape as the API's logs. Never the query string or any header.
  console.log(
    JSON.stringify({
      event: "request_forwarded",
      level: "info",
      service: "web",
      timestamp: new Date().toISOString(),
      request_id: requestId,
      trace_id: traceId,
      method: request.method,
      route: routeForLog(request.nextUrl.pathname),
    }),
  );
  return NextResponse.next({ request: { headers } });
}

// Only the calls that the rewrites in next.config.ts send on to the API.
export const config = { matcher: ["/api/v1/:path*", "/health/:path*"] };
