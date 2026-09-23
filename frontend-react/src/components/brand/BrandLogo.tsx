import type { SVGProps } from "react";

type BrandLogoProps = {
  size?: number;
  title?: string;
} & Omit<SVGProps<SVGSVGElement>, "children" | "height" | "viewBox" | "width">;

/** 用途：负责 BrandLogo 的界面或数据处理职责。 */
export function BrandLogo({
  size = 40,
  title = "Mini ChatChat",
  ...props
}: BrandLogoProps) {
  const titleId = "mini-chatchat-logo-title";

  /** 用途：负责 return 的界面或数据处理职责。 */
  return (
    <svg
      aria-labelledby={title ? titleId : undefined}
      height={size}
      role={title ? "img" : undefined}
      viewBox="0 0 48 48"
      width={size}
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      {title && <title id={titleId}>{title}</title>}
      <rect fill="#E8F3EE" height="48" rx="14" width="48" />
      <path
        d="M13 17.8C13 13.5 16.5 10 20.8 10h9.7c4.3 0 7.8 3.5 7.8 7.8v5.4c0 4.3-3.5 7.8-7.8 7.8h-6.1l-7.1 5.6c-.8.6-1.9 0-1.9-1v-5.2A7.8 7.8 0 0 1 13 23.2v-5.4Z"
        fill="#3F7D62"
      />
      <path
        d="M18.2 18.4h13.1M18.2 23.2h9.2"
        fill="none"
        stroke="#FFFFFF"
        strokeLinecap="round"
        strokeWidth="2.6"
      />
      <circle cx="34.4" cy="14.3" fill="#6FB7A1" r="3.2" />
      <circle cx="37.8" cy="28.8" fill="#4D8C70" r="2.2" />
      <path
        d="M34.4 17.5v4.8c0 2.3 1.2 4.4 3.1 5.7"
        fill="none"
        stroke="#BDE2D6"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
    </svg>
  );
}
