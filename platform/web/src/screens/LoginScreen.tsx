import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { loginWithPlaceholder } from "@/api/auth";
import { useSession } from "@/hooks/useSession";

export function LoginScreen() {
  const { token, signIn } = useSession();
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
      const session = await loginWithPlaceholder({ email, password });
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
        <p className="subtitle">Dev-only placeholder login while standalone web is being built locally.</p>
        <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" />
        <input
          value={password}
          type="password"
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Password"
        />
        {error ? <p className="error-text">{error}</p> : null}
        <button className="primary-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing in..." : "Continue"}
        </button>
      </form>
    </div>
  );
}
