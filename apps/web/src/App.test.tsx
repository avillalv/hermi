import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, expect, test, vi } from "vitest";
import { authStore } from "./routes/auth/authStore";
import { App } from "./App";

// The Trips tab needs a session; the list call is stubbed.
beforeEach(() => {
  vi.stubGlobal("fetch", async () => Response.json({ items: [], next_cursor: null, has_more: false }));
  authStore.signIn("tok", "free");
});

test("opens on the Trips tab", () => {
  render(
    <MemoryRouter initialEntries={["/"]}>
      <App />
    </MemoryRouter>,
  );
  expect(screen.getByRole("heading", { name: "Trips" })).toBeInTheDocument();
});
