import { useState } from "react";
import { BrandLogo } from "../components/brand";
import { EmailPasswordForm } from "./EmailPasswordForm";
import { OAuthButtons } from "./OAuthButtons";
import { useAuth } from "./AuthContext";
import { Link, useNavigate } from "../router";
import { useI18n } from "../i18n";

/** 用途：负责 RegisterPage 的界面或数据处理职责。 */
export function RegisterPage() {
  const auth = useAuth();
  const { t } = useI18n();
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
      setError(t("auth.registerFailed"));
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
          <p className="auth-eyebrow">{t("auth.userIsolation")}</p>
          <h1>{t("auth.registerTitle")}</h1>
          <p>{t("auth.registerDescription")}</p>
        </div>
        <EmailPasswordForm
          error={error}
          isLoading={isSubmitting}
          mode="register"
          onSubmit={handleSubmit}
        />
        <OAuthButtons mode="register" />
        <p className="auth-switch">
          {t("auth.alreadyRegistered")} <Link to="/login">{t("auth.signIn")}</Link>
        </p>
        <Link className="auth-back-link" to="/chat">
          {t("auth.continueAsGuest")}
        </Link>
      </section>
    </main>
  );
}
