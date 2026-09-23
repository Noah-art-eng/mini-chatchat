/** 用途：负责 formatJson 的界面或数据处理职责。 */
export function formatJson(value: unknown) {
  if (value === undefined || value === null) return "None";
  return JSON.stringify(value, null, 2);
}

/** 用途：负责 isRecord 的界面或数据处理职责。 */
export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** 用途：负责 asText 的界面或数据处理职责。 */
export function asText(value: unknown) {
  return typeof value === "string" ? value : "";
}

/** 用途：负责 asNumber 的界面或数据处理职责。 */
export function asNumber(value: unknown) {
  return typeof value === "number" ? value : null;
}

/** 用途：负责 getPreview 的界面或数据处理职责。 */
export function getPreview(value: unknown, maxLength = 900) {
  const text = asText(value);
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}...`;
}

export type Translate = (
  key: string,
  values?: Record<string, string | number>
) => string;
