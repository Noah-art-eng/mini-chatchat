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
import { useI18n } from "../../i18n";

type PendingAction =
  | { kind: "revoke"; session: AccountSession }
  | { kind: "logout-others" }
  | { kind: "logout-all" }
  | { kind: "unlink-oauth"; provider: OAuthProviderStatus }
  | null;

/** 用途：负责 formatDate 的界面或数据处理职责。 */
function formatDate(value: string | null) {
  if (!value) return "Never";

  try {
    return new Date(value.replace(" ", "T")).toLocaleString();
  } catch {
    return value;
  }
}

/** 用途：负责 AccountPage 的界面或数据处理职责。 */
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
    /** 用途：负责 setIsLoadingSessions 的界面或数据处理职责。 */
    setIsLoadingSessions(true);
    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);

    try {
      const response = await listAuthSessions();
      /** 用途：负责 setSessions 的界面或数据处理职责。 */
      setSessions(response.sessions);
    } catch {
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(t("account.sessionsLoadFailed"));
    } finally {
      /** 用途：负责 setIsLoadingSessions 的界面或数据处理职责。 */
      setIsLoadingSessions(false);
    }
  }, [t]);

  const refreshOAuthProviders = useCallback(async () => {
    /** 用途：负责 setIsLoadingProviders 的界面或数据处理职责。 */
    setIsLoadingProviders(true);
    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);

    try {
      const response = await listOAuthProviders();
      /** 用途：负责 setOAuthProviders 的界面或数据处理职责。 */
      setOAuthProviders(response.providers);
    } catch {
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(t("account.oauthLoadFailed"));
    } finally {
      /** 用途：负责 setIsLoadingProviders 的界面或数据处理职责。 */
      setIsLoadingProviders(false);
    }
  }, [t]);

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    /** 用途：负责 setDisplayName 的界面或数据处理职责。 */
    setDisplayName(auth.session.displayName);
  }, [auth.session.displayName]);

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    if (!auth.session.isGuest) {
      /** 用途：负责 refreshSessions 的界面或数据处理职责。 */
      refreshSessions().catch(() => undefined);
      /** 用途：负责 refreshOAuthProviders 的界面或数据处理职责。 */
      refreshOAuthProviders().catch(() => undefined);
    }
  }, [auth.session.isGuest, refreshOAuthProviders, refreshSessions]);

  /** 用途：负责 handleProfileSubmit 的界面或数据处理职责。 */
  async function handleProfileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    /** 用途：负责 setIsSavingProfile 的界面或数据处理职责。 */
    setIsSavingProfile(true);
    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);

    try {
      await auth.updateAccount({ displayName });
      /** 用途：负责 showToast 的界面或数据处理职责。 */
      showToast({ message: t("account.profileUpdated"), variant: "success" });
    } catch {
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(t("account.profileUpdateFailed"));
    } finally {
      /** 用途：负责 setIsSavingProfile 的界面或数据处理职责。 */
      setIsSavingProfile(false);
    }
  }

  /** 用途：负责 confirmPendingAction 的界面或数据处理职责。 */
  async function confirmPendingAction() {
    if (!pendingAction) return;

    /** 用途：负责 setIsActionLoading 的界面或数据处理职责。 */
    setIsActionLoading(true);
    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);

    try {
      if (pendingAction.kind === "revoke") {
        const response = await revokeAuthSession(pendingAction.session.session_id);
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast({ message: t("account.sessionRevoked"), variant: "success" });
        if (response.revoked_current) {
          auth.resetToGuest();
          return;
        }
      }

      if (pendingAction.kind === "logout-others") {
        await logoutOtherSessions();
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast({ message: t("account.otherSessionsRevoked"), variant: "success" });
      }

      if (pendingAction.kind === "logout-all") {
        await logoutAllSessions();
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast({ message: t("account.allSessionsRevoked"), variant: "success" });
        auth.resetToGuest();
        return;
      }

      if (pendingAction.kind === "unlink-oauth") {
        await unlinkOAuthProvider(pendingAction.provider.provider);
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast({ message: t("account.oauthUnlinked"), variant: "success" });
        await refreshOAuthProviders();
      }

      await refreshSessions();
    } catch {
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(t("account.sessionActionFailed"));
    } finally {
      /** 用途：负责 setIsActionLoading 的界面或数据处理职责。 */
      setIsActionLoading(false);
      /** 用途：负责 setPendingAction 的界面或数据处理职责。 */
      setPendingAction(null);
    }
  }

  /** 用途：负责 handleOAuthLink 的界面或数据处理职责。 */
  async function handleOAuthLink(provider: OAuthProviderStatus) {
    /** 用途：负责 setError 的界面或数据处理职责。 */
    setError(null);
    try {
      const response = await startOAuthLink(provider.provider);
      window.location.assign(response.authorization_url);
    } catch {
      /** 用途：负责 setError 的界面或数据处理职责。 */
      setError(t("account.oauthLinkFailed"));
    }
  }

  /** 用途：负责 providerIcon 的界面或数据处理职责。 */
  function providerIcon(provider: string) {
    /** 用途：负责 return 的界面或数据处理职责。 */
    return (
      <span className="oauth-provider-mark" aria-hidden="true">
        {provider === "github" ? "GH" : "G"}
      </span>
    );
  }

  if (auth.session.isGuest) {
    /** 用途：负责 return 的界面或数据处理职责。 */
    return (
      <section className="account-page">
        <div className="account-hero">
          <p className="auth-eyebrow">{t("account.privateWorkspace")}</p>
          <h1>{t("account.signInRequiredTitle")}</h1>
          <p>{t("account.signInRequiredDescription")}</p>
        </div>
      </section>
    );
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <section className="account-page" data-testid="account-page">
      <header className="account-hero">
        <div className="account-hero-icon" aria-hidden="true">
          <Icon icon={UserRound} size="lg" />
        </div>
        <div>
          <p className="auth-eyebrow">{t("account.title")}</p>
          <h1>{t("account.heading")}</h1>
          <p>{t("account.subtitle")}</p>
        </div>
      </header>

      {error && <div className="account-error">{error}</div>}

      <div className="account-grid">
        <section className="account-card" data-testid="profile-section">
          <div className="account-card-heading">
            <Icon icon={UserRound} size="md" />
            <div>
              <h2>{t("account.profile")}</h2>
              <p>{t("account.profileDescription")}</p>
            </div>
          </div>

          <form className="account-form" onSubmit={handleProfileSubmit}>
            <label>
              <span>{t("account.displayName")}</span>
              <input
                maxLength={80}
                onChange={event => setDisplayName(event.target.value)}
                value={displayName}
              />
            </label>
            <div className="account-readonly-grid">
              <div>
                <span>{t("account.email")}</span>
                <strong>{auth.session.email}</strong>
              </div>
              <div>
                <span>{t("account.authProvider")}</span>
                <strong>{auth.session.authProvider}</strong>
              </div>
              <div>
                <span>{t("account.createdAt")}</span>
                <strong>{formatDate(auth.session.createdAt)}</strong>
              </div>
            </div>
            <Button loading={isSavingProfile} type="submit" variant="primary">
              {t("account.saveProfile")}
            </Button>
          </form>
        </section>

        <section className="account-card" data-testid="oauth-section">
          <div className="account-card-heading">
            <Icon icon={Link2} size="md" />
            <div>
              <h2>{t("account.connectedAccounts")}</h2>
              <p>{t("account.connectedAccountsDescription")}</p>
            </div>
          </div>
          {isLoadingProviders && (
            <div className="account-session-empty">{t("account.loadingProviders")}</div>
          )}
          {!isLoadingProviders && (
            <div className="oauth-provider-list">
              {oauthProviders.map(provider => (
                <article className="oauth-provider-row" key={provider.provider}>
                  <div className="oauth-provider-main">
                    {providerIcon(provider.provider)}
                    <div>
                      <strong>{provider.label}</strong>
                      <p>
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

        <section className="account-card" data-testid="security-section">
          <div className="account-card-heading">
            <Icon icon={ShieldCheck} size="md" />
            <div>
              <h2>{t("account.security")}</h2>
              <p>{t("account.securityDescription")}</p>
            </div>
          </div>
          <div className="account-security-actions">
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

      <section className="account-card account-sessions" data-testid="session-list">
        <div className="account-card-heading">
          <Icon icon={Monitor} size="md" />
          <div>
            <h2>{t("account.sessions")}</h2>
            <p>{t("account.sessionsDescription")}</p>
          </div>
        </div>

        {isLoadingSessions && (
          <div className="account-session-empty">{t("account.loadingSessions")}</div>
        )}

        {!isLoadingSessions && sessions.length === 0 && (
          <div className="account-session-empty">{t("account.noSessions")}</div>
        )}

        {!isLoadingSessions && sessions.map(session => (
          <article
            className={session.is_current ? "session-row current" : "session-row"}
            data-testid={`session-row-${session.is_current ? "current" : "other"}`}
            key={session.session_id}
          >
            <div className="session-row-main">
              <div className="session-row-title">
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
              <p>{session.device}</p>
              <dl className="session-row-meta">
                <div>
                  <dt>{t("account.lastActivity")}</dt>
                  <dd>{formatDate(session.last_used_at || session.created_at)}</dd>
                </div>
                <div>
                  <dt>{t("account.expiresAt")}</dt>
                  <dd>{formatDate(session.expires_at)}</dd>
                </div>
                {session.ip_address && (
                  <div>
                    <dt>{t("account.ipAddress")}</dt>
                    <dd>{session.ip_address}</dd>
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
