import { useState } from "react";
import { BrandLogo } from "../components/brand";
import { EmailPasswordForm } from "./EmailPasswordForm";
import { OAuthButtons } from "./OAuthButtons";
import { useAuth } from "./AuthContext";
import { Link, useNavigate } from "../router";
import { useI18n } from "../i18n";

/** 用途：负责 LoginPage 的界面或数据处理职责。 */
export function LoginPage() {
  const auth = useAuth();
  const { t } = useI18n();
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
      setError(t("auth.loginFailed"));
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
          <p className="auth-eyebrow">{t("auth.privateWorkspace")}</p>
          <h1>{t("auth.signInTitle")}</h1>
          <p>{t("auth.signInDescription")}</p>
        </div>
        <EmailPasswordForm
          error={error}
          isLoading={isSubmitting}
          mode="login"
          onSubmit={handleSubmit}
        />
        <OAuthButtons mode="login" />
        <p className="auth-switch">
          {t("auth.newHere")} <Link to="/register">{t("auth.createAccount")}</Link>
        </p>
        <Link className="auth-back-link" to="/chat">
          {t("auth.continueAsGuest")}
        </Link>
      </section>
    </main>
  );
}
