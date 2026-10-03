import { Boxes } from "lucide-react";
import { DependencyList } from "./DependencyList";
import { useI18n } from "../../i18n";
import { Icon } from "../ui";
import type { HealthDepsResponse } from "../../api/system";
import { systemBadgeClassName, systemCardClassName } from "./systemStyles";

type DependencySectionProps = {
  deps: HealthDepsResponse | null;
  status: "loading" | "ready" | "error";
};

export function DependencySection({ deps, status }: DependencySectionProps) {
  const { t } = useI18n();

  return (
    <article className={systemCardClassName}>
      <span className={`${systemBadgeClassName} status-${deps?.status || status}`}>
        {deps?.status || t("common.loading")}
      </span>
      <h2><Icon icon={Boxes} size="sm" tone="database" />{t("settings.dependencies")}</h2>
      <DependencyList checks={deps?.checks || {}} />
    </article>
  );
}
