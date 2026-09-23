import { Boxes } from "lucide-react";
import { DependencyList } from "./DependencyList";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { HealthDepsResponse } from "../../api/system";

type DependencySectionProps = {
  deps: HealthDepsResponse | null;
  status: "loading" | "ready" | "error";
};

/** 用途：负责 DependencySection 的界面或数据处理职责。 */
export function DependencySection({ deps, status }: DependencySectionProps) {
  const { t } = useI18n();

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <article className="settings-card">
      <span className={`settings-badge status-${deps?.status || status}`}>
        {deps?.status || t("common.loading")}
      </span>
      <h2><Icon icon={Boxes} size="sm" tone="database" />{t("settings.dependencies")}</h2>
      <DependencyList checks={deps?.checks || {}} />
    </article>
  );
}
