import { useState } from "react";
import { BrandLogo } from "../components/brand";
import { EmailPasswordForm } from "./EmailPasswordForm";
import { OAuthButtons } from "./OAuthButtons";
import { useAuth } from "./AuthContext";
import { Link, useNavigate } from "../router";

/** 用途：负责 LoginPage 的界面或数据处理职责。 */
export function LoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  /** 用途：负责 handleSubmit 的界面或数据处理职责。 */
  async function handleSubmit(payload: { email: string; password: string }) {
    /** 用途：负责 setIsSubmitting 的界面或数据处理职责。 */
    setIsSubmitting(true);
    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);

    try {
      await auth.login(payload);
      /** 用途：负责 navigate 的界面或数据处理职责。 */
      navigate("/chat", { replace: true });
    } catch {
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError("Email or password is incorrect.");
    } finally {
      /** 用途：负责 setIsSubmitting 的界面或数据处理职责。 */
      setIsSubmitting(false);
    }
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <main className="auth-page">
      <section className="auth-card">
        <BrandLogo size={48} title="Mini ChatChat" />
        <div>
          <p className="auth-eyebrow">Private workspace</p>
          <h1>Sign in to Mini ChatChat</h1>
          <p>Use your own conversations, knowledge bases, Agent tools, and preferences.</p>
        </div>
        <EmailPasswordForm
          error={error}
          isLoading={isSubmitting}
          mode="login"
          onSubmit={handleSubmit}
        />
        <OAuthButtons mode="login" />
        <p className="auth-switch">
          New here? <Link to="/register">Create an account</Link>
        </p>
        <Link className="auth-back-link" to="/chat">
          Continue as guest
        </Link>
      </section>
    </main>
  );
}
