import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";
import { cx } from "../utils";

type TextVariant = "body" | "bodySmall" | "caption" | "label" | "muted";
type TextTone =
  | "default"
  | "muted"
  | "danger"
  | "warning"
  | "success"
  | "info";

const variantClasses: Record<TextVariant, string> = {
  body: "text-mc-body",
  bodySmall: "text-mc-body-small",
  caption: "text-mc-caption",
  label: "text-mc-label font-mc-semibold",
  muted: "text-mc-body-small",
};

const toneClasses: Record<Exclude<TextTone, "default">, string> = {
  muted: "text-mc-muted",
  danger: "text-mc-danger",
  warning: "text-mc-warning",
  success: "text-mc-success",
  info: "text-mc-info",
};

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
  const colorClass =
    tone === "default"
      ? variant === "muted"
        ? "text-mc-muted"
        : "text-mc-text"
      : toneClasses[tone];

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <Component
      className={cx(
        "m-0 font-mc-sans font-mc-regular tracking-[0]",
        variantClasses[variant],
        colorClass,
        truncate && "overflow-hidden text-ellipsis whitespace-nowrap",
        className
      )}
      {...props}
    >
      {children}
    </Component>
  );
}
