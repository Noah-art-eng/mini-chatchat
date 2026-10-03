import { DependencyItem } from "./DependencyItem";

type DependencyListProps = {
  checks: Record<string, string>;
};

export function DependencyList({ checks }: DependencyListProps) {
  return (
    <dl>
      {Object.entries(checks).map(([name, value]) => (
        <DependencyItem key={name} name={name} value={value} />
      ))}
    </dl>
  );
}
