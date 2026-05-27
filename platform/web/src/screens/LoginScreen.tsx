import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { getGoogleAuthStartUrl, loginWithBackendFallback } from "@/api/auth";
import { useSession } from "@/hooks/useSession";

export function LoginScreen() {
  const { authMode, isHydrated, token, signIn, authError } = useSession();
  const navigate = useNavigate();
  const [email, setEmail] = useState("dev@plantlab.local");
  const [password, setPassword] = useState("password");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (token) {
    return <Navigate to="/devices" replace />;
  }

  if (!isHydrated) {
    return (
      <div className="centered-page">
        <div className="auth-card">Restoring session...</div>
      </div>
    );
  }

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const session = await loginWithBackendFallback({ email, password });
      signIn(session);
      navigate("/devices", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const startGoogleAuth = () => {
    setError(null);
    try {
      window.location.href = getGoogleAuthStartUrl();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start Google sign-in.");
    }
  };

  return (
    <div className="centered-page">
      <div className="auth-card">
        <div className="eyebrow">PLANTLAB WEB</div>
        <h1>Sign in</h1>
        <div className="stack-form">
          <p className="subtitle">Sign in to sync and manage your PlantLab devices.</p>
          <button className="primary-button" type="button" onClick={startGoogleAuth}>
            Continue with Google
          </button>
        </div>
        {authMode === "dev" ? (
          <form className="stack-form dev-login-panel" onSubmit={onSubmit}>
            <p className="subtitle">Local development sign-in</p>
            <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" />
            <input
              value={password}
              type="password"
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Password"
            />
            <button className="secondary-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Signing in..." : "Continue locally"}
            </button>
          </form>
        ) : null}
        {authError ? <p className="error-text">{authError}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
      </div>
    </div>
  );
}
