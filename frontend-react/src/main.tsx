import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./pages/App";
import { ConversationProvider } from "./stores/conversationStore";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ConversationProvider>
      <App />
    </ConversationProvider>
  </React.StrictMode>
);
