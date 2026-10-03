import { Link2, Monitor, ShieldCheck, UserRound } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  listAuthSessions,
  listOAuthProviders,
  logoutAllSessions,
  logoutOtherSessions,
  revokeAuthSession,
  startOAuthLink,
  unlinkOAuthProvider,
  type AccountSession,
  type OAuthProviderStatus
} from "../../api/auth";
import { useAuth } from "../../auth";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Button, Icon, StatusBadge, useToast } from "../../components/ui";
import { cx } from "../../components/ui/utils";
import { useI18n } from "../../i18n";

type PendingAction =
  | { kind: "revoke"; session: AccountSession }
  | { kind: "logout-others" }
  | { kind: "logout-all" }
  | { kind: "unlink-oauth"; provider: OAuthProviderStatus }
  | null;

function formatDate(value: string | null) {
  if (!value) return "Never";

  try {
    return new Date(value.replace(" ", "T")).toLocaleString();
  } catch {
    return value;
  }
}

export function AccountPage() {
  const auth = useAuth();
  const { t } = useI18n();
  const { showToast } = useToast();
  const [displayName, setDisplayName] = useState(auth.session.displayName);
  const [sessions, setSessions] = useState<AccountSession[]>([]);
  const [oauthProviders, setOAuthProviders] = useState<OAuthProviderStatus[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [isLoadingProviders, setIsLoadingProviders] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const otherSessions = useMemo(
    () => sessions.filter(session => !session.is_current && session.is_active),
    [sessions]
  );

  const refreshSessions = useCallback(async () => {
    setIsLoadingSessions(true);
    setError(null);

    try {
      const response = await listAuthSessions();
      setSessions(response.sessions);
    } catch {
      setError(t("account.sessionsLoadFailed"));
    } finally {
      setIsLoadingSessions(false);
    }
  }, [t]);

  const refreshOAuthProviders = useCallback(async () => {
    setIsLoadingProviders(true);
    setError(null);

    try {
      const response = await listOAuthProviders();
      setOAuthProviders(response.providers);
    } catch {
      setError(t("account.oauthLoadFailed"));
    } finally {
      setIsLoadingProviders(false);
    }
  }, [t]);

  useEffect(() => {
    setDisplayName(auth.session.displayName);
  }, [auth.session.displayName]);

  useEffect(() => {
    if (!auth.session.isGuest) {
      refreshSessions().catch(() => undefined);
      refreshOAuthProviders().catch(() => undefined);
    }
  }, [auth.session.isGuest, refreshOAuthProviders, refreshSessions]);

  async function handleProfileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSavingProfile(true);
    setError(null);

    try {
      await auth.updateAccount({ displayName });
      showToast({ message: t("account.profileUpdated"), variant: "success" });
    } catch {
      setError(t("account.profileUpdateFailed"));
    } finally {
      setIsSavingProfile(false);
    }
  }

  async function confirmPendingAction() {
    if (!pendingAction) return;

    setIsActionLoading(true);
    setError(null);

    try {
      if (pendingAction.kind === "revoke") {
        const response = await revokeAuthSession(pendingAction.session.session_id);
        showToast({ message: t("account.sessionRevoked"), variant: "success" });
        if (response.revoked_current) {
          auth.resetToGuest();
          return;
        }
      }

      if (pendingAction.kind === "logout-others") {
        await logoutOtherSessions();
        showToast({ message: t("account.otherSessionsRevoked"), variant: "success" });
      }

      if (pendingAction.kind === "logout-all") {
        await logoutAllSessions();
        showToast({ message: t("account.allSessionsRevoked"), variant: "success" });
        auth.resetToGuest();
        return;
      }

      if (pendingAction.kind === "unlink-oauth") {
        await unlinkOAuthProvider(pendingAction.provider.provider);
        showToast({ message: t("account.oauthUnlinked"), variant: "success" });
        await refreshOAuthProviders();
      }

      await refreshSessions();
    } catch {
      setError(t("account.sessionActionFailed"));
    } finally {
      setIsActionLoading(false);
      setPendingAction(null);
    }
  }

  async function handleOAuthLink(provider: OAuthProviderStatus) {
    setError(null);
    try {
      const response = await startOAuthLink(provider.provider);
      window.location.assign(response.authorization_url);
    } catch {
      setError(t("account.oauthLinkFailed"));
    }
  }

  function providerIcon(provider: string) {
    return (
      <span
        className="oauth-provider-mark inline-grid h-[18px] w-[18px] place-items-center rounded-mc-circle bg-mc-selected text-mc-caption font-mc-bold text-mc-brand"
        aria-hidden="true"
      >
        {provider === "github" ? "GH" : "G"}
      </span>
    );
  }

  if (auth.session.isGuest) {
    return (
      <section className="account-page mx-auto grid max-w-[1120px] gap-mc-6 px-mc-6 py-mc-8 max-[720px]:px-mc-3 max-[720px]:py-mc-5">
        <div className="account-hero">
          <p className="auth-eyebrow m-0 text-mc-label font-mc-semibold tracking-[.08em] text-mc-brand uppercase">
            {t("account.privateWorkspace")}
          </p>
          <h1 className="m-0 text-mc-text">{t("account.signInRequiredTitle")}</h1>
          <p className="mt-mc-1 mb-0 text-mc-secondary">
            {t("account.signInRequiredDescription")}
          </p>
        </div>
      </section>
    );
  }

  return (
    <section
      className="account-page mx-auto grid max-w-[1120px] gap-mc-6 px-mc-6 py-mc-8 max-[720px]:px-mc-3 max-[720px]:py-mc-5"
      data-testid="account-page"
    >
      <header className="account-hero flex items-center gap-mc-4 rounded-mc-xl border border-solid border-mc-border-subtle bg-[color-mix(in_srgb,var(--color-bg-surface)_92%,transparent)] p-[28px] max-[720px]:grid">
        <div className="account-hero-icon grid h-[56px] w-[56px] flex-none place-items-center rounded-mc-lg bg-mc-brand-soft text-mc-brand" aria-hidden="true">
          <Icon icon={UserRound} size="lg" />
        </div>
        <div>
          <p className="auth-eyebrow m-0 text-mc-label font-mc-semibold tracking-[.08em] text-mc-brand uppercase">
            {t("account.title")}
          </p>
          <h1 className="m-0 text-mc-text">{t("account.heading")}</h1>
          <p className="mt-mc-1 mb-0 text-mc-secondary">{t("account.subtitle")}</p>
        </div>
      </header>

      {error && (
        <div className="account-error rounded-mc-lg border border-solid border-[#fecaca] bg-mc-danger-soft px-mc-4 py-mc-3 text-mc-danger">
          {error}
        </div>
      )}

      <div className="account-grid grid grid-cols-[minmax(0,1.2fr)_minmax(280px,.8fr)] gap-mc-5 max-[900px]:grid-cols-1">
        <section className="account-card grid gap-mc-5 rounded-mc-lg border border-solid border-mc-border-subtle bg-[color-mix(in_srgb,var(--color-bg-surface)_92%,transparent)] p-mc-6 hover:shadow-mc-xs" data-testid="profile-section">
          <div className="account-card-heading flex items-start gap-mc-3">
            <Icon icon={UserRound} size="md" tone="brand" />
            <div>
              <h2 className="m-0 text-mc-text">{t("account.profile")}</h2>
              <p className="mt-mc-1 mb-0 text-mc-secondary">
                {t("account.profileDescription")}
              </p>
            </div>
          </div>

          <form className="account-form grid gap-mc-4" onSubmit={handleProfileSubmit}>
            <label className="grid gap-mc-2">
              <span className="text-mc-label font-mc-medium text-mc-muted">
                {t("account.displayName")}
              </span>
              <input
                className="min-h-[var(--control-height-md)] rounded-mc-md border border-solid border-mc-border bg-mc-elevated px-mc-3 text-mc-text focus:border-mc-border-focus focus:outline-none focus:shadow-[var(--shadow-focus)]"
                maxLength={80}
                onChange={event => setDisplayName(event.target.value)}
                value={displayName}
              />
            </label>
            <div className="account-readonly-grid grid grid-cols-2 gap-mc-3 max-[720px]:grid-cols-1">
              <div className="grid gap-mc-1 rounded-mc-md border border-solid border-mc-border-subtle bg-mc-subtle p-mc-3">
                <span className="text-mc-label font-mc-medium text-mc-muted">
                  {t("account.email")}
                </span>
                <strong>{auth.session.email}</strong>
              </div>
              <div className="grid gap-mc-1 rounded-mc-md border border-solid border-mc-border-subtle bg-mc-subtle p-mc-3">
                <span className="text-mc-label font-mc-medium text-mc-muted">
                  {t("account.authProvider")}
                </span>
                <strong>{auth.session.authProvider}</strong>
              </div>
              <div className="grid gap-mc-1 rounded-mc-md border border-solid border-mc-border-subtle bg-mc-subtle p-mc-3">
                <span className="text-mc-label font-mc-medium text-mc-muted">
                  {t("account.createdAt")}
                </span>
                <strong>{formatDate(auth.session.createdAt)}</strong>
              </div>
            </div>
            <Button loading={isSavingProfile} type="submit" variant="primary">
              {t("account.saveProfile")}
            </Button>
          </form>
        </section>

        <section className="account-card grid gap-mc-5 rounded-mc-lg border border-solid border-mc-border-subtle bg-[color-mix(in_srgb,var(--color-bg-surface)_92%,transparent)] p-mc-6 hover:shadow-mc-xs" data-testid="oauth-section">
          <div className="account-card-heading flex items-start gap-mc-3">
            <Icon icon={Link2} size="md" tone="brand" />
            <div>
              <h2 className="m-0 text-mc-text">{t("account.connectedAccounts")}</h2>
              <p className="mt-mc-1 mb-0 text-mc-secondary">
                {t("account.connectedAccountsDescription")}
              </p>
            </div>
          </div>
          {isLoadingProviders && (
            <div className="account-session-empty rounded-mc-lg border border-dashed border-mc-border p-mc-6 text-center text-mc-secondary">
              {t("account.loadingProviders")}
            </div>
          )}
          {!isLoadingProviders && (
            <div className="oauth-provider-list grid gap-mc-3">
              {oauthProviders.map(provider => (
                <article className="oauth-provider-row flex items-center justify-between gap-mc-4 rounded-mc-lg border border-solid border-mc-border-subtle bg-mc-elevated p-mc-4" key={provider.provider}>
                  <div className="oauth-provider-main flex min-w-0 items-center gap-mc-3">
                    {providerIcon(provider.provider)}
                    <div>
                      <strong>{provider.label}</strong>
                      <p className="mt-mc-1 mb-0 break-words text-mc-secondary">
                        {provider.linked
                          ? provider.account?.provider_email || t("account.oauthLinked")
                          : provider.configured
                            ? t("account.oauthNotLinked")
                            : t("account.oauthUnavailable")}
                      </p>
                    </div>
                  </div>
                  {provider.linked ? (
                    <Button
                      onClick={() => setPendingAction({ kind: "unlink-oauth", provider })}
                      type="button"
                      variant="secondary"
                    >
                      {t("account.unlinkOAuth")}
                    </Button>
                  ) : (
                    <Button
                      disabled={!provider.configured}
                      onClick={() => handleOAuthLink(provider)}
                      type="button"
                      variant="secondary"
                    >
                      {t("account.linkOAuth")}
                    </Button>
                  )}
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="account-card grid gap-mc-5 rounded-mc-lg border border-solid border-mc-border-subtle bg-[color-mix(in_srgb,var(--color-bg-surface)_92%,transparent)] p-mc-6 hover:shadow-mc-xs" data-testid="security-section">
          <div className="account-card-heading flex items-start gap-mc-3">
            <Icon icon={ShieldCheck} size="md" tone="brand" />
            <div>
              <h2 className="m-0 text-mc-text">{t("account.security")}</h2>
              <p className="mt-mc-1 mb-0 text-mc-secondary">
                {t("account.securityDescription")}
              </p>
            </div>
          </div>
          <div className="account-security-actions flex flex-wrap gap-mc-3">
            <Button
              disabled={otherSessions.length === 0}
              onClick={() => setPendingAction({ kind: "logout-others" })}
              type="button"
              variant="secondary"
            >
              {t("account.logoutOthers")}
            </Button>
            <Button
              onClick={() => setPendingAction({ kind: "logout-all" })}
              type="button"
              variant="danger"
            >
              {t("account.logoutAll")}
            </Button>
          </div>
        </section>
      </div>

      <section className="account-card account-sessions grid gap-mc-4 rounded-mc-lg border border-solid border-mc-border-subtle bg-[color-mix(in_srgb,var(--color-bg-surface)_92%,transparent)] p-mc-6 hover:shadow-mc-xs" data-testid="session-list">
        <div className="account-card-heading flex items-start gap-mc-3">
          <Icon icon={Monitor} size="md" tone="brand" />
          <div>
            <h2 className="m-0 text-mc-text">{t("account.sessions")}</h2>
            <p className="mt-mc-1 mb-0 text-mc-secondary">
              {t("account.sessionsDescription")}
            </p>
          </div>
        </div>

        {isLoadingSessions && (
          <div className="account-session-empty rounded-mc-lg border border-dashed border-mc-border p-mc-6 text-center text-mc-secondary">
            {t("account.loadingSessions")}
          </div>
        )}

        {!isLoadingSessions && sessions.length === 0 && (
          <div className="account-session-empty rounded-mc-lg border border-dashed border-mc-border p-mc-6 text-center text-mc-secondary">
            {t("account.noSessions")}
          </div>
        )}

        {!isLoadingSessions && sessions.map(session => (
          <article
            className={cx(
              "session-row grid grid-cols-[minmax(0,1fr)_auto] items-center gap-mc-4 rounded-mc-lg border border-solid border-mc-border-subtle bg-mc-elevated p-mc-4 max-[720px]:grid-cols-1",
              session.is_current && "current border-mc-border-focus bg-mc-brand-soft"
            )}
            data-testid={`session-row-${session.is_current ? "current" : "other"}`}
            key={session.session_id}
          >
            <div className="session-row-main grid gap-mc-2">
              <div className="session-row-title flex items-center gap-mc-2">
                <strong>
                  {session.is_current
                    ? t("account.currentDevice")
                    : t("account.otherDevice")}
                </strong>
                <StatusBadge
                  label={
                    session.is_active
                      ? t("account.active")
                      : t("account.revoked")
                  }
                  status={session.is_active ? "success" : "neutral"}
                />
              </div>
              <p className="m-0 text-mc-secondary">{session.device}</p>
              <dl className="session-row-meta m-0 flex flex-wrap gap-mc-4">
                <div className="grid gap-[2px]">
                  <dt className="text-mc-label font-mc-medium text-mc-muted">
                    {t("account.lastActivity")}
                  </dt>
                  <dd className="m-0 text-mc-secondary">
                    {formatDate(session.last_used_at || session.created_at)}
                  </dd>
                </div>
                <div className="grid gap-[2px]">
                  <dt className="text-mc-label font-mc-medium text-mc-muted">
                    {t("account.expiresAt")}
                  </dt>
                  <dd className="m-0 text-mc-secondary">
                    {formatDate(session.expires_at)}
                  </dd>
                </div>
                {session.ip_address && (
                  <div className="grid gap-[2px]">
                    <dt className="text-mc-label font-mc-medium text-mc-muted">
                      {t("account.ipAddress")}
                    </dt>
                    <dd className="m-0 text-mc-secondary">{session.ip_address}</dd>
                  </div>
                )}
              </dl>
            </div>
            {session.is_active && (
              <Button
                onClick={() => setPendingAction({ kind: "revoke", session })}
                type="button"
                variant={session.is_current ? "danger" : "secondary"}
              >
                {session.is_current
                  ? t("account.logoutThisDevice")
                  : t("account.revokeSession")}
              </Button>
            )}
          </article>
        ))}
      </section>

      <ConfirmDialog
        confirmLabel={
          pendingAction?.kind === "logout-all"
            ? t("account.confirmLogoutAll")
            : t("common.confirm")
        }
        description={
          pendingAction?.kind === "revoke"
            ? (
                pendingAction.session.is_current
                  ? t("account.confirmRevokeCurrentDescription")
                  : t("account.confirmRevokeDescription")
              )
            : pendingAction?.kind === "unlink-oauth"
              ? t("account.confirmUnlinkOAuthDescription")
            : pendingAction?.kind === "logout-others"
              ? t("account.confirmLogoutOthersDescription")
              : t("account.confirmLogoutAllDescription")
        }
        isLoading={isActionLoading}
        isOpen={pendingAction !== null}
        onCancel={() => setPendingAction(null)}
        onConfirm={confirmPendingAction}
        title={
          pendingAction?.kind === "logout-all"
            ? t("account.confirmLogoutAllTitle")
            : pendingAction?.kind === "unlink-oauth"
              ? t("account.confirmUnlinkOAuthTitle")
            : t("account.confirmRevokeTitle")
        }
      />
    </section>
  );
}
