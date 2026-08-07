import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";

const core = process.env.CORE_OPENAPI_URL ?? "http://127.0.0.1:8000/openapi.json";
const ai = process.env.AI_OPENAPI_URL ?? "http://127.0.0.1:8001/openapi.json";
mkdirSync("lib/api/generated", { recursive: true });

for (const [source, output] of [[core, "lib/api/generated/core.ts"], [ai, "lib/api/generated/ai.ts"]]) {
  execFileSync(process.platform === "win32" ? "npm.cmd" : "npm", ["exec", "openapi-typescript", source, "-o", output], { stdio: "inherit" });
}
