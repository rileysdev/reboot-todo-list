import {
  createContext,
  useContext,
  useState,
  type ReactNode,
} from "react";

// A development-only stand-in for real authentication: the user picks a
// display name, from which we derive a stable account id (persisted in
// localStorage). This is NOT secure sign-in — it exists so the app has a
// real, non-empty per-account id to key state on until a token verifier
// is wired. See the servicer module's note on deferred authorization.

export type Profile = { accountId: string; displayName: string };

type ProfileContextValue = {
  profile: Profile | null;
  signIn: (displayName: string) => void;
  signOut: () => void;
};

const ProfileContext = createContext<ProfileContextValue | null>(null);
const STORAGE_KEY = "todo.profile";

function accountIdFromName(displayName: string): string {
  const slug = displayName
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `acct-${slug || "guest"}`;
}

function loadProfile(): Profile | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Profile;
    if (parsed.accountId && parsed.displayName) return parsed;
    return null;
  } catch {
    return null;
  }
}

export function ProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(loadProfile);

  const signIn = (displayName: string) => {
    const name = displayName.trim();
    if (!name) return;
    const next: Profile = {
      accountId: accountIdFromName(name),
      displayName: name,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setProfile(next);
  };

  const signOut = () => {
    localStorage.removeItem(STORAGE_KEY);
    setProfile(null);
  };

  return (
    <ProfileContext.Provider value={{ profile, signIn, signOut }}>
      {children}
    </ProfileContext.Provider>
  );
}

export function useProfile(): ProfileContextValue {
  const value = useContext(ProfileContext);
  if (!value) throw new Error("useProfile must be used within ProfileProvider");
  return value;
}
