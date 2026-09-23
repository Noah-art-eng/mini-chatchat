import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { cx } from "../utils";
import "./Heading.css";

type HeadingVariant = "display" | "page" | "section" | "panel" | "card";
type HeadingLevel = 1 | 2 | 3 | 4;

type HeadingProps = {
  children: ReactNode;
  className?: string;
  description?: ReactNode;
  eyebrow?: ReactNode;
  level?: HeadingLevel;
  variant?: HeadingVariant;
} & Omit<ComponentPropsWithoutRef<"h1">, "children" | "className">;

/** 用途：负责 Heading 的界面或数据处理职责。 */
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

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <div className={cx("ui-heading-block", className)}>
      {eyebrow && <p className="ui-heading__eyebrow">{eyebrow}</p>}
      <Component className={cx("ui-heading", `ui-heading--${variant}`)} {...props}>
        {children}
      </Component>
      {description && <p className="ui-heading__description">{description}</p>}
    </div>
  );
}
