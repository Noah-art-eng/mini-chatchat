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

const sizeClasses: Record<DialogSize, string> = {
  sm: "w-[min(100%,var(--dialog-width-sm))]",
  md: "w-[min(100%,var(--dialog-width-md))]",
  lg: "w-[min(100%,var(--dialog-width-lg))]",
};

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

    return () => {
      previousFocusRef.current?.focus?.();
    };
  }, [initialFocus, isOpen]);

  if (!isOpen) return null;

  function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === "Escape" && !preventClose) {
      event.preventDefault();
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

  function handleBackdropClick() {
    if (!preventClose) onClose();
  }

  return createPortal(
    <div
      className="fixed top-[0px] right-[0px] bottom-[0px] left-[0px] z-[var(--z-dialog)] flex items-center justify-center bg-[color-mix(in_srgb,var(--color-text-primary)_18%,transparent)] p-mc-6 max-[480px]:items-end max-[480px]:p-mc-3 max-[480px]:pb-[calc(var(--space-3)+var(--safe-area-bottom))]"
      onMouseDown={handleBackdropClick}
    >
      <section
        aria-describedby={description ? descriptionId : undefined}
        aria-labelledby={titleId}
        aria-modal="true"
        className={cx(
          "ui-dialog grid max-h-[min(720px,calc(100vh-var(--space-12)))] gap-mc-5 overflow-auto rounded-mc-xl border border-solid border-mc-border-subtle bg-mc-elevated p-mc-6 shadow-mc-md focus:outline-none max-[480px]:max-h-[var(--bottom-sheet-max-height)] max-[480px]:rounded-[var(--radius-xl)_var(--radius-xl)_var(--radius-lg)_var(--radius-lg)] max-[480px]:p-mc-5",
          sizeClasses[size],
          className
        )}
        onKeyDown={handleKeyDown}
        onMouseDown={event => event.stopPropagation()}
        ref={dialogRef}
        role="dialog"
        tabIndex={-1}
      >
        <div className="ui-dialog__header grid gap-mc-3">
          <Heading level={2} variant="panel" id={titleId}>
            {title}
          </Heading>
          {description && (
            <Text id={descriptionId} tone="muted" variant="bodySmall">
              {description}
            </Text>
          )}
        </div>
        {children && <div className="grid gap-mc-3">{children}</div>}
        {error && <InlineError message={error} urgent />}
        {actions.length > 0 && (
          <div className="flex items-center justify-end gap-mc-3 max-[480px]:flex-col-reverse max-[480px]:items-stretch">
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

function getFocusable(root: HTMLElement | null): HTMLElement[] {
  if (!root) return [];
  return Array.from(root.querySelectorAll<HTMLElement>(focusableSelector));
}
