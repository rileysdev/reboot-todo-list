import { useEffect, useState, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAccount } from "@api/todo/v1/todo_rbt_react";
import { ProfileProvider, useProfile } from "./profile";
import { SignIn } from "./SignIn";
import { AppShell } from "./AppShell";
import { ListsPage } from "./pages/ListsPage";
import { BoardPage } from "./pages/BoardPage";
import css from "./App.module.css";

export function App() {
  return (
    <ProfileProvider>
      <Gated />
    </ProfileProvider>
  );
}

function Gated() {
  const { profile } = useProfile();
  if (!profile) return <SignIn />;
  // Keyed by accountId so switching accounts remounts the gate cleanly.
  return (
    <AccountGate key={profile.accountId} accountId={profile.accountId}>
      <AppShell>
        <Routes>
          <Route path="/" element={<ListsPage />} />
          <Route path="/list/:id" element={<BoardPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </AccountGate>
  );
}

// A browser app has no MCP host to auto-construct the account and no
// initialize hook, so the SPA constructs it on first login. A reader on
// an un-constructed actor errors, so we wait for this to resolve (whether
// it constructs fresh or the account already exists) before rendering the
// data pages.
function AccountGate({
  accountId,
  children,
}: {
  accountId: string;
  children: ReactNode;
}) {
  const { create } = useAccount({ id: accountId });
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    // No custom idempotency key: Reboot idempotency keys must be UUIDs, and
    // the generated client mints a valid one when none is passed. A repeat
    // call (e.g. StrictMode's double-invoke) simply comes back aborted with
    // StateAlreadyConstructed, which still means "the account exists."
    void create({}).finally(() => {
      // Either the account was just created or it already existed; both
      // mean it now exists and readers are safe.
      if (!cancelled) setReady(true);
    });
    return () => {
      cancelled = true;
    };
    // Runs once — the component is keyed by accountId.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!ready) {
    return (
      <div className={css.gate}>
        <div className={css.gateSpinner} />
      </div>
    );
  }
  return <>{children}</>;
}
