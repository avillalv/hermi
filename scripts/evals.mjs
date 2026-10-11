// npm run evals [-- --provider fake|anthropic_api|claude_cli --max-usd N --suite NAME --out PATH]
// The default is the fake provider: no .env is read and nothing leaves the machine. A live provider needs
// EVALS_LIVE=1 and --max-usd (the Python harness refuses otherwise); only then is .env loaded, for the key.
import { run } from "./run.mjs";
import { loadEnv } from "./lib/local.mjs";

const args = process.argv.slice(2);
const i = args.indexOf("--provider");
const provider = (i >= 0 ? args[i + 1] : args.find((a) => a.startsWith("--provider="))?.split("=")[1]) ?? "fake";
const env = provider === "fake" ? { ...process.env, AI_PROVIDER: "fake" } : { ...loadEnv() };
process.exit(run("uv", ["run", "--no-sync", "python", "-m", "tests.evals", ...args], { cwd: "apps/worker", env }));
