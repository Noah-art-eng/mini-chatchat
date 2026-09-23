import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";
import { cx, type SpacingToken } from "../utils";
import "./Stack.css";

type StackAlign = "stretch" | "start" | "center" | "end";

type StackProps<T extends ElementType> = {
  align?: StackAlign;
  as?: T;
  children: ReactNode;
  className?: string;
  gap?: SpacingToken;
} & Omit<ComponentPropsWithoutRef<T>, "as" | "children" | "className">;

/** 用途：负责 Stack 的界面或数据处理职责。 */
export function Stack<T extends ElementType = "div">({
  align = "stretch",
  as,
  children,
  className,
  gap = "4",
  ...props
}: StackProps<T>) {
  const Component = as || "div";

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <Component
      className={cx(
        "ui-stack",
        `ui-stack--gap-${gap}`,
        `ui-stack--align-${align}`,
        className
      )}
      {...props}
    >
      {children}
    </Component>
  );
}
