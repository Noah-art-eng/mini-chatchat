import type { ReactNode } from "react";
import { Button } from "./ui";
import { useI18n } from "../i18n";
import { cx } from "./ui/utils";
import { contextStyles } from "./ContextPanel/contextStyles";

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
  return (
    <>
      <button
        className={contextStyles.mobileTrigger}
        onClick={() => onOpen?.()}
        type="button"
      >
        {title}
      </button>
      {isOpen && (
        <button
          aria-label={t("common.close")}
          className={contextStyles.mobileBackdrop}
          onClick={() => onClose?.()}
          type="button"
        />
      )}
      <aside
        aria-label={ariaLabel}
        className={cx(
          contextStyles.panel,
          `shell-context-panel--${workspace}`,
          isOpen ? contextStyles.open : contextStyles.collapsed,
          className
        )}
      >
        <header className={contextStyles.header}>
          <div>
            <p className="eyebrow">{t("chat.details")}</p>
            <h2>{title}</h2>
          </div>
          {onClose && (
            <Button
              className={contextStyles.close}
              onClick={onClose}
              size="sm"
              variant="ghost"
            >
              {t("common.close")}
            </Button>
          )}
        </header>
        {tabs.length > 0 && (
          <div className={contextStyles.tabs} role="tablist">
            {tabs.map(tab => (
              <button
                aria-selected={activeTab === tab.id}
                className={cx(contextStyles.tab, activeTab === tab.id && contextStyles.tabActive)}
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
        <div className={contextStyles.body}>{children}</div>
      </aside>
    </>
  );
}
