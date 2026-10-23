// Test file for rules/typescript.yml (the annotations work as described in python.py).
export function Demo({ html }: { html: string }) {
  const el = document.createElement("div");
  // ruleid: qbank-no-raw-html
  el.innerHTML = html;
  // ruleid: qbank-no-raw-html
  document.write(html);
  // ruleid: qbank-no-eval
  eval(html);
  // ruleid: qbank-no-eval
  new Function(html);
  // ruleid: qbank-no-token-in-browser-storage
  localStorage.setItem("authToken", html);
  // ruleid: qbank-no-token-in-browser-storage
  window.sessionStorage.setItem("session", html);
  // ok: qbank-no-token-in-browser-storage
  localStorage.setItem("sidebar-collapsed", "1");
  // ok: qbank-no-raw-html
  el.textContent = html;
  // ruleid: qbank-no-raw-html
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}

// ruleid: qbank-no-next-server-code
export async function GET() {
  return new Response("x");
}

// ok: qbank-no-next-server-code
export function helper() {
  return 1;
}
