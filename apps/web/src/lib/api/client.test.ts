import { afterEach, describe, expect, it, vi } from "vitest";
import { createApiClient, type AuthHooks } from "./client";

type Call = { url: string; init: RequestInit };

/** A mock server: `respond` gets each call and the token it carried. */
function server(respond: (c: Call, n: number) => Response) {
  const calls: Call[] = [];
  const fetchMock = vi.fn(async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    return respond({ url, init }, calls.length);
  });
  return { calls, fetchMock: fetchMock as unknown as typeof fetch };
}
const json = (status: number, body: unknown = {}) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
const auth = (o: Partial<AuthHooks> = {}): AuthHooks => ({
  getAccessToken: () => "tok1",
  refresh: vi.fn(async () => "tok2"),
  onSignedOut: vi.fn(),
  ...o,
});
const bearer = (c: Call) => new Headers(c.init.headers).get("authorization");

afterEach(() => vi.restoreAllMocks());

describe("api client", () => {
  it("sends a bearer token, omits cookies and joins the base URL", async () => {
    const s = server(() => json(200, { ok: 1 }));
    const api = createApiClient({ baseUrl: "https://api.x/", auth: auth(), fetch: s.fetchMock });
    const r = await api.get("/v1/me");
    expect(r.data).toEqual({ ok: 1 });
    expect(s.calls[0].url).toBe("https://api.x/v1/me");
    expect(bearer(s.calls[0])).toBe("Bearer tok1");
    expect(s.calls[0].init.credentials).toBe("omit");
  });

  it("sends no Authorization header when signed out", async () => {
    const s = server(() => json(200));
    const api = createApiClient({ baseUrl: "http://a", auth: auth({ getAccessToken: () => null }), fetch: s.fetchMock });
    await api.get("/v1/x");
    expect(bearer(s.calls[0])).toBeNull();
  });

  it("serialises a JSON body", async () => {
    const s = server(() => json(201, { id: "1" }));
    const api = createApiClient({ baseUrl: "http://a", auth: auth(), fetch: s.fetchMock });
    await api.post("/v1/trips", { name: "Lisbon" });
    expect(s.calls[0].init.method).toBe("POST");
    expect(s.calls[0].init.body).toBe('{"name":"Lisbon"}');
    expect(new Headers(s.calls[0].init.headers).get("content-type")).toBe("application/json");
  });

  it("on 401 refreshes once and retries with the new token", async () => {
    const s = server((c) => (bearer(c) === "Bearer tok2" ? json(200, { ok: 1 }) : json(401)));
    const a = auth();
    const api = createApiClient({ baseUrl: "http://a", auth: a, fetch: s.fetchMock });
    const r = await api.get("/v1/me");
    expect(r.response.status).toBe(200);
    expect(a.refresh).toHaveBeenCalledTimes(1);
    expect(s.calls).toHaveLength(2);
    expect(a.onSignedOut).not.toHaveBeenCalled();
  });

  it("signs out when the retry is still 401", async () => {
    const s = server(() => json(401));
    const a = auth();
    const api = createApiClient({ baseUrl: "http://a", auth: a, fetch: s.fetchMock });
    const r = await api.get("/v1/me");
    expect(r.response.status).toBe(401);
    expect(s.calls).toHaveLength(2);
    expect(a.refresh).toHaveBeenCalledTimes(1);
    expect(a.onSignedOut).toHaveBeenCalledTimes(1);
  });

  it("signs out when the refresh fails", async () => {
    const s = server(() => json(401));
    const a = auth({ refresh: vi.fn(async () => null) });
    const api = createApiClient({ baseUrl: "http://a", auth: a, fetch: s.fetchMock });
    await api.get("/v1/me");
    expect(s.calls).toHaveLength(1);
    expect(a.onSignedOut).toHaveBeenCalledTimes(1);
  });

  it("shares one refresh across concurrent 401s", async () => {
    const s = server((c) => (bearer(c) === "Bearer tok2" ? json(200) : json(401)));
    const a = auth();
    const api = createApiClient({ baseUrl: "http://a", auth: a, fetch: s.fetchMock });
    await Promise.all([api.get("/v1/a"), api.get("/v1/b")]);
    expect(a.refresh).toHaveBeenCalledTimes(1);
  });

  it("signs out once when concurrent retries both stay 401", async () => {
    const s = server(() => json(401));
    const a = auth();
    const api = createApiClient({ baseUrl: "http://a", auth: a, fetch: s.fetchMock });
    await Promise.all([api.get("/v1/a"), api.get("/v1/b")]);
    expect(a.onSignedOut).toHaveBeenCalledTimes(1);
  });

  it("returns a 2xx with an invalid JSON body as an error", async () => {
    const s = server(() => new Response("<html>", { status: 200 }));
    const api = createApiClient({ baseUrl: "http://a", auth: auth(), fetch: s.fetchMock });
    const r = await api.get("/v1/x");
    expect(r.data).toBeUndefined();
    expect(r.error).toBe("<html>");
  });

  it("does not refresh on other errors and returns the problem body", async () => {
    const s = server(() => json(403, { code: "forbidden" }));
    const a = auth();
    const api = createApiClient({ baseUrl: "http://a", auth: a, fetch: s.fetchMock });
    const r = await api.get("/v1/x");
    expect(r.error).toEqual({ code: "forbidden" });
    expect(r.data).toBeUndefined();
    expect(a.refresh).not.toHaveBeenCalled();
  });
});
