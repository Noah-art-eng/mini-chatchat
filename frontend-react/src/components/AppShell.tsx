import type { ReactNode } from "react";
import { PanelLeft } from "lucide-react";
import { BrandIdentity } from "./brand";
import { SidebarNavigation } from "./SidebarNavigation";
import { TopBar } from "./TopBar";
import type { AppPage } from "../pages/App";
import { useI18n } from "../i18n";
import { Icon } from "./ui";

type AppShellProps = {
  activePage: AppPage;
  children: ReactNode;
  conversationSidebar?: ReactNode;
  isConversationSidebarOpen: boolean;
  onSelectPage: (page: AppPage) => void;
  onGoHome: () => void;
  onToggleConversationSidebar: () => void;
};

/** 用途：负责 AppShell 的界面或数据处理职责。 */
export function AppShell({
  activePage,
  children,
  conversationSidebar,
  isConversationSidebarOpen,
  onGoHome,
  onSelectPage,
  onToggleConversationSidebar
}: AppShellProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className="app-shell">
      <div className="ambient-layer" aria-hidden="true" />
      <aside className="app-rail" aria-label={t("app.workspaceLabel")}>
        <BrandIdentity onGoHome={onGoHome} />
        <SidebarNavigation
          activePage={activePage}
          onSelectPage={onSelectPage}
        />
        <div className="rail-footnote">
          <span>{t("app.workspaceLabel")}</span>
          <strong>{t("app.productStatus")}</strong>
        </div>
      </aside>

      <div className="app-workspace">
        <TopBar activePage={activePage} />
        <div
          className={
            conversationSidebar
              ? "workspace-body with-conversation-dock"
              : "workspace-body full-width"
          }
        >
          {conversationSidebar && (
            <>
              <button
                aria-label={isConversationSidebarOpen ? t("common.close") : t("conversations.title")}
                className="mobile-sidebar-toggle"
                onClick={onToggleConversationSidebar}
                type="button"
              >
                <Icon icon={PanelLeft} size="sm" />
                {isConversationSidebarOpen
                  ? t("common.close")
                  : t("conversations.title")}
              </button>
              {isConversationSidebarOpen && (
                <button
                  aria-label={t("common.close")}
                  className="mobile-sidebar-backdrop"
                  onClick={onToggleConversationSidebar}
                  type="button"
                />
              )}
              <aside
                aria-label={t("conversations.title")}
                className={
                  isConversationSidebarOpen
                    ? "conversation-dock open"
                    : "conversation-dock"
                }
              >
                {conversationSidebar}
              </aside>
            </>
          )}
          <main className="workspace-main">{children}</main>
        </div>
      </div>
    </div>
  );
}
