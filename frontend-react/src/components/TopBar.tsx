import { useEffect, useState } from "react";
import { Activity } from "lucide-react";
import { getHealth, type HealthResponse } from "../api/system";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { Icon } from "./ui";
import { useI18n } from "../i18n";
import { useAuth } from "../auth";
import { useConversationStore } from "../stores/conversationStore";
import type { AppPage } from "../pages/App";
import { useNavigate } from "../router";

type TopBarProps = {
  activePage: AppPage;
};

/** 用途：负责 TopBar 的界面或数据处理职责。 */
export function TopBar({ activePage }: TopBarProps) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { logout, session } = useAuth();
  const { chatMode, kbName } = useConversationStore();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    let ignore = false;

    /** 用途：负责 getHealth 的界面或数据处理职责。 */
    getHealth()
      .then(result => {
        if (ignore) return;
        /** 用途：负责 setHealth 的界面或数据处理职责。 */
        setHealth(result);
      })
      .catch(() => undefined);

    /** 用途：负责 return 的界面或数据处理职责。 */
    return () => {
      ignore = true;
    };
  }, []);

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <header className="top-bar">
      <div className="top-bar-status">
        <strong className="top-bar-page">
          {t(`nav.${activePage === "kb" ? "knowledgeBase" : activePage}`)}
        </strong>
        {(activePage === "chat" || activePage === "agent") && (
          <span className="top-bar-context">{t(`modes.${chatMode}`)}</span>
        )}
        {(activePage === "chat" || activePage === "agent" || activePage === "kb") && (
          <span className="top-bar-context">
            {t("app.currentKb")} <strong>{kbName}</strong>
          </span>
        )}
        <span
          className={`top-bar-health status-${health?.status || "loading"}`}
          title={`${health?.status || t("common.loading")} · ${health?.version ? `v${health.version}` : "v1.0"}`}
        >
          <Icon
            icon={Activity}
            size="sm"
            tone={health?.status === "ok" ? "success" : "warning"}
          />
          <span>{health?.status || t("common.loading")}</span>
        </span>
        <span className="top-bar-version">
          {health?.version ? `v${health.version}` : "v1.0"}
        </span>
      </div>
      <div className="top-bar-actions">
        {session.isGuest ? (
          <div className="top-bar-auth-actions" aria-label={t("auth.session")}>
            <button onClick={() => navigate("/login")} type="button">
              {t("auth.signIn")}
            </button>
            <button onClick={() => navigate("/register")} type="button">
              {t("auth.register")}
            </button>
          </div>
        ) : (
          <div className="top-bar-auth-actions" aria-label={t("auth.session")}>
            <span className="top-bar-user-pill">
              {session.displayName || session.email}
            </span>
            <button onClick={() => navigate("/account")} type="button">
              {t("account.menu")}
            </button>
            <button onClick={() => logout().catch(console.error)} type="button">
              {t("account.logout")}
            </button>
          </div>
        )}
        <LanguageSwitcher />
      </div>
    </header>
  );
}
