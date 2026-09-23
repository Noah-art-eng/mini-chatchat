import { Bot, Library, Lock, MessageSquare, Settings } from "lucide-react";
import type { AppPage } from "../pages/App";
import { useI18n } from "../i18n";
import { Icon } from "./ui";
import { useAuth } from "../auth";

type SidebarNavigationProps = {
  activePage: AppPage;
  onSelectPage: (page: AppPage) => void;
};

const navItems: Array<{ page: AppPage; labelKey: string; icon: typeof MessageSquare }> = [
  { page: "chat", labelKey: "nav.chat", icon: MessageSquare },
  { page: "kb", labelKey: "nav.knowledgeBase", icon: Library },
  { page: "agent", labelKey: "nav.agent", icon: Bot },
  { page: "settings", labelKey: "nav.settings", icon: Settings }
];

/** 用途：负责 SidebarNavigation 的界面或数据处理职责。 */
export function SidebarNavigation({
  activePage,
  onSelectPage
}: SidebarNavigationProps) {
  const { t } = useI18n();
  const auth = useAuth();

  /** 用途：负责 isLocked 的界面或数据处理职责。 */
  function isLocked(page: AppPage) {
    /** 用途：负责 return 的界面或数据处理职责。 */
    return (
      (page === "kb" && !auth.can("can_manage_kb")) ||
      (page === "agent" && !auth.can("can_use_agent"))
    );
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <nav className="primary-navigation" aria-label="Primary navigation">
      {navItems.map(item => (
        <button
          aria-current={item.page === activePage ? "page" : undefined}
          aria-label={t(item.labelKey)}
          className={item.page === activePage ? "active" : ""}
          data-testid={`nav-${item.page}`}
          key={item.page}
          onClick={() => onSelectPage(item.page)}
          type="button"
        >
          <span aria-hidden="true" className="nav-glyph">
            <Icon icon={item.icon} size="sm" />
          </span>
          <span>{t(item.labelKey)}</span>
          {isLocked(item.page) && (
            <span aria-label="Sign in required" className="nav-lock">
              <Icon icon={Lock} size="sm" />
            </span>
          )}
        </button>
      ))}
    </nav>
  );
}
