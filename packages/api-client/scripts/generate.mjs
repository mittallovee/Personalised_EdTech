// Generates src/schema.ts (TypeScript types) from the API contract api/openapi.json.
//   node scripts/generate.mjs           write the file (after `make openapi`)
//   node scripts/generate.mjs --check   fail if the committed file is out of date (CI)
import { readFile, writeFile } from "node:fs/promises";
import openapiTS, { astToString } from "openapi-typescript";

const contract = new URL("../../../api/openapi.json", import.meta.url);
const target = new URL("../src/schema.ts", import.meta.url);
const header =
  "// Generated from api/openapi.json by `pnpm --filter @qbank/api-client generate`. Do not edit.\n\n";

const ast = await openapiTS(JSON.parse(await readFile(contract, "utf8")));
const generated = header + astToString(ast);

if (process.argv.includes("--check")) {
  const committed = await readFile(target, "utf8").catch(() => "");
  if (committed !== generated) {
    console.error(
      "src/schema.ts is out of date: run `pnpm --filter @qbank/api-client generate` and commit it.",
    );
    process.exit(1);
  }
  console.log("src/schema.ts matches api/openapi.json.");
} else {
  await writeFile(target, generated);
  console.log("Wrote src/schema.ts");
}
