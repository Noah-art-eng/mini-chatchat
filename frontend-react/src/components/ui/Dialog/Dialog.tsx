import {
  type KeyboardEvent,
  type ReactNode,
  useEffect,
  useId,
  useRef
} from "react";
import { createPortal } from "react-dom";
import { Button } from "../Button";
import { Heading } from "../Heading";
import { InlineError } from "../InlineError";
import { Text } from "../Text";
import { cx } from "../utils";
import "./Dialog.css";

type DialogSize = "sm" | "md" | "lg";

type DialogAction = {
  disabled?: boolean;
  label: string;
  loading?: boolean;
  onClick: () => void;
  variant?: "primary" | "secondary" | "danger";
};

type DialogProps = {
  actions?: DialogAction[];
  children?: ReactNode;
  className?: string;
  description?: ReactNode;
  error?: string | null;
  initialFocus?: "first" | "cancel";
  isOpen: boolean;
  onClose: () => void;
  preventClose?: boolean;
  size?: DialogSize;
  title: ReactNode;
};

const focusableSelector = [
  "a[href]",
  "button:not([disabled])",
  "textarea:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "[tabindex]:not([tabindex='-1'])"
].join(",");

/** 用途：负责 Dialog 的界面或数据处理职责。 */
export function Dialog({
  actions = [],
  children,
  className,
  description,
  error,
  initialFocus = "first",
  isOpen,
  onClose,
  preventClose = false,
  size = "md",
  title
}: DialogProps) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef<HTMLElement | null>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  /** 用途：负责 useEffect 的界面或数据处理职责。 */
  useEffect(() => {
    if (!isOpen) return;

    previousFocusRef.current = document.activeElement as HTMLElement | null;
    const dialog = dialogRef.current;
    const focusable = getFocusable(dialog);
    const preferred =
      initialFocus === "cancel"
        ? focusable.find(element => element.dataset.dialogCancel === "true")
        : undefined;

    window.setTimeout(() => {
      (preferred || focusable[0] || dialog)?.focus();
    }, 0);

    /** 用途：负责 return 的界面或数据处理职责。 */
    return () => {
      previousFocusRef.current?.focus?.();
    };
  }, [initialFocus, isOpen]);

  if (!isOpen) return null;

  /** 用途：负责 handleKeyDown 的界面或数据处理职责。 */
  function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === "Escape" && !preventClose) {
      event.preventDefault();
      /** 用途：负责 onClose 的界面或数据处理职责。 */
      onClose();
      return;
    }

    if (event.key !== "Tab") return;

    const focusable = getFocusable(dialogRef.current);
    if (focusable.length === 0) {
      event.preventDefault();
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const active = document.activeElement;

    if (event.shiftKey && active === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  }

  /** 用途：负责 handleBackdropClick 的界面或数据处理职责。 */
  function handleBackdropClick() {
    if (!preventClose) onClose();
  }

  return createPortal(
    <div className="ui-dialog-backdrop" onMouseDown={handleBackdropClick}>
      <section
        aria-describedby={description ? descriptionId : undefined}
        aria-labelledby={titleId}
        aria-modal="true"
        className={cx("ui-dialog", `ui-dialog--${size}`, className)}
        onKeyDown={handleKeyDown}
        onMouseDown={event => event.stopPropagation()}
        ref={dialogRef}
        role="dialog"
        tabIndex={-1}
      >
        <div className="ui-dialog__header">
          <Heading level={2} variant="panel" id={titleId}>
            {title}
          </Heading>
          {description && (
            <Text id={descriptionId} tone="muted" variant="bodySmall">
              {description}
            </Text>
          )}
        </div>
        {children && <div className="ui-dialog__body">{children}</div>}
        {error && <InlineError message={error} urgent />}
        {actions.length > 0 && (
          <div className="ui-dialog__actions">
            {actions.map((action, index) => (
              <Button
                data-dialog-cancel={index === 0 ? "true" : undefined}
                disabled={action.disabled}
                key={`${action.label}-${index}`}
                loading={action.loading}
                onClick={action.onClick}
                variant={action.variant || "secondary"}
              >
                {action.label}
              </Button>
            ))}
          </div>
        )}
      </section>
    </div>,
    document.body
  );
}

/** 用途：负责 getFocusable 的界面或数据处理职责。 */
function getFocusable(root: HTMLElement | null): HTMLElement[] {
  if (!root) return [];
  return Array.from(root.querySelectorAll<HTMLElement>(focusableSelector));
}
