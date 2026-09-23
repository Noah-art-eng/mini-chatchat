/** 用途：负责 cx 的界面或数据处理职责。 */
export function cx(
  ...classes: Array<string | false | null | undefined>
): string {
  return classes.filter(Boolean).join(" ");
}

export type UiSize = "sm" | "md" | "lg";

export type SpacingToken =
  | "1"
  | "2"
  | "3"
  | "4"
  | "5"
  | "6"
  | "8"
  | "10"
  | "12"
  | "16";
