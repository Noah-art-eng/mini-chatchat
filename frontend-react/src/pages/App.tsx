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
import { useI18n } from "../i18n";

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

function getPageFromPath(pathname: string): AppPage {
  if (pathname.startsWith("/knowledge")) return "kb";
  if (pathname.startsWith("/agent")) return "agent";
  if (pathname.startsWith("/account")) return "account";
  if (pathname.startsWith("/system")) return "settings";
  return "chat";
}

/**
 * React 应用的页面装配入口。
 * 这里根据路由和当前权限选择工作区；具体聊天、知识库和系统业务留给各 feature 处理。
 */
export function App() {
  const { t } = useI18n();
  const location = useLocation();
  const navigate = useNavigate();
  const auth = useAuth();
  const { refreshConversations, startNewConversation } = useConversationStore();
  const activePage = useMemo(
    () => getPageFromPath(location.pathname),
    [location.pathname]
  );
  const [isConversationSidebarOpen, setIsConversationSidebarOpen] =
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

  useEffect(() => {
    if (auth.isLoading) return;

    const completed = auth.isAuthenticated
      ? Boolean(auth.preferences?.onboarding_completed)
      : isOnboardingCompleted();

    if (!completed) {
      setIsWelcomeOpen(true);
    }
  }, [auth.isAuthenticated, auth.isLoading, auth.preferences?.onboarding_completed]);

  useEffect(() => {
    if (auth.isLoading) return;
    // 登录身份变化后清掉上一用户的会话状态，再按新 user scope 重新读取侧栏列表。
    startNewConversation();
    refreshConversations().catch(() => undefined);
  }, [auth.isLoading, auth.session.id, refreshConversations, startNewConversation]);

  useLayoutEffect(() => {
    if (location.pathname === "/") {
      navigate(pagePaths.chat, { replace: true });
      return;
    }

    document.title = pageTitles[activePage];
  }, [activePage, location.pathname, navigate]);

  function completeWelcomeGuide() {
    if (auth.isAuthenticated) {
      auth.updatePreferences({ onboarding_completed: true }).catch(() => undefined);
    } else {
      setOnboardingCompleted(true);
    }
    setIsWelcomeOpen(false);
  }

  function startFreshConversation() {
    startNewConversation();
    navigate(pagePaths.chat);
    setIsConversationSidebarOpen(false);
    window.setTimeout(() => {
      document
        .querySelector<HTMLTextAreaElement>(".chat-composer textarea")
        ?.focus();
    }, 0);
  }

  if (isAuthPage) {
    return location.pathname.startsWith("/register") ? (
      <RegisterPage />
    ) : (
      <LoginPage />
    );
  }

  return (
    <>
      <AppShell
      activePage={activePage}
      conversationSidebar={
        showConversationSidebar ? (
          <ConversationSidebar onStartNewConversation={startFreshConversation} />
        ) : undefined
      }
      isConversationSidebarOpen={isConversationSidebarOpen}
      onSelectPage={page => {
        navigate(pagePaths[page]);
        setIsConversationSidebarOpen(false);
      }}
      onGoHome={() => {
        navigate(pagePaths.chat);
        setIsConversationSidebarOpen(false);
      }}
      onToggleConversationSidebar={() =>
        setIsConversationSidebarOpen(isOpen => !isOpen)
      }
    >
      {!canUseCurrentPage && (
        <section className="restricted-workspace max-w-[560px] self-center justify-self-center rounded-mc-xl border border-solid border-mc-border-subtle bg-mc-surface p-mc-8 text-center shadow-mc-sm">
          <p className="auth-eyebrow m-0 text-mc-label font-mc-semibold tracking-[.08em] text-mc-brand uppercase">
            {t("auth.privateWorkspace")}
          </p>
          <h1 className="m-0 text-mc-heading leading-[var(--line-height-heading)] text-mc-text">
            {t("auth.restrictedTitle")}
          </h1>
          <p className="mt-mc-2 mb-0 text-mc-secondary">
            {t("auth.restrictedDescription")}
          </p>
          <div className="restricted-actions mt-mc-5 inline-flex items-center justify-center gap-mc-4">
            <Button onClick={() => navigate("/login")} variant="primary">
              {t("auth.signIn")}
            </Button>
            <Link className="font-mc-medium text-mc-brand no-underline" to="/register">
              {t("auth.createAccount")}
            </Link>
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
