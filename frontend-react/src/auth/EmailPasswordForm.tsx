import { Eye, EyeOff } from "lucide-react";
import { FormEvent, useState } from "react";
import { Button, Icon } from "../components/ui";
import { useI18n } from "../i18n";

type EmailPasswordFormProps = {
  error?: string | null;
  isLoading?: boolean;
  mode: "login" | "register";
  onSubmit: (payload: {
    displayName?: string;
    email: string;
    password: string;
  }) => Promise<void>;
};

/** 用途：负责 EmailPasswordForm 的界面或数据处理职责。 */
export function EmailPasswordForm({
  error,
  isLoading = false,
  mode,
  onSubmit
}: EmailPasswordFormProps) {
  const { t } = useI18n();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  /** 用途：负责 handleSubmit 的界面或数据处理职责。 */
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({
      displayName: displayName.trim() || undefined,
      email,
      password
    });
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <form className="auth-form grid gap-mc-4" onSubmit={handleSubmit}>
      {mode === "register" && (
        <label className="auth-field grid gap-mc-2">
          <span className="text-mc-label font-mc-medium text-mc-secondary">
            {t("auth.displayName")}
          </span>
          <input
            className="min-h-[var(--control-height-md)] rounded-mc-md border border-solid border-mc-border bg-mc-subtle px-mc-3 text-mc-text focus:border-mc-border-focus focus:outline-none focus:shadow-[var(--shadow-focus)]"
            autoComplete="name"
            onChange={event => setDisplayName(event.target.value)}
            placeholder="Mini ChatChat User"
            value={displayName}
          />
        </label>
      )}

      <label className="auth-field grid gap-mc-2">
        <span className="text-mc-label font-mc-medium text-mc-secondary">
          {t("auth.email")}
        </span>
        <input
          className="min-h-[var(--control-height-md)] rounded-mc-md border border-solid border-mc-border bg-mc-subtle px-mc-3 text-mc-text focus:border-mc-border-focus focus:outline-none focus:shadow-[var(--shadow-focus)]"
          autoComplete="email"
          onChange={event => setEmail(event.target.value)}
          placeholder="you@example.com"
          required
          type="email"
          value={email}
        />
      </label>

      <label className="auth-field grid gap-mc-2">
        <span className="text-mc-label font-mc-medium text-mc-secondary">
          {t("auth.password")}
        </span>
        <div className="auth-password-control grid grid-cols-[1fr_auto] items-center gap-mc-2">
          <input
            className="min-h-[var(--control-height-md)] rounded-mc-md border border-solid border-mc-border bg-mc-subtle px-mc-3 text-mc-text focus:border-mc-border-focus focus:outline-none focus:shadow-[var(--shadow-focus)]"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={8}
            onChange={event => setPassword(event.target.value)}
            placeholder={t("auth.passwordHint")}
            required
            type={showPassword ? "text" : "password"}
            value={password}
          />
          <button
            aria-label={showPassword ? t("auth.hidePassword") : t("auth.showPassword")}
            className="inline-flex h-[var(--control-height-md)] w-[var(--control-height-md)] items-center justify-center rounded-mc-md border border-solid border-mc-border bg-mc-surface text-mc-secondary transition-[background-color,border-color,color,box-shadow] duration-[var(--motion-duration-fast)] ease-[var(--motion-ease-standard)] hover:border-mc-border-strong hover:bg-mc-hover hover:text-mc-text focus-visible:[outline-width:var(--focus-ring-width)] focus-visible:[outline-style:solid] focus-visible:[outline-color:var(--color-border-focus)] focus-visible:outline-offset-[var(--focus-ring-offset)] focus-visible:[box-shadow:var(--shadow-focus)]"
            onClick={() => setShowPassword(value => !value)}
            type="button"
          >
            <Icon icon={showPassword ? EyeOff : Eye} size="sm" />
          </button>
        </div>
      </label>

      {error && (
        <p className="auth-error m-0 rounded-mc-md bg-mc-danger-soft p-mc-3 text-mc-danger">
          {error}
        </p>
      )}

      <Button loading={isLoading} type="submit" variant="primary">
        {mode === "login" ? t("auth.signIn") : t("auth.createAccount")}
      </Button>
    </form>
  );
}
