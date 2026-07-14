import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RebootClientProvider } from "@reboot-dev/reboot-react";
import { BoardApp } from "./App";
import "../../index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RebootClientProvider>
      <BoardApp />
    </RebootClientProvider>
  </StrictMode>
);
