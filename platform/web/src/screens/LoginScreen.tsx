import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { loginWithBackendFallback } from "@/api/auth";
import { useSession } from "@/hooks/useSession";

export function LoginScreen() {
  const { token, signIn, authError } = useSession();
  const navigate = useNavigate();
  const [email, setEmail] = useState("dev@plantlab.local");
  const [password, setPassword] = useState("password");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (token) {
    return <Navigate to="/devices" replace />;
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

  return (
    <div className="centered-page">
      <form className="auth-card" onSubmit={onSubmit}>
        <div className="eyebrow">PLANTLAB WEB</div>
        <h1>Sign in</h1>
        <p className="subtitle">Dev-only login uses the local backend when available and falls back to mock mode when it is not.</p>
        <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" />
        <input
          value={password}
          type="password"
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Password"
        />
        {authError ? <p className="error-text">{authError}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
        <button className="primary-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing in..." : "Continue"}
        </button>
      </form>
    </div>
  );
}
