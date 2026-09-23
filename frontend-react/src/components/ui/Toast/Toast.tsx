import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState
} from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { Icon } from "../Icon";
import { IconButton } from "../IconButton";
import { Text } from "../Text";
import { cx } from "../utils";
import "./Toast.css";

type ToastVariant = "success" | "info" | "warning" | "error";

type ToastAction = {
  label: string;
  onClick: () => void;
};

type ToastItem = {
  action?: ToastAction;
  duration?: number;
  id: string;
  message: string;
  variant: ToastVariant;
};

type AddToastInput = Omit<ToastItem, "id"> & {
  id?: string;
};

type ToastContextValue = {
  dismissToast: (id: string) => void;
  showToast: (toast: AddToastInput) => string;
};

const ToastContext = createContext<ToastContextValue | null>(null);
const MAX_TOASTS = 3;

/** 用途：负责 ToastProvider 的界面或数据处理职责。 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timersRef = useRef<Map<string, number>>(new Map());

  const dismissToast = useCallback((id: string) => {
    const timer = timersRef.current.get(id);
    if (timer) window.clearTimeout(timer);
    timersRef.current.delete(id);
    /** 用途：负责 setToasts 的界面或数据处理职责。 */
    setToasts(current => current.filter(toast => toast.id !== id));
  }, []);

  const scheduleDismiss = useCallback(
    (toast: ToastItem) => {
      const duration = toast.duration ?? (toast.variant === "error" ? 8000 : 4200);
      if (duration <= 0) return;
      const timer = window.setTimeout(() => dismissToast(toast.id), duration);
      timersRef.current.set(toast.id, timer);
    },
    [dismissToast]
  );

  const showToast = useCallback(
    (toast: AddToastInput) => {
      const id =
        toast.id ||
        `${toast.variant}-${toast.message}-${Date.now().toString(36)}`;
      const nextToast = { ...toast, id };

      /** 用途：负责 setToasts 的界面或数据处理职责。 */
      setToasts(current => {
        const deduped = current.filter(
          item => item.message !== toast.message || item.variant !== toast.variant
        );
        return [nextToast, ...deduped].slice(0, MAX_TOASTS);
      });
      /** 用途：负责 scheduleDismiss 的界面或数据处理职责。 */
      scheduleDismiss(nextToast);
      return id;
    },
    [scheduleDismiss]
  );

  const value = useMemo(
    () => ({ dismissToast, showToast }),
    [dismissToast, showToast]
  );

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <ToastContext.Provider value={value}>
      {children}
      {createPortal(
        <div
          aria-live="polite"
          className="ui-toast-viewport"
          data-testid="toast-viewport"
        >
          {toasts.map(toast => (
            <article
              className={cx("ui-toast", `ui-toast--${toast.variant}`)}
              key={toast.id}
              onFocus={() => pauseToast(toast.id, timersRef.current)}
              onMouseEnter={() => pauseToast(toast.id, timersRef.current)}
            >
              <Text as="p" variant="bodySmall">
                {toast.message}
              </Text>
              {toast.action && (
                <button
                  className="ui-toast__action"
                  onClick={toast.action.onClick}
                  type="button"
                >
                  {toast.action.label}
                </button>
              )}
              <IconButton
                aria-label="Dismiss notification"
                onClick={() => dismissToast(toast.id)}
                size="sm"
                variant="ghost"
              >
                <Icon icon={X} size="sm" />
              </IconButton>
            </article>
          ))}
        </div>,
        document.body
      )}
    </ToastContext.Provider>
  );
}

/** 用途：负责 useToast 的界面或数据处理职责。 */
export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
}

/** 用途：负责 pauseToast 的界面或数据处理职责。 */
function pauseToast(id: string, timers: Map<string, number>) {
  const timer = timers.get(id);
  if (!timer) return;
  window.clearTimeout(timer);
  timers.delete(id);
}
