export const ONBOARDING_COMPLETED_KEY = "mini-chatchat:onboarding-completed";
export const DEVELOPER_MODE_INTRO_SEEN_KEY =
  "mini-chatchat:developer-mode-intro-seen";

function canUseStorage() {
  // 服务端渲染或测试环境可能没有 window；此时不让引导偏好访问抛错。
  return typeof window !== "undefined" && Boolean(window.localStorage);
}

export function isOnboardingCompleted() {
  // 无法使用浏览器存储时按“已完成”处理，避免反复弹出无法持久化的引导。
  if (!canUseStorage()) return true;
  return localStorage.getItem(ONBOARDING_COMPLETED_KEY) === "true";
}

export function setOnboardingCompleted(completed = true) {
  if (!canUseStorage()) return;
  localStorage.setItem(ONBOARDING_COMPLETED_KEY, String(completed));
}

export function isDeveloperModeIntroSeen() {
  // Developer Mode 的说明单独记录，不与首次使用引导互相覆盖。
  if (!canUseStorage()) return true;
  return localStorage.getItem(DEVELOPER_MODE_INTRO_SEEN_KEY) === "true";
}

export function setDeveloperModeIntroSeen(seen = true) {
  if (!canUseStorage()) return;
  localStorage.setItem(DEVELOPER_MODE_INTRO_SEEN_KEY, String(seen));
}
