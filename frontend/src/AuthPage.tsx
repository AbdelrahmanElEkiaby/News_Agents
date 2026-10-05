import React from "react";
import { Loader2, Newspaper } from "lucide-react";

import { User, loginUser, registerUser, storeToken } from "./api";

type AuthMode = "login" | "register";

export function AuthPage({ onAuthenticated }: { onAuthenticated: (user: User) => void }) {
  const [mode, setMode] = React.useState<AuthMode>("login");
  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const result =
        mode === "login"
          ? await loginUser(email.trim(), password)
          : await registerUser(name.trim(), email.trim(), password);

      storeToken(result.access_token);
      onAuthenticated(result.user);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Authentication failed");
    } finally {
      setIsLoading(false);
    }
  }

  function changeMode(nextMode: AuthMode) {
    setMode(nextMode);
    setErrorMessage(null);
  }

  return (
    <main className="auth-page">
      <section className="auth-intro">
        <div className="auth-brand">
          <Newspaper size={24} />
          <span>News Agent</span>
        </div>
        <h1>Your sources. Your interests. One focused feed.</h1>
        <p>
          Subscribe to Arabic and English publishers, then rank their latest reporting around the
          topics that matter to you.
        </p>
      </section>

      <section className="auth-card">
        <div className="auth-tabs">
          <button
            className={mode === "login" ? "active" : ""}
            onClick={() => changeMode("login")}
            type="button"
          >
            Login
          </button>
          <button
            className={mode === "register" ? "active" : ""}
            onClick={() => changeMode("register")}
            type="button"
          >
            Register
          </button>
        </div>

        <div className="auth-heading">
          <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
          <p>
            {mode === "login"
              ? "Sign in to open your personalized feed."
              : "Register to start choosing your news sources."}
          </p>
        </div>

        <form className="auth-form" onSubmit={submit}>
          {mode === "register" && (
            <label>
              <span>Name</span>
              <input
                autoComplete="name"
                onChange={(event) => setName(event.target.value)}
                placeholder="Your name"
                required
                value={name}
              />
            </label>
          )}

          <label>
            <span>Email</span>
            <input
              autoComplete="email"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              required
              type="email"
              value={email}
            />
          </label>

          <label>
            <span>Password</span>
            <input
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="At least 8 characters"
              required
              type="password"
              value={password}
            />
          </label>

          {errorMessage && <p className="auth-error">{errorMessage}</p>}

          <button className="auth-submit" disabled={isLoading} type="submit">
            {isLoading && <Loader2 className="spin" size={17} />}
            {mode === "login" ? "Login" : "Create account"}
          </button>
        </form>
      </section>
    </main>
  );
}
