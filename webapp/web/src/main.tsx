import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { RebootClientProvider } from "@reboot-dev/reboot-react";
import { App } from "./App";
import "./index.css";

// Talk to the backend through this page's own origin: the Vite dev server
// proxies `/__/reboot` to the backend (see vite.config.ts). Using the
// current origin (rather than a hardcoded localhost:9992) is what makes the
// app work when it's reached over a forwarded host — e.g. a GitHub
// Codespaces `*.app.github.dev` URL, where `localhost` is the viewer's own
// machine. Override with VITE_REBOOT_URL only when pointing at a separate
// backend host.
const REBOOT_URL =
  (import.meta.env.VITE_REBOOT_URL as string | undefined) ??
  window.location.origin;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RebootClientProvider url={REBOOT_URL}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </RebootClientProvider>
  </StrictMode>
);
