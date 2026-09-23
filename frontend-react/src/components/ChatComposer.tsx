import type { FormEvent, KeyboardEvent } from "react";
import { ArrowUp, LoaderCircle } from "lucide-react";
import { Icon } from "./ui";
import { useI18n } from "../i18n";

type ChatComposerProps = {
  disabledReason?: string | null;
  input: string;
  isSending: boolean;
  onChangeInput: (value: string) => void;
  onSubmit: () => void;
};

/** 用途：负责 ChatComposer 的界面或数据处理职责。 */
export function ChatComposer({
  disabledReason,
  input,
  isSending,
  onChangeInput,
  onSubmit
}: ChatComposerProps) {
  const { t } = useI18n();
  const disabled = isSending || input.trim().length === 0 || Boolean(disabledReason);

  /** 用途：负责 handleSubmit 的界面或数据处理职责。 */
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (disabled) return;
    /** 用途：负责 onSubmit 的界面或数据处理职责。 */
    onSubmit();
  }

  /** 用途：负责 handleKeyDown 的界面或数据处理职责。 */
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!disabled) onSubmit();
    }
  }

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <form className="chat-composer" onSubmit={handleSubmit}>
      {disabledReason && <p className="composer-warning">{disabledReason}</p>}
      <div className="composer-topline">
        <span>{t("chat.composerHint")}</span>
        <span>{isSending ? t("chat.streamingNow") : t("chat.enterToSend")}</span>
      </div>
      <div className="composer-input-row">
        <textarea
          aria-label={t("chat.composerPlaceholder")}
          onKeyDown={handleKeyDown}
          onChange={event => onChangeInput(event.target.value)}
          placeholder={t("chat.composerPlaceholder")}
          rows={2}
          value={input}
        />
        <button
          aria-label={isSending ? t("chat.sending") : t("chat.send")}
          className="send-button"
          disabled={disabled}
          type="submit"
        >
          <Icon
            icon={isSending ? LoaderCircle : ArrowUp}
            size="sm"
            tone={isSending ? "muted" : "default"}
          />
        </button>
      </div>
    </form>
  );
}
