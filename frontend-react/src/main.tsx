import React from "react";
import ReactDOM from "react-dom/client";
import { I18nProvider } from "./i18n";
import { App } from "./pages/App";
import { ToastProvider } from "./components/ui";
import { ConversationProvider } from "./stores/conversationStore";
import { AuthProvider } from "./auth";
import { AppRouter } from "./router";
import "./styles/tokens.css";
import "./styles.css";
import "./design-system.css";
import "./styles/shell.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <AppRouter>
      <I18nProvider>
        <ToastProvider>
          <AuthProvider>
            <ConversationProvider>
              <App />
            </ConversationProvider>
          </AuthProvider>
        </ToastProvider>
      </I18nProvider>
    </AppRouter>
  </React.StrictMode>
);
