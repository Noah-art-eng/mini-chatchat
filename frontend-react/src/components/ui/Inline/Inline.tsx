import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";
import { cx, type SpacingToken } from "../utils";

type InlineAlign = "start" | "center" | "end" | "stretch";
type InlineJustify = "start" | "center" | "end" | "between";

const alignClasses: Record<InlineAlign, string> = {
  start: "items-start",
  center: "items-center",
  end: "items-end",
  stretch: "items-stretch",
};

const justifyClasses: Record<InlineJustify, string> = {
  start: "justify-start",
  center: "justify-center",
  end: "justify-end",
  between: "justify-between",
};

const gapClasses: Record<SpacingToken, string> = {
  "1": "gap-mc-1",
  "2": "gap-mc-2",
  "3": "gap-mc-3",
  "4": "gap-mc-4",
  "5": "gap-mc-5",
  "6": "gap-mc-6",
  "8": "gap-mc-8",
  "10": "gap-mc-10",
  "12": "gap-mc-12",
  "16": "gap-mc-16",
};

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
        "flex min-w-0 flex-row",
        gapClasses[gap],
        alignClasses[align],
        justifyClasses[justify],
        wrap && "flex-wrap",
        className
      )}
      {...props}
    >
      {children}
    </Component>
  );
}
