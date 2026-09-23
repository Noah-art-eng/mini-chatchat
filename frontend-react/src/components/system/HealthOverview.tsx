import { HealthCard } from "./HealthCard";
import type { HealthResponse } from "../../api/system";

type HealthOverviewProps = {
  health: HealthResponse | null;
  status: "loading" | "ready" | "error";
};

/** 用途：负责 HealthOverview 的界面或数据处理职责。 */
export function HealthOverview({ health, status }: HealthOverviewProps) {
  return <HealthCard health={health} status={status} />;
}
