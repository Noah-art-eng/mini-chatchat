import { HealthCard } from "./HealthCard";
import type { HealthResponse } from "../../api/system";

type HealthOverviewProps = {
  health: HealthResponse | null;
  status: "loading" | "ready" | "error";
};

export function HealthOverview({ health, status }: HealthOverviewProps) {
  return <HealthCard health={health} status={status} />;
}
