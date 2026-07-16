import { useEffect } from "react";
import { useConversationStore } from "../../stores/conversationStore";

export function ConversationSidebar() {
  const {
    conversations,
    conversationId,
    isLoadingConversations,
    deleteConversationById,
    loadConversation,
    renameConversationById,
    refreshConversations,
    startNewConversation
  } = useConversationStore();

  useEffect(() => {
    refreshConversations().catch(console.error);
  }, [refreshConversations]);

  return (
    <section className="conversation-sidebar" aria-label="Conversations">
      <div className="sidebar-header">
        <div>
          <p className="eyebrow">Mini ChatChat</p>
          <h1>Conversations</h1>
        </div>
        <button type="button" onClick={startNewConversation}>
          New
        </button>
      </div>

      <div className="conversation-list">
        {isLoadingConversations && <p className="muted">Loading...</p>}

        {!isLoadingConversations && conversations.length === 0 && (
          <p className="muted">No conversations yet.</p>
        )}

        {conversations.map(conversation => {
          const title = conversation.title || `Conversation ${conversation.id}`;

          return (
            <article className="conversation-item" key={conversation.id}>
              <button
                className={
                  conversation.id === conversationId
                    ? "conversation-row active"
                    : "conversation-row"
                }
                onClick={() => loadConversation(conversation)}
                type="button"
              >
                <span>{title}</span>
                <small>
                  Updated {conversation.updated_time || conversation.create_time}
                </small>
              </button>

              <div className="conversation-actions">
                <button
                  data-testid={`rename-conversation-${conversation.id}`}
                  onClick={() => {
                    const nextTitle = window.prompt("Rename conversation", title);
                    if (nextTitle === null) return;
                    if (!nextTitle.trim()) {
                      window.alert("Conversation title cannot be empty.");
                      return;
                    }

                    renameConversationById(
                      conversation.id,
                      nextTitle
                    ).catch(console.error);
                  }}
                  type="button"
                >
                  Rename
                </button>
                <button
                  data-testid={`delete-conversation-${conversation.id}`}
                  onClick={() => {
                    if (!window.confirm(`Delete "${title}"?`)) return;

                    deleteConversationById(conversation.id).catch(console.error);
                  }}
                  type="button"
                >
                  Delete
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
