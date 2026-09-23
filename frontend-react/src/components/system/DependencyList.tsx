import { DependencyItem } from "./DependencyItem";

type DependencyListProps = {
  checks: Record<string, string>;
};

/** 用途：负责 DependencyList 的界面或数据处理职责。 */
export function DependencyList({ checks }: DependencyListProps) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <dl>
      {Object.entries(checks).map(([name, value]) => (
        <DependencyItem key={name} name={name} value={value} />
      ))}
    </dl>
  );
}
