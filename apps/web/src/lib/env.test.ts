import { describe, expect, it } from "vitest";
import { readEnv } from "./env";

describe("readEnv", () => {
  it("defaults the API base to localhost 8100 and strips a trailing slash", () => {
    expect(readEnv({}).apiBaseUrl).toBe("http://localhost:8100");
    expect(readEnv({ VITE_API_BASE_URL: "https://api.staging.example/" }).apiBaseUrl).toBe(
      "https://api.staging.example",
    );
  });
  it("throws on a hosted env with no API base URL", () => {
    expect(() => readEnv({ VITE_APP_ENV: "staging" })).toThrow(/VITE_API_BASE_URL/);
    expect(readEnv({ VITE_APP_ENV: "staging", VITE_API_BASE_URL: "https://a.example" }).appEnv).toBe("staging");
    expect(readEnv({ VITE_APP_ENV: "ci" }).apiBaseUrl).toBe("http://localhost:8100");
  });
  it("treats empty public keys as undefined", () => {
    const e = readEnv({ VITE_SENTRY_DSN: "", VITE_POSTHOG_KEY: "ph_x" });
    expect(e.sentryDsn).toBeUndefined();
    expect(e.posthogKey).toBe("ph_x");
    expect(e.appEnv).toBe("local");
  });
});
