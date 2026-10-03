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

function getConversationGroupLabelKey(key: string) {
  if (key === "today") return "conversations.groupToday";
  if (key === "yesterday") return "conversations.groupYesterday";
  if (key === "lastWeek") return "conversations.groupLastWeek";
  if (key === "thisMonth") return "conversations.groupThisMonth";
  return "conversations.groupOlder";
}

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

  useEffect(() => {
    refreshConversations().catch(() => undefined);
  }, [refreshConversations]);

  useEffect(() => {
    function handleNewConversationShortcut(event: KeyboardEvent) {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "n") {
        return;
      }

      event.preventDefault();
      onStartNewConversation();
    }

    window.addEventListener("keydown", handleNewConversationShortcut);
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

  function getTitle(conversation: Conversation) {
    return conversation.title || `${t("chat.conversation")} ${conversation.id}`;
  }

  function renameConversationItem(conversation: Conversation) {
    const title = getTitle(conversation);
    const nextTitle = window.prompt(t("conversations.renamePrompt"), title);
    setOpenMenuId(null);
    if (nextTitle === null) return;
    if (!nextTitle.trim()) {
      window.alert(t("conversations.emptyTitle"));
      return;
    }

    renameConversationById(conversation.id, nextTitle)
      .then(() => {
        showToast({ message: t("conversations.renameSuccess"), variant: "success" });
      })
      .catch(error => {
        console.error(error);
        showToast({ message: t("conversations.renameFailed"), variant: "error" });
      });
  }

  async function confirmDeleteConversation() {
    if (!conversationToDelete) return;

    const deletedConversationId = conversationToDelete.id;
    const nextConversation = conversations.find(
      conversation => conversation.id !== deletedConversationId
    );

    setConversationToDelete(null);
    try {
      await deleteConversationById(deletedConversationId);
      showToast({ message: t("conversations.deleteSuccess"), variant: "success" });
    } catch (error) {
      console.error(error);
      showToast({ message: t("conversations.deleteFailed"), variant: "error" });
      return;
    }

    if (deletedConversationId === conversationId && nextConversation) {
      await loadConversation(nextConversation);
    }
  }

  async function confirmDeleteAllConversations() {
    const conversationIds = conversations.map(conversation => conversation.id);
    setIsDeletingAll(true);
    try {
      await deleteConversationsByIds(conversationIds);
      showToast({ message: t("conversations.clearAllSuccess"), variant: "success" });
    } catch (error) {
      console.error(error);
      showToast({ message: t("conversations.clearAllFailed"), variant: "error" });
    } finally {
      setIsDeletingAll(false);
      setIsDeleteAllOpen(false);
    }
  }

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
                            setOpenMenuId(null);
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
          confirmDeleteAllConversations().catch(console.error);
        }}
        title={t("conversations.clearAllTitle")}
      />
    </section>
  );
}
