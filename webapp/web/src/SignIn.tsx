import { useState, type FC } from "react";
import { useProfile } from "./profile";
import css from "./SignIn.module.css";

export const SignIn: FC = () => {
  const { signIn } = useProfile();
  const [name, setName] = useState("");

  const submit = () => {
    if (name.trim()) signIn(name);
  };

  return (
    <div className={css.page}>
      <div className={css.card}>
        <div className={css.mark}>✦</div>
        <span className={css.kicker}>Welcome</span>
        <h1 className={css.title}>Your lists, in order.</h1>
        <p className={css.blurb}>
          A calm place for todos you can drag into exactly the shape of
          your day. Enter a name to open your workspace.
        </p>
        <div className={css.field}>
          <input
            autoFocus
            className={css.input}
            value={name}
            placeholder="Your name"
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") submit();
            }}
          />
          <button
            className={css.button}
            onClick={submit}
            disabled={!name.trim()}
            type="button"
          >
            Continue
          </button>
        </div>
        <p className={css.note}>
          No password — this is a local profile for trying the app.
        </p>
      </div>
    </div>
  );
};
