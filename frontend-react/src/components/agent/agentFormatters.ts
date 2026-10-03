export function formatJson(value: unknown) {
  if (value === undefined || value === null) return "None";
  return JSON.stringify(value, null, 2);
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function asText(value: unknown) {
  return typeof value === "string" ? value : "";
}

export function asNumber(value: unknown) {
  return typeof value === "number" ? value : null;
}

export function getPreview(value: unknown, maxLength = 900) {
  const text = asText(value);
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}...`;
}

export type Translate = (
  key: string,
  values?: Record<string, string | number>
) => string;
