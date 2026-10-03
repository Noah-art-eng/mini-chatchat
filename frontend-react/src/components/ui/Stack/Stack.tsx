import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";
import { cx, type SpacingToken } from "../utils";

type StackAlign = "stretch" | "start" | "center" | "end";

const alignClasses: Record<StackAlign, string> = {
  stretch: "items-stretch",
  start: "items-start",
  center: "items-center",
  end: "items-end",
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

type StackProps<T extends ElementType> = {
  align?: StackAlign;
  as?: T;
  children: ReactNode;
  className?: string;
  gap?: SpacingToken;
} & Omit<ComponentPropsWithoutRef<T>, "as" | "children" | "className">;

export function Stack<T extends ElementType = "div">({
  align = "stretch",
  as,
  children,
  className,
  gap = "4",
  ...props
}: StackProps<T>) {
  const Component = as || "div";

  return (
    <Component
      className={cx(
        "flex flex-col",
        gapClasses[gap],
        alignClasses[align],
        className
      )}
      {...props}
    >
      {children}
    </Component>
  );
}
