import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";
import { cx } from "../utils";

type SurfaceVariant = "base" | "subtle" | "elevated" | "critical";

const variantClasses: Record<SurfaceVariant, string> = {
  base: "bg-mc-surface",
  subtle: "bg-mc-subtle",
  elevated: "bg-mc-elevated shadow-mc-sm",
  critical: "border-mc-danger-soft bg-mc-danger-soft",
};

type SurfaceProps<T extends ElementType> = {
  as?: T;
  children: ReactNode;
  className?: string;
  interactive?: boolean;
  variant?: SurfaceVariant;
} & Omit<ComponentPropsWithoutRef<T>, "as" | "children" | "className">;

export function Surface<T extends ElementType = "div">({
  as,
  children,
  className,
  interactive = false,
  variant = "base",
  ...props
}: SurfaceProps<T>) {
  const Component = as || "div";

  return (
    <Component
      className={cx(
        "rounded-mc-lg border border-solid border-mc-border-subtle",
        variantClasses[variant],
        interactive &&
          "transition-[background-color,border-color,box-shadow] duration-[var(--motion-duration-fast)] ease-[var(--motion-ease-standard)] hover:border-mc-border hover:shadow-mc-xs",
        className
      )}
      {...props}
    >
      {children}
    </Component>
  );
}
