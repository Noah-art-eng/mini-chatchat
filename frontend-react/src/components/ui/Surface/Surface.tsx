import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";
import { cx } from "../utils";
import "./Surface.css";

type SurfaceVariant = "base" | "subtle" | "elevated" | "critical";

type SurfaceProps<T extends ElementType> = {
  as?: T;
  children: ReactNode;
  className?: string;
  interactive?: boolean;
  variant?: SurfaceVariant;
} & Omit<ComponentPropsWithoutRef<T>, "as" | "children" | "className">;

/** 用途：负责 Surface 的界面或数据处理职责。 */
export function Surface<T extends ElementType = "div">({
  as,
  children,
  className,
  interactive = false,
  variant = "base",
  ...props
}: SurfaceProps<T>) {
  const Component = as || "div";

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <Component
      className={cx(
        "ui-surface",
        `ui-surface--${variant}`,
        interactive && "ui-surface--interactive",
        className
      )}
      {...props}
    >
      {children}
    </Component>
  );
}
