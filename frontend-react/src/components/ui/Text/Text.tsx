import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";
import { cx } from "../utils";
import "./Text.css";

type TextVariant = "body" | "bodySmall" | "caption" | "label" | "muted";
type TextTone =
  | "default"
  | "muted"
  | "danger"
  | "warning"
  | "success"
  | "info";

type TextProps<T extends ElementType> = {
  as?: T;
  children: ReactNode;
  className?: string;
  tone?: TextTone;
  truncate?: boolean;
  variant?: TextVariant;
} & Omit<ComponentPropsWithoutRef<T>, "as" | "children" | "className">;

/** 用途：负责 Text 的界面或数据处理职责。 */
export function Text<T extends ElementType = "p">({
  as,
  children,
  className,
  tone = "default",
  truncate = false,
  variant = "body",
  ...props
}: TextProps<T>) {
  const Component = as || "p";

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <Component
      className={cx(
        "ui-text",
        `ui-text--${variant}`,
        `ui-text--tone-${tone}`,
        truncate && "ui-text--truncate",
        className
      )}
      {...props}
    >
      {children}
    </Component>
  );
}
