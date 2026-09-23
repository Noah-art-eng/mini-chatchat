type DependencyItemProps = {
  name: string;
  value: string;
};

/** 用途：负责 DependencyItem 的界面或数据处理职责。 */
export function DependencyItem({ name, value }: DependencyItemProps) {
  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div>
      <dt>{name}</dt>
      <dd>
        <span className={`status status-${value}`}>{value}</span>
      </dd>
    </div>
  );
}
