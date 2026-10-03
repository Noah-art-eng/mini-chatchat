import { useState } from "react";
import { BrandLogo } from "../components/brand";
import { EmailPasswordForm } from "./EmailPasswordForm";
import { OAuthButtons } from "./OAuthButtons";
import { useAuth } from "./AuthContext";
import { Link, useNavigate } from "../router";
import { useI18n } from "../i18n";

export function LoginPage() {
  const auth = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(payload: { email: string; password: string }) {
    setIsSubmitting(true);
    setError(null);

    try {
      await auth.login(payload);
      navigate("/chat", { replace: true });
    } catch {
      setError(t("auth.loginFailed"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-page flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,rgba(86,140,112,0.12),transparent_34%),var(--color-bg-app)] p-mc-8">
      <section className="auth-card grid w-full max-w-[440px] gap-mc-5 rounded-mc-xl border border-solid border-mc-border-subtle bg-mc-surface p-mc-8 shadow-mc-md">
        <BrandLogo size={48} title="Mini ChatChat" />
        <div>
          <p className="auth-eyebrow m-0 text-mc-label font-mc-semibold tracking-[.08em] text-mc-brand uppercase">
            {t("auth.privateWorkspace")}
          </p>
          <h1 className="m-0 text-mc-heading leading-[var(--line-height-heading)] text-mc-text">
            {t("auth.signInTitle")}
          </h1>
          <p className="mt-mc-2 mb-0 text-mc-secondary">
            {t("auth.signInDescription")}
          </p>
        </div>
        <EmailPasswordForm
          error={error}
          isLoading={isSubmitting}
          mode="login"
          onSubmit={handleSubmit}
        />
        <OAuthButtons mode="login" />
        <p className="auth-switch text-mc-body-small text-mc-secondary">
          {t("auth.newHere")}{" "}
          <Link className="font-mc-medium text-mc-brand no-underline" to="/register">
            {t("auth.createAccount")}
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
