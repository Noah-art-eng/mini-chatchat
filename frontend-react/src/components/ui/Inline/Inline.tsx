import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";
import { cx, type SpacingToken } from "../utils";
import "./Inline.css";

type InlineAlign = "start" | "center" | "end" | "stretch";
type InlineJustify = "start" | "center" | "end" | "between";

type InlineProps<T extends ElementType> = {
  align?: InlineAlign;
  as?: T;
  children: ReactNode;
  className?: string;
  gap?: SpacingToken;
  justify?: InlineJustify;
  wrap?: boolean;
} & Omit<ComponentPropsWithoutRef<T>, "as" | "children" | "className">;

/** 用途：负责 Inline 的界面或数据处理职责。 */
export function Inline<T extends ElementType = "div">({
  align = "center",
  as,
  children,
  className,
  gap = "2",
  justify = "start",
  wrap = false,
  ...props
}: InlineProps<T>) {
  const Component = as || "div";

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <Component
      className={cx(
        "ui-inline",
        `ui-inline--gap-${gap}`,
        `ui-inline--align-${align}`,
        `ui-inline--justify-${justify}`,
        wrap && "ui-inline--wrap",
        className
      )}
      {...props}
    >
      {children}
    </Component>
  );
}
