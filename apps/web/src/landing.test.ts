import { beforeEach, describe, expect, it, vi } from "vitest";
import brandLogo from "../../../app-buildout/brand/hermi-logo.svg?raw";
import brandDark from "../../../app-buildout/brand/hermi-logo-dark.svg?raw";
import landingDark from "../public/landing/hermi-logo-dark.svg?raw";
import landingLogo from "../public/landing/hermi-logo.svg?raw";
import indexHtml from "../public/landing/index.html?raw";
import landingJs from "../public/landing/landing.js?raw";
import privacyHtml from "../public/landing/privacy.html?raw";

const files: Record<string, string> = { "index.html": indexHtml, "privacy.html": privacyHtml, "landing.js": landingJs };
const read = (f: string) => files[f];

describe("landing page", () => {
  const html = read("index.html");
  it("has the headline, logo, fields and privacy link", () => {
    expect(html).toContain("Plan together.");
    expect(html).toContain("Know the fare.");
    expect(html).toContain('<img src="hermi-logo.svg" alt="Hermi"');
    expect(landingLogo).toBe(brandLogo);
    expect(landingDark).toBe(brandDark);
    expect(html).toContain('srcset="hermi-logo-dark.svg"');
    for (const name of ["email", "who", "current_app"]) expect(html).toContain(`name="${name}"`);
    expect(html).toMatch(/href="privacy\.html"/);
    expect(html).toContain('name="viewport"');
    expect(html).toContain('name="description"');
  });
  it("makes no external requests and no dash characters", () => {
    for (const f of ["index.html", "privacy.html", "landing.js"]) {
      const s = read(f);
      expect(s).not.toMatch(/(src|href)="https?:\/\//);
      expect(s).not.toMatch(new RegExp(`[${String.fromCharCode(0x2013, 0x2014)}]`));
    }
  });
  it("posts to a configurable API url", () => {
    expect(html).toContain("data-api-url");
    expect(read("landing.js")).toContain("/v1/waitlist");
  });
});

describe("landing.js submit flow", () => {
  const status = () => document.getElementById("status")!;
  const button = () => document.querySelector("button")!;
  const submit = async () => {
    document.getElementById("waitlist")!.dispatchEvent(new Event("submit", { cancelable: true }));
    await vi.waitFor(() => expect(button().disabled).toBe(false));
  };
  beforeEach(() => {
    document.body.innerHTML = indexHtml.slice(indexHtml.indexOf("<main>"), indexHtml.indexOf("<script"));
    document.body.dataset.apiUrl = "https://api.test/";
    (document.querySelector('[name="email"]') as HTMLInputElement).value = "a@example.com";
    new Function(landingJs)();
  });
  it("202 shows success and resets the form, posting to the configured url", async () => {
    const f = vi.fn().mockResolvedValue({ ok: true, status: 202 });
    vi.stubGlobal("fetch", f);
    await submit();
    expect(f.mock.calls[0][0]).toBe("https://api.test/v1/waitlist");
    expect(status().textContent).toContain("You are on the list");
    expect((document.querySelector('[name="email"]') as HTMLInputElement).value).toBe("");
  });
  it("429 shows the rate limit message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 429 }));
    await submit();
    expect(status().textContent).toContain("Too many tries");
  });
  it("422 shows the email error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 422 }));
    await submit();
    expect(status().textContent).toContain("Check your email address");
  });
  it("500 shows the generic error, not the email error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await submit();
    expect(status().textContent).toContain("Something went wrong");
  });
  it("a rejected fetch shows the connection message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("x")));
    await submit();
    expect(status().textContent).toContain("No connection");
  });
  it("disables the button while sending", async () => {
    let done!: (v: unknown) => void;
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise((r) => (done = r))));
    document.getElementById("waitlist")!.dispatchEvent(new Event("submit", { cancelable: true }));
    expect(button().disabled).toBe(true);
    done({ ok: true, status: 202 });
    await vi.waitFor(() => expect(button().disabled).toBe(false));
  });
});
