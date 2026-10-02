import type { ReactNode } from "react";
import { PanelLeft } from "lucide-react";
import { BrandIdentity } from "./brand";
import { SidebarNavigation } from "./SidebarNavigation";
import { TopBar } from "./TopBar";
import type { AppPage } from "../pages/App";
import { useI18n } from "../i18n";
import { Icon } from "./ui";
import { cx } from "./ui/utils";
import { shellStyles } from "./shellStyles";

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
    <div className={shellStyles.shell}>
      <div className={shellStyles.ambient} aria-hidden="true" />
      <aside className={shellStyles.rail} aria-label={t("app.workspaceLabel")}>
        <BrandIdentity onGoHome={onGoHome} />
        <SidebarNavigation
          activePage={activePage}
          onSelectPage={onSelectPage}
        />
        <div className={shellStyles.footnote}>
          <span className={shellStyles.footnoteLabel}>{t("app.workspaceLabel")}</span>
          <strong className={shellStyles.footnoteValue}>{t("app.productStatus")}</strong>
        </div>
      </aside>

      <div className={shellStyles.workspace}>
        <TopBar activePage={activePage} />
        <div
          className={cx(shellStyles.body, conversationSidebar ? "with-conversation-dock" : "full-width")}
        >
          {conversationSidebar && (
            <>
              <button
                aria-label={isConversationSidebarOpen ? t("common.close") : t("conversations.title")}
                className={shellStyles.mobileToggle}
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
                  className={shellStyles.mobileBackdrop}
                  onClick={onToggleConversationSidebar}
                  type="button"
                />
              )}
              <aside
                aria-label={t("conversations.title")}
                className={cx(shellStyles.dock, isConversationSidebarOpen && "open")}
              >
                {conversationSidebar}
              </aside>
            </>
          )}
          <main className={shellStyles.main}>{children}</main>
        </div>
      </div>
    </div>
  );
}
