import { useState } from "react";
import { BrandLogo } from "../components/brand";
import { EmailPasswordForm } from "./EmailPasswordForm";
import { OAuthButtons } from "./OAuthButtons";
import { useAuth } from "./AuthContext";
import { Link, useNavigate } from "../router";

/** 用途：负责 RegisterPage 的界面或数据处理职责。 */
export function RegisterPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  /** 用途：负责 handleSubmit 的界面或数据处理职责。 */
  async function handleSubmit(payload: {
    displayName?: string;
    email: string;
    password: string;
  }) {
    /** 用途：负责 setIsSubmitting 的界面或数据处理职责。 */
    setIsSubmitting(true);
    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);

    try {
      await auth.register(payload);
      /** 用途：负责 navigate 的界面或数据处理职责。 */
      navigate("/chat", { replace: true });
    } catch {
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError("Unable to create the account. Check the email and password.");
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
          <p className="auth-eyebrow">User isolation</p>
          <h1>Create your workspace</h1>
          <p>Your private conversations and knowledge bases stay separate from the demo workspace.</p>
        </div>
        <EmailPasswordForm
          error={error}
          isLoading={isSubmitting}
          mode="register"
          onSubmit={handleSubmit}
        />
        <OAuthButtons mode="register" />
        <p className="auth-switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
        <Link className="auth-back-link" to="/chat">
          Continue as guest
        </Link>
      </section>
    </main>
  );
}
