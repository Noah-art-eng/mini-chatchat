import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useState
} from "react";
import { en } from "./en";
import { zhCN } from "./zh-CN";

const LANGUAGE_STORAGE_KEY = "mini-chatchat:language";

export type LanguageCode = "en" | "zh-CN";

const dictionaries = {
  en,
  "zh-CN": zhCN
};

type I18nContextValue = {
  language: LanguageCode;
  setLanguage: (language: LanguageCode) => void;
  t: (key: string, values?: Record<string, string | number>) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

/** 用途：负责 detectLanguage 的界面或数据处理职责。 */
function detectLanguage(): LanguageCode {
  const saved = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (saved === "en" || saved === "zh-CN") return saved;

  const browserLanguage = navigator.language.toLowerCase();
  return browserLanguage.startsWith("zh") ? "zh-CN" : "en";
}

/** 用途：负责 interpolate 的界面或数据处理职责。 */
function interpolate(template: string, values?: Record<string, string | number>) {
  if (!values) return template;

  return Object.entries(values).reduce(
    (text, [key, value]) => text.split(`{{${key}}}`).join(String(value)),
    template
  );
}

/** 用途：负责 getTranslation 的界面或数据处理职责。 */
function getTranslation(language: LanguageCode, key: string) {
  const parts = key.split(".");
  let value: unknown = dictionaries[language];

  for (const part of parts) {
    if (!value || typeof value !== "object" || !(part in value)) {
      return key;
    }
    value = (value as Record<string, unknown>)[part];
  }

  return typeof value === "string" ? value : key;
}

/** 用途：负责 I18nProvider 的界面或数据处理职责。 */
export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<LanguageCode>(() =>
    /** 用途：负责 detectLanguage 的界面或数据处理职责。 */
    detectLanguage()
  );

  const setLanguage = useCallback((nextLanguage: LanguageCode) => {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLanguage);
    /** 用途：负责 setLanguageState 的界面或数据处理职责。 */
    setLanguageState(nextLanguage);
  }, []);

  const t = useCallback(
    (key: string, values?: Record<string, string | number>) =>
      /** 用途：负责 interpolate 的界面或数据处理职责。 */
      interpolate(getTranslation(language, key), values),
    [language]
  );

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      t
    }),
    [language, setLanguage, t]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

/** 用途：负责 useI18n 的界面或数据处理职责。 */
export function useI18n() {
  const context = useContext(I18nContext);

  if (!context) {
    throw new Error("useI18n must be used within I18nProvider.");
  }

  return context;
}
