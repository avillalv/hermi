import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { App } from "./App";
import { queryClient } from "./lib/queryClient";
import { initSentry } from "./lib/sentry";
import { isAdminHost } from "./routes/admin/adminHost";
import "./index.css";

// No third-party calls from the admin host: its CSP allows none (08 section 9 rule 7).
if (!isAdminHost()) initSentry();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
