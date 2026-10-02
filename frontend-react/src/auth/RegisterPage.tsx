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
    <main className="auth-page flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,rgba(86,140,112,0.12),transparent_34%),var(--color-bg-app)] p-mc-8">
      <section className="auth-card grid w-full max-w-[440px] gap-mc-5 rounded-mc-xl border border-solid border-mc-border-subtle bg-mc-surface p-mc-8 shadow-mc-md">
        <BrandLogo size={48} title="Mini ChatChat" />
        <div>
          <p className="auth-eyebrow m-0 text-mc-label font-mc-semibold tracking-[.08em] text-mc-brand uppercase">
            {t("auth.userIsolation")}
          </p>
          <h1 className="m-0 text-mc-heading leading-[var(--line-height-heading)] text-mc-text">
            {t("auth.registerTitle")}
          </h1>
          <p className="mt-mc-2 mb-0 text-mc-secondary">
            {t("auth.registerDescription")}
          </p>
        </div>
        <EmailPasswordForm
          error={error}
          isLoading={isSubmitting}
          mode="register"
          onSubmit={handleSubmit}
        />
        <OAuthButtons mode="register" />
        <p className="auth-switch text-mc-body-small text-mc-secondary">
          {t("auth.alreadyRegistered")}{" "}
          <Link className="font-mc-medium text-mc-brand no-underline" to="/login">
            {t("auth.signIn")}
          </Link>
        </p>
        <Link
          className="auth-back-link text-mc-body-small font-mc-medium text-mc-brand no-underline"
          to="/chat"
        >
          {t("auth.continueAsGuest")}
        </Link>
      </section>
    </main>
  );
}
