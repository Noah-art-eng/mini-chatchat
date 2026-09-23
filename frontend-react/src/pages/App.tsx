import { useEffect, useLayoutEffect, useMemo, useState } from "react";
import { AppShell } from "../components/AppShell";
import { ModeIntroDialog, WelcomeDialog } from "../components/onboarding";
import { ChatArea } from "../features/chat/ChatArea";
import { ConversationSidebar } from "../features/conversation/ConversationSidebar";
import { AccountPage } from "../features/account/AccountPage";
import { KnowledgeBasePage } from "../features/kb/KnowledgeBasePage";
import { SettingsPage } from "../features/settings/SettingsPage";
import {
  isOnboardingCompleted,
  setOnboardingCompleted
} from "../onboarding/preferences";
import { LoginPage, RegisterPage, useAuth } from "../auth";
import { Button } from "../components/ui";
import { useConversationStore } from "../stores/conversationStore";
import { Link, useLocation, useNavigate } from "../router";

export type AppPage = "chat" | "kb" | "agent" | "settings" | "account";

const pagePaths: Record<AppPage, string> = {
  agent: "/agent",
  account: "/account",
  chat: "/chat",
  kb: "/knowledge",
  settings: "/system"
};

const pageTitles: Record<AppPage, string> = {
  agent: "Mini ChatChat · Agent",
  account: "Mini ChatChat · Account",
  chat: "Mini ChatChat",
  kb: "Mini ChatChat · Knowledge",
  settings: "Mini ChatChat · System"
};

/** 用途：负责 getPageFromPath 的界面或数据处理职责。 */
function getPageFromPath(pathname: string): AppPage {
  if (pathname.startsWith("/knowledge")) return "kb";
  if (pathname.startsWith("/agent")) return "agent";
  if (pathname.startsWith("/account")) return "account";
  if (pathname.startsWith("/system")) return "settings";
  return "chat";
}

/** 用途：负责 App 的界面或数据处理职责。 */
export function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const auth = useAuth();
  const { refreshConversations, startNewConversation } = useConversationStore();
  const activePage = useMemo(
    () => getPageFromPath(location.pathname),
    [location.pathname]
  );
  const [isConversationSidebarOpen, setIsConversationSidebarOpen] =
    /** 用途：负责 useState 的界面或数据处理职责。 */
    useState(false);
  const [isModeGuideOpen, setIsModeGuideOpen] = useState(false);
  const [isWelcomeOpen, setIsWelcomeOpen] = useState(false);
  const showConversationSidebar = activePage === "chat" || activePage === "agent";
  const isAuthPage =
    location.pathname.startsWith("/login") ||
    location.pathname.startsWith("/register");

  const canUseCurrentPage =
    activePage === "chat" ||
    activePage === "settings" ||
    (activePage === "account" && auth.isAuthenticated) ||
    (activePage === "kb" && auth.can("can_manage_kb")) ||
    (activePage === "agent" && auth.can("can_use_agent"));

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    if (auth.isLoading) return;

    const completed = auth.isAuthenticated
      ? Boolean(auth.preferences?.onboarding_completed)
      : isOnboardingCompleted();

    if (!completed) {
      /** 用途：负责 setIsWelcomeOpen 的界面或数据处理职责。 */
      setIsWelcomeOpen(true);
    }
  }, [auth.isAuthenticated, auth.isLoading, auth.preferences?.onboarding_completed]);

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    if (auth.isLoading) return;
    /** 用途：负责 startNewConversation 的界面或数据处理职责。 */
    startNewConversation();
    /** 用途：负责 refreshConversations 的界面或数据处理职责。 */
    refreshConversations().catch(() => undefined);
  }, [auth.isLoading, auth.session.id, refreshConversations, startNewConversation]);

  /** 用途：负责 useLayoutEffect 的界面或数据处理职责。 */
  useLayoutEffect(() => {
    if (location.pathname === "/") {
      /** 用途：负责 navigate 的界面或数据处理职责。 */
      navigate(pagePaths.chat, { replace: true });
      return;
    }

    document.title = pageTitles[activePage];
  }, [activePage, location.pathname, navigate]);

  /** 用途：负责 completeWelcomeGuide 的界面或数据处理职责。 */
  function completeWelcomeGuide() {
    if (auth.isAuthenticated) {
      auth.updatePreferences({ onboarding_completed: true }).catch(() => undefined);
    } else {
      /** 用途：负责 setOnboardingCompleted 的界面或数据处理职责。 */
      setOnboardingCompleted(true);
    }
    /** 用途：负责 setIsWelcomeOpen 的界面或数据处理职责。 */
    setIsWelcomeOpen(false);
  }

  if (isAuthPage) {
    return location.pathname.startsWith("/register") ? (
      <RegisterPage />
    ) : (
      <LoginPage />
    );
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <>
      <AppShell
      activePage={activePage}
      conversationSidebar={
        showConversationSidebar ? <ConversationSidebar /> : undefined
      }
      isConversationSidebarOpen={isConversationSidebarOpen}
      onSelectPage={page => {
        /** 用途：负责 navigate 的界面或数据处理职责。 */
        navigate(pagePaths[page]);
        /** 用途：负责 setIsConversationSidebarOpen 的界面或数据处理职责。 */
        setIsConversationSidebarOpen(false);
      }}
      onGoHome={() => {
        /** 用途：负责 navigate 的界面或数据处理职责。 */
        navigate(pagePaths.chat);
        /** 用途：负责 setIsConversationSidebarOpen 的界面或数据处理职责。 */
        setIsConversationSidebarOpen(false);
      }}
      onToggleConversationSidebar={() =>
        /** 用途：负责 setIsConversationSidebarOpen 的界面或数据处理职责。 */
        setIsConversationSidebarOpen(isOpen => !isOpen)
      }
    >
      {!canUseCurrentPage && (
        <section className="restricted-workspace">
          <p className="auth-eyebrow">Private workspace</p>
          <h1>Sign in to use this workspace</h1>
          <p>
            Knowledge management, Agent tools, MCP, filesystem, SQLite, and Developer Mode
            are available after signing in.
          </p>
          <div className="restricted-actions">
            <Button onClick={() => navigate("/login")} variant="primary">
              Sign in
            </Button>
            <Link to="/register">Create account</Link>
          </div>
        </section>
      )}
      {activePage === "chat" && canUseCurrentPage && (
        <ChatArea
          onOpenModeGuide={() => setIsModeGuideOpen(true)}
          preferredMode="chat"
        />
      )}
      {activePage === "agent" && canUseCurrentPage && (
        <ChatArea
          onOpenModeGuide={() => setIsModeGuideOpen(true)}
          preferredMode="agent"
        />
      )}
      {activePage === "kb" && canUseCurrentPage && <KnowledgeBasePage />}
      {activePage === "account" && canUseCurrentPage && <AccountPage />}
      {activePage === "settings" && canUseCurrentPage && (
        <SettingsPage
          onShowModeGuide={() => setIsModeGuideOpen(true)}
          onShowWelcomeGuide={() => setIsWelcomeOpen(true)}
        />
      )}
      </AppShell>
      <WelcomeDialog isOpen={isWelcomeOpen} onComplete={completeWelcomeGuide} />
      <ModeIntroDialog
        isOpen={isModeGuideOpen}
        onClose={() => setIsModeGuideOpen(false)}
      />
    </>
  );
}
