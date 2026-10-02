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
import { cx } from "./ui/utils";
import { shellStyles } from "./shellStyles";

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
    <header className={shellStyles.topBar}>
      <div className={cx(shellStyles.topBarGroup, shellStyles.topBarStatus)}>
        <strong className={shellStyles.page}>
          {t(`nav.${activePage === "kb" ? "knowledgeBase" : activePage}`)}
        </strong>
        {(activePage === "chat" || activePage === "agent") && (
          <span className={shellStyles.context}>{t(`modes.${chatMode}`)}</span>
        )}
        {(activePage === "chat" || activePage === "agent" || activePage === "kb") && (
          <span className={shellStyles.context}>
            {t("app.currentKb")} <strong>{kbName}</strong>
          </span>
        )}
        <span
          className={cx(shellStyles.health, `status-${health?.status || "loading"}`)}
          title={`${health?.status || t("common.loading")} · ${health?.version ? `v${health.version}` : "v1.0"}`}
        >
          <Icon
            icon={Activity}
            size="sm"
            tone={health?.status === "ok" ? "success" : "warning"}
          />
          <span>{health?.status || t("common.loading")}</span>
        </span>
        <span className={shellStyles.version}>
          {health?.version ? `v${health.version}` : "v1.0"}
        </span>
      </div>
      <div className={cx(shellStyles.topBarGroup, shellStyles.actions)}>
        {session.isGuest ? (
          <div className={shellStyles.authActions} aria-label={t("auth.session")}>
            <button className={shellStyles.authButton} onClick={() => navigate("/login")} type="button">
              {t("auth.signIn")}
            </button>
            <button className={shellStyles.authButton} onClick={() => navigate("/register")} type="button">
              {t("auth.register")}
            </button>
          </div>
        ) : (
          <div className={shellStyles.authActions} aria-label={t("auth.session")}>
            <span className={shellStyles.user}>
              {session.displayName || session.email}
            </span>
            <button className={shellStyles.authButton} onClick={() => navigate("/account")} type="button">
              {t("account.menu")}
            </button>
            <button className={shellStyles.authButton} onClick={() => logout().catch(console.error)} type="button">
              {t("account.logout")}
            </button>
          </div>
        )}
        <LanguageSwitcher />
      </div>
    </header>
  );
}
