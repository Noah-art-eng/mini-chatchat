type DependencyItemProps = {
  name: string;
  value: string;
};

export function DependencyItem({ name, value }: DependencyItemProps) {
  return (
    <div>
      <dt>{name}</dt>
      <dd>
        <span className={`status status-${value}`}>{value}</span>
      </dd>
    </div>
  );
}
