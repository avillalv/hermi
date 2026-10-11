import { run } from "./run.mjs";
import { dbUrlParts, loadEnv } from "./lib/local.mjs";

// The migration tests need the local database URLs, so pytest gets those three from .env (the process env wins).
const file = loadEnv();
// Only the three test URLs, so ENVIRONMENT and the rest of .env stay out of pytest.
const env = { ...process.env };
for (const k of ["TEST_DATABASE_URL", "TEST_DATABASE_URL_SYSTEM", "TEST_MIGRATION_DATABASE_URL"]) if (!env[k] && file[k]) env[k] = file[k];
// The admin login on the test database: DATABASE_URL_ADMIN with the database name of TEST_DATABASE_URL.
if (!env.TEST_DATABASE_URL_ADMIN) {
  const adminUrl = env.DATABASE_URL_ADMIN || file.DATABASE_URL_ADMIN;
  const testDb = dbUrlParts(env.TEST_DATABASE_URL).database;
  if (adminUrl && testDb) env.TEST_DATABASE_URL_ADMIN = adminUrl.replace(/\/[^/?]+(\?|$)/, `/${testDb}$1`);
}
let code = 0;
for (const dir of ["apps/api", "apps/worker"]) {
  code ||= run("uv", ["run", "--no-sync", "pytest", "-q"], { cwd: dir, env });
}
process.exit(code);
