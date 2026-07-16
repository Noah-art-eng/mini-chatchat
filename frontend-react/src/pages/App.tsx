import { KnowledgeBasePanel } from "../components/KnowledgeBasePanel";
import { ChatArea } from "../features/chat/ChatArea";
import { ConversationSidebar } from "../features/conversation/ConversationSidebar";
import { AppLayout } from "../layouts/AppLayout";

export function App() {
  return (
    <AppLayout
      aside={<KnowledgeBasePanel />}
      main={<ChatArea />}
      sidebar={<ConversationSidebar />}
    />
  );
}
