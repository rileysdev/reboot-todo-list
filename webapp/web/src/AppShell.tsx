import { type FC, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useProfile } from "./profile";
import { useTheme } from "./theme";
import css from "./AppShell.module.css";

const SunIcon: FC = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
    <circle cx="8" cy="8" r="3.2" fill="currentColor" />
    {Array.from({ length: 8 }).map((_, i) => {
      const a = (i * Math.PI) / 4;
      const x1 = 8 + Math.cos(a) * 5.4;
      const y1 = 8 + Math.sin(a) * 5.4;
      const x2 = 8 + Math.cos(a) * 7;
      const y2 = 8 + Math.sin(a) * 7;
      return (
        <line
          key={i}
          x1={x1}
          y1={y1}
          x2={x2}
          y2={y2}
          stroke="currentColor"
          strokeWidth="1.4"
          strokeLinecap="round"
        />
      );
    })}
  </svg>
);

const MoonIcon: FC = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
    <path
      d="M13 9.5A5.2 5.2 0 0 1 6.5 3 5.2 5.2 0 1 0 13 9.5Z"
      fill="currentColor"
    />
  </svg>
);

export const AppShell: FC<{ children: ReactNode }> = ({ children }) => {
  const { profile, signOut } = useProfile();
  const { theme, toggle } = useTheme();
  const initial = (profile?.displayName ?? "?").charAt(0).toUpperCase();

  return (
    <div className={css.shell}>
      <header className={css.bar}>
        <Link to="/" className={css.brand}>
          <span className={css.brandMark}>✦</span>
          <span className={css.brandName}>Paper Todos</span>
        </Link>
        <div className={css.right}>
          <button
            className={css.iconBtn}
            onClick={toggle}
            aria-label="Toggle theme"
            title="Toggle light / dark"
            type="button"
          >
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
          </button>
          <div className={css.account}>
            <span className={css.avatar}>{initial}</span>
            <span className={css.accountName}>{profile?.displayName}</span>
          </div>
          <button
            className={css.signOut}
            onClick={signOut}
            type="button"
          >
            Sign out
          </button>
        </div>
      </header>
      <main className={css.main}>{children}</main>
    </div>
  );
};
