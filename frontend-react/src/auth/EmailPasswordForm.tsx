import { Eye, EyeOff } from "lucide-react";
import { FormEvent, useState } from "react";
import { Button, Icon } from "../components/ui";

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
    <form className="auth-form" onSubmit={handleSubmit}>
      {mode === "register" && (
        <label className="auth-field">
          <span>Display name</span>
          <input
            autoComplete="name"
            onChange={event => setDisplayName(event.target.value)}
            placeholder="Mini ChatChat User"
            value={displayName}
          />
        </label>
      )}

      <label className="auth-field">
        <span>Email</span>
        <input
          autoComplete="email"
          onChange={event => setEmail(event.target.value)}
          placeholder="you@example.com"
          required
          type="email"
          value={email}
        />
      </label>

      <label className="auth-field">
        <span>Password</span>
        <div className="auth-password-control">
          <input
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={8}
            onChange={event => setPassword(event.target.value)}
            placeholder="At least 8 characters"
            required
            type={showPassword ? "text" : "password"}
            value={password}
          />
          <button
            aria-label={showPassword ? "Hide password" : "Show password"}
            onClick={() => setShowPassword(value => !value)}
            type="button"
          >
            <Icon icon={showPassword ? EyeOff : Eye} size="sm" />
          </button>
        </div>
      </label>

      {error && <p className="auth-error">{error}</p>}

      <Button loading={isLoading} type="submit" variant="primary">
        {mode === "login" ? "Sign in" : "Create account"}
      </Button>
    </form>
  );
}
