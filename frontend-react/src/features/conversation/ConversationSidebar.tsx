import { useEffect, useMemo, useState } from "react";
import { MessageSquare, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { Icon } from "../../components/ui";
import { cx } from "../../components/ui/utils";
import { useToast } from "../../components/ui";
import { useI18n } from "../../i18n";
import { useConversationStore } from "../../stores/conversationStore";
import type { Conversation } from "../../types/conversation";
import { conversationStyles } from "./conversationStyles";

/** 用途：负责 formatConversationTime 的界面或数据处理职责。 */
function formatConversationTime(value?: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

/** 用途：负责 getConversationGroupKey 的界面或数据处理职责。 */
function getConversationGroupKey(value?: string) {
  const date = value ? new Date(value) : new Date(0);
  const now = new Date();
  if (Number.isNaN(date.getTime())) return "older";

  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(startOfToday);
  startOfYesterday.setDate(startOfToday.getDate() - 1);
  const startOfLastWeek = new Date(startOfToday);
  startOfLastWeek.setDate(startOfToday.getDate() - 7);

  if (date >= startOfToday) return "today";
  if (date >= startOfYesterday) return "yesterday";
  if (date >= startOfLastWeek) return "lastWeek";
  return "older";
}

/** 用途：负责 getConversationGroupLabelKey 的界面或数据处理职责。 */
function getConversationGroupLabelKey(key: string) {
  if (key === "today") return "conversations.groupToday";
  if (key === "yesterday") return "conversations.groupYesterday";
  if (key === "lastWeek") return "conversations.groupLastWeek";
  if (key === "thisMonth") return "conversations.groupThisMonth";
  return "conversations.groupOlder";
}

/** 用途：负责 ConversationSidebar 的界面或数据处理职责。 */
export function ConversationSidebar({
  onStartNewConversation
}: {
  onStartNewConversation: () => void;
}) {
  const { t } = useI18n();
  const { showToast } = useToast();
  const {
    conversations,
    conversationId,
    isLoadingConversations,
    deleteConversationById,
    deleteConversationsByIds,
    loadConversation,
    renameConversationById,
    refreshConversations
  } = useConversationStore();
  const [query, setQuery] = useState("");
  const [openMenuId, setOpenMenuId] = useState<number | null>(null);
  const [conversationToDelete, setConversationToDelete] =
    useState<Conversation | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [isDeleteAllOpen, setIsDeleteAllOpen] = useState(false);
  const [isDeletingAll, setIsDeletingAll] = useState(false);

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    /** 用途：负责 refreshConversations 的界面或数据处理职责。 */
    refreshConversations().catch(() => undefined);
  }, [refreshConversations]);

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    /** 用途：负责 handleNewConversationShortcut 的界面或数据处理职责。 */
    function handleNewConversationShortcut(event: KeyboardEvent) {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "n") {
        return;
      }

      event.preventDefault();
      /** 用途：负责 startNewConversation 的界面或数据处理职责。 */
      onStartNewConversation();
    }

    window.addEventListener("keydown", handleNewConversationShortcut);
    /** 用途：负责 return 的界面或数据处理职责。 */
    return () => {
      window.removeEventListener("keydown", handleNewConversationShortcut);
    };
  }, [onStartNewConversation]);

  const filteredConversations = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return conversations;

    return conversations.filter(conversation =>
      (conversation.title || `Conversation ${conversation.id}`)
        .toLowerCase()
        .includes(normalizedQuery)
    );
  }, [conversations, query]);

  const groupedConversations = useMemo(() => {
    const groupOrder = ["today", "yesterday", "lastWeek", "thisMonth", "older"];
    const groups = new Map<string, Conversation[]>();

    filteredConversations.forEach(conversation => {
      let key = getConversationGroupKey(
        conversation.updated_time || conversation.create_time
      );
      const date = conversation.updated_time || conversation.create_time;
      if (key === "older" && date) {
        const conversationDate = new Date(date);
        const now = new Date();
        if (
          !Number.isNaN(conversationDate.getTime()) &&
          conversationDate.getFullYear() === now.getFullYear() &&
          conversationDate.getMonth() === now.getMonth()
        ) {
          key = "thisMonth";
        }
      }
      groups.set(key, [...(groups.get(key) || []), conversation]);
    });

    return groupOrder
      .map(key => ({
        key,
        label: t(getConversationGroupLabelKey(key)),
        conversations: groups.get(key) || []
      }))
      .filter(group => group.conversations.length > 0);
  }, [filteredConversations, t]);

  /** 用途：负责 getTitle 的界面或数据处理职责。 */
  function getTitle(conversation: Conversation) {
    return conversation.title || `${t("chat.conversation")} ${conversation.id}`;
  }

  /** 用途：负责 renameConversationItem 的界面或数据处理职责。 */
  function renameConversationItem(conversation: Conversation) {
    const title = getTitle(conversation);
    const nextTitle = window.prompt(t("conversations.renamePrompt"), title);
    /** 用途：负责 setOpenMenuId 的界面或数据处理职责。 */
    setOpenMenuId(null);
    if (nextTitle === null) return;
    if (!nextTitle.trim()) {
      window.alert(t("conversations.emptyTitle"));
      return;
    }

    /** 用途：负责 renameConversationById 的界面或数据处理职责。 */
    renameConversationById(conversation.id, nextTitle)
      .then(() => {
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast({ message: t("conversations.renameSuccess"), variant: "success" });
      })
      .catch(error => {
        console.error(error);
        /** 用途：负责 showToast 的界面或数据处理职责。 */
        showToast({ message: t("conversations.renameFailed"), variant: "error" });
      });
  }

  /** 用途：负责 confirmDeleteConversation 的界面或数据处理职责。 */
  async function confirmDeleteConversation() {
    if (!conversationToDelete) return;

    const deletedConversationId = conversationToDelete.id;
    const nextConversation = conversations.find(
      conversation => conversation.id !== deletedConversationId
    );

    /** 用途：负责 setConversationToDelete 的界面或数据处理职责。 */
    setConversationToDelete(null);
    try {
      await deleteConversationById(deletedConversationId);
      /** 用途：负责 showToast 的界面或数据处理职责。 */
      showToast({ message: t("conversations.deleteSuccess"), variant: "success" });
    } catch (error) {
      console.error(error);
      /** 用途：负责 showToast 的界面或数据处理职责。 */
      showToast({ message: t("conversations.deleteFailed"), variant: "error" });
      return;
    }

    if (deletedConversationId === conversationId && nextConversation) {
      await loadConversation(nextConversation);
    }
  }

  /** 用途：负责 confirmDeleteAllConversations 的界面或数据处理职责。 */
  async function confirmDeleteAllConversations() {
    const conversationIds = conversations.map(conversation => conversation.id);
    /** 用途：负责 setIsDeletingAll 的界面或数据处理职责。 */
    setIsDeletingAll(true);
    try {
      await deleteConversationsByIds(conversationIds);
      /** 用途：负责 showToast 的界面或数据处理职责。 */
      showToast({ message: t("conversations.clearAllSuccess"), variant: "success" });
    } catch (error) {
      console.error(error);
      /** 用途：负责 showToast 的界面或数据处理职责。 */
      showToast({ message: t("conversations.clearAllFailed"), variant: "error" });
    } finally {
      /** 用途：负责 setIsDeletingAll 的界面或数据处理职责。 */
      setIsDeletingAll(false);
      /** 用途：负责 setIsDeleteAllOpen 的界面或数据处理职责。 */
      setIsDeleteAllOpen(false);
    }
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <section className={conversationStyles.sidebar} aria-label={t("conversations.title")}>
      <div className={conversationStyles.header}>
        <div>
          <p className="eyebrow">{t("app.name")}</p>
          <h2>{t("conversations.title")}</h2>
        </div>
        <button
          className={conversationStyles.newButton}
          onClick={onStartNewConversation}
          type="button"
        >
          {t("conversations.new")}
          <kbd className={conversationStyles.shortcut}>{t("conversations.newShortcut")}</kbd>
        </button>
      </div>

      <label className={conversationStyles.search}>
        <span className="sr-only">{t("conversations.search")}</span>
        <input
          aria-label={t("conversations.search")}
          className={conversationStyles.searchInput}
          onChange={event => setQuery(event.target.value)}
          placeholder={t("conversations.search")}
          value={query}
        />
      </label>

      <div className={conversationStyles.actions}>
        <span className={conversationStyles.actionsLabel}>{t("conversations.recent")}</span>
        <button
          className={conversationStyles.clearButton}
          disabled={conversations.length === 0 || isDeletingAll}
          onClick={() => setIsDeleteAllOpen(true)}
          type="button"
        >
          {isDeletingAll ? t("conversations.clearing") : t("conversations.clearAll")}
        </button>
      </div>

      <div className={conversationStyles.list}>
        {isLoadingConversations && <p className="muted">{t("conversations.loading")}</p>}

        {!isLoadingConversations && filteredConversations.length === 0 && (
          <div className={conversationStyles.empty}>
            <strong className="block text-mc-body-small font-mc-semibold text-mc-text">{query ? t("conversations.noSearchResults") : t("conversations.empty")}</strong>
            <p className="mt-mc-1 text-mc-caption text-mc-muted">
              {query
                ? t("conversations.noSearchResultsHint")
                : t("conversations.emptyHint")}
            </p>
          </div>
        )}

        {groupedConversations.map((group, groupIndex) => (
          <div className={cx(conversationStyles.group, groupIndex > 0 && conversationStyles.groupAfter)} key={group.key}>
            <button
              aria-expanded={!collapsedGroups.has(group.key)}
              className={conversationStyles.groupLabel}
              onClick={() =>
                /** 用途：负责 setCollapsedGroups 的界面或数据处理职责。 */
                setCollapsedGroups(current => {
                  const next = new Set(current);
                  if (next.has(group.key)) {
                    next.delete(group.key);
                  } else {
                    next.add(group.key);
                  }
                  return next;
                })
              }
              type="button"
            >
              <span>{group.label}</span>
              <span>{group.conversations.length}</span>
            </button>
            {!collapsedGroups.has(group.key) && group.conversations.map(conversation => {
              const title = getTitle(conversation);
              const updatedTime = formatConversationTime(
                conversation.updated_time || conversation.create_time
              );

              /** 用途：负责 return 的界面或数据处理职责。 */
              return (
                <article
                  className={cx(
                    conversationStyles.item,
                    conversation.id === conversationId && conversationStyles.itemActive
                  )}
                  key={conversation.id}
                >
                  <button
                    className={conversationStyles.row}
                    onClick={() => loadConversation(conversation)}
                    type="button"
                  >
                    <Icon icon={MessageSquare} size="sm" tone="muted" />
                    <span className={conversationStyles.rowText}>
                      <span className={conversationStyles.rowTitle}>{title}</span>
                      <small className={conversationStyles.rowTime}>{t("conversations.updated", { time: updatedTime })}</small>
                    </span>
                  </button>

                  <div
                    className={cx(
                      conversationStyles.menu,
                      openMenuId === conversation.id && conversationStyles.menuOpen
                    )}
                  >
                    <button
                      aria-label={t("conversations.menu")}
                      className={conversationStyles.menuTrigger}
                      data-testid={`conversation-menu-${conversation.id}`}
                      onClick={() =>
                        /** 用途：负责 setOpenMenuId 的界面或数据处理职责。 */
                        setOpenMenuId(current =>
                          current === conversation.id ? null : conversation.id
                        )
                      }
                      type="button"
                    >
                      <Icon icon={MoreHorizontal} size="sm" />
                    </button>
                    {openMenuId === conversation.id && (
                      <div className={conversationStyles.popover}>
                        <button
                          className={conversationStyles.popoverButton}
                          data-testid={`rename-conversation-${conversation.id}`}
                          onClick={() => renameConversationItem(conversation)}
                          type="button"
                        >
                          <Icon icon={Pencil} size="sm" />
                          {t("conversations.rename")}
                        </button>
                        <button
                          className={cx(conversationStyles.popoverButton, conversationStyles.dangerButton)}
                          data-testid={`delete-conversation-${conversation.id}`}
                          onClick={() => {
                            /** 用途：负责 setOpenMenuId 的界面或数据处理职责。 */
                            setOpenMenuId(null);
                            /** 用途：负责 setConversationToDelete 的界面或数据处理职责。 */
                            setConversationToDelete(conversation);
                          }}
                          type="button"
                        >
                          <Icon icon={Trash2} size="sm" tone="danger" />
                          {t("conversations.delete")}
                        </button>
                      </div>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        ))}
      </div>

      <ConfirmDialog
        confirmLabel={t("conversations.confirmDelete")}
        description={t("conversations.deleteDescription", {
          title: conversationToDelete ? getTitle(conversationToDelete) : ""
        })}
        isOpen={Boolean(conversationToDelete)}
        onCancel={() => setConversationToDelete(null)}
        onConfirm={() => {
          /** 用途：负责 confirmDeleteConversation 的界面或数据处理职责。 */
          confirmDeleteConversation().catch(console.error);
        }}
        title={t("conversations.deleteTitle")}
      />
      <ConfirmDialog
        confirmLabel={t("conversations.confirmClearAll")}
        description={t("conversations.clearAllDescription")}
        isLoading={isDeletingAll}
        isOpen={isDeleteAllOpen}
        onCancel={() => {
          if (!isDeletingAll) setIsDeleteAllOpen(false);
        }}
        onConfirm={() => {
          /** 用途：负责 confirmDeleteAllConversations 的界面或数据处理职责。 */
          confirmDeleteAllConversations().catch(console.error);
        }}
        title={t("conversations.clearAllTitle")}
      />
    </section>
  );
}
