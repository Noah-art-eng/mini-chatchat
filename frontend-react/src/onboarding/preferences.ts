export const ONBOARDING_COMPLETED_KEY = "mini-chatchat:onboarding-completed";
export const DEVELOPER_MODE_INTRO_SEEN_KEY =
  "mini-chatchat:developer-mode-intro-seen";

/** 用途：负责 canUseStorage 的界面或数据处理职责。 */
function canUseStorage() {
  return typeof window !== "undefined" && Boolean(window.localStorage);
}

/** 用途：负责 isOnboardingCompleted 的界面或数据处理职责。 */
export function isOnboardingCompleted() {
  if (!canUseStorage()) return true;
  return localStorage.getItem(ONBOARDING_COMPLETED_KEY) === "true";
}

/** 用途：负责 setOnboardingCompleted 的界面或数据处理职责。 */
export function setOnboardingCompleted(completed = true) {
  if (!canUseStorage()) return;
  localStorage.setItem(ONBOARDING_COMPLETED_KEY, String(completed));
}

/** 用途：负责 isDeveloperModeIntroSeen 的界面或数据处理职责。 */
export function isDeveloperModeIntroSeen() {
  if (!canUseStorage()) return true;
  return localStorage.getItem(DEVELOPER_MODE_INTRO_SEEN_KEY) === "true";
}

/** 用途：负责 setDeveloperModeIntroSeen 的界面或数据处理职责。 */
export function setDeveloperModeIntroSeen(seen = true) {
  if (!canUseStorage()) return;
  localStorage.setItem(DEVELOPER_MODE_INTRO_SEEN_KEY, String(seen));
}
