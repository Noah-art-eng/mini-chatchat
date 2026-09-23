import type { ReactNode } from "react";
import { useState } from "react";
import { Button } from "./ui";
import { useI18n } from "../i18n";

export type ContextPanelTab = {
  id: string;
  label: string;
};

type ContextPanelProps = {
  activeTab?: string;
  ariaLabel: string;
  children: ReactNode;
  className?: string;
  isOpen?: boolean;
  onChangeTab?: (tab: string) => void;
  onClose?: () => void;
  onOpen?: () => void;
  tabs?: ContextPanelTab[];
  title: string;
  workspace: "chat" | "agent" | "knowledge" | "system";
};

/** 用途：负责 ContextPanel 的界面或数据处理职责。 */
export function ContextPanel({
  activeTab,
  ariaLabel,
  children,
  className,
  isOpen = true,
  onChangeTab,
  onClose,
  onOpen,
  tabs = [],
  title,
  workspace
}: ContextPanelProps) {
  const { t } = useI18n();
  const [isLocalOpen, setIsLocalOpen] = useState(false);

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <>
      <button
        className="context-panel-mobile-trigger"
        onClick={() => {
          /** 用途：负责 setIsLocalOpen 的界面或数据处理职责。 */
          setIsLocalOpen(true);
          onOpen?.();
        }}
        type="button"
      >
        {title}
      </button>
      {isOpen && isLocalOpen && (
        <button
          aria-label={t("common.close")}
          className="context-panel-mobile-backdrop"
          onClick={() => {
            /** 用途：负责 setIsLocalOpen 的界面或数据处理职责。 */
            setIsLocalOpen(false);
            onClose?.();
          }}
          type="button"
        />
      )}
      <aside
        aria-label={ariaLabel}
        className={[
          "context-panel",
          "shell-context-panel",
          `shell-context-panel--${workspace}`,
          isOpen ? "open" : "collapsed",
          isLocalOpen && "mobile-open",
          className || ""
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <header className="shell-context-panel__header">
          <div>
            <p className="eyebrow">{t("chat.details")}</p>
            <h2>{title}</h2>
          </div>
          {onClose && (
            <Button
              className="shell-context-panel__close"
              onClick={() => {
                /** 用途：负责 setIsLocalOpen 的界面或数据处理职责。 */
                setIsLocalOpen(false);
                /** 用途：负责 onClose 的界面或数据处理职责。 */
                onClose();
              }}
              size="sm"
              variant="ghost"
            >
              {t("common.close")}
            </Button>
          )}
        </header>
        {tabs.length > 0 && (
          <div className="context-tabs" role="tablist">
            {tabs.map(tab => (
              <button
                aria-selected={activeTab === tab.id}
                className={activeTab === tab.id ? "active" : ""}
                key={tab.id}
                onClick={() => onChangeTab?.(tab.id)}
                role="tab"
                type="button"
              >
                {tab.label}
              </button>
            ))}
          </div>
        )}
        <div className="context-panel-body">{children}</div>
      </aside>
    </>
  );
}
