import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { cx } from "../utils";

type HeadingVariant = "display" | "page" | "section" | "panel" | "card";
type HeadingLevel = 1 | 2 | 3 | 4;

const variantClasses: Record<HeadingVariant, string> = {
  display: "text-mc-display font-mc-bold",
  page: "text-mc-heading font-mc-bold",
  section: "text-mc-title font-mc-semibold",
  panel: "text-mc-body font-mc-semibold leading-[var(--line-height-compact)]",
  card: "text-mc-body font-mc-semibold leading-[var(--line-height-compact)]",
};

type HeadingProps = {
  children: ReactNode;
  className?: string;
  description?: ReactNode;
  eyebrow?: ReactNode;
  level?: HeadingLevel;
  variant?: HeadingVariant;
} & Omit<ComponentPropsWithoutRef<"h1">, "children" | "className">;

export function Heading({
  children,
  className,
  description,
  eyebrow,
  level = 2,
  variant = "section",
  ...props
}: HeadingProps) {
  const Component = `h${level}` as const;

  return (
    <div className={cx("grid gap-mc-2", className)}>
      {eyebrow && (
        <p className="m-0 font-mc-sans text-mc-label font-mc-semibold text-mc-muted">
          {eyebrow}
        </p>
      )}
      <Component
        className={cx(
          "m-0 font-mc-sans tracking-[0] text-mc-text",
          variantClasses[variant]
        )}
        {...props}
      >
        {children}
      </Component>
      {description && (
        <p className="m-0 font-mc-sans text-mc-body-small text-mc-muted">
          {description}
        </p>
      )}
    </div>
  );
}
