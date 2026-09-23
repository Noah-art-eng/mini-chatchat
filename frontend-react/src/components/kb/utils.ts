/** 用途：负责 safeFileName 的界面或数据处理职责。 */
export function safeFileName(filename: string) {
  return filename.replace(/[^a-zA-Z0-9._-]/g, "-");
}
