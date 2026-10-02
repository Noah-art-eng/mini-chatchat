import { Activity } from "lucide-react";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { HealthResponse } from "../../api/system";
import { cx } from "../ui/utils";

type SystemHeaderProps = {
  health: HealthResponse | null;
  status: "loading" | "ready" | "error";
};

/** 用途：负责 SystemHeader 的界面或数据处理职责。 */
export function SystemHeader({ health, status }: SystemHeaderProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <header className="page-header system-hero relative flex items-start gap-[14px] overflow-hidden rounded-mc-lg border border-solid border-transparent bg-transparent px-0 pt-mc-2 pb-mc-4 [box-shadow:none] max-[720px]:grid">
      <div aria-hidden="true">
        <Icon icon={Activity} size="lg" tone="info" />
      </div>
      <div>
        <p className="eyebrow">{t("nav.settings")}</p>
        <h1>{t("settings.title")}</h1>
        <p>{t("settings.subtitle")}</p>
      </div>
      <div
        className={cx(
          "system-health-orb relative z-[1] grid min-w-[220px] self-stretch gap-[5px] rounded-[18px] border border-solid border-mc-border-subtle bg-mc-surface p-mc-4 [box-shadow:none] max-[720px]:min-w-0 [&>span]:text-mc-caption [&>span]:font-[800] [&>span]:text-mc-muted [&>span]:uppercase [&>strong]:text-[18px]",
          `system-health-${health?.status || status}`
        )}
      >
        <span>{t("settings.health")}</span>
        <strong>{health?.status || status}</strong>
      </div>
    </header>
  );
}
