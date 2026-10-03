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

function detectLanguage(): LanguageCode {
  // 用户手动选择优先；没有记录时才根据浏览器语言决定首次显示语言。
  const saved = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (saved === "en" || saved === "zh-CN") return saved;

  const browserLanguage = navigator.language.toLowerCase();
  return browserLanguage.startsWith("zh") ? "zh-CN" : "en";
}

function interpolate(template: string, values?: Record<string, string | number>) {
  if (!values) return template;

  return Object.entries(values).reduce(
    (text, [key, value]) => text.split(`{{${key}}}`).join(String(value)),
    template
  );
}

function getTranslation(language: LanguageCode, key: string) {
  // 翻译键按 `section.field` 逐层查找，缺失时返回原键，避免界面渲染失败。
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

export function I18nProvider({ children }: { children: ReactNode }) {
  // 语言切换同时写入 localStorage，使刷新后继续使用用户选择。
  const [language, setLanguageState] = useState<LanguageCode>(() =>
    detectLanguage()
  );

  const setLanguage = useCallback((nextLanguage: LanguageCode) => {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLanguage);
    setLanguageState(nextLanguage);
  }, []);

  const t = useCallback(
    (key: string, values?: Record<string, string | number>) =>
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

export function useI18n() {
  const context = useContext(I18nContext);

  if (!context) {
    throw new Error("useI18n must be used within I18nProvider.");
  }

  return context;
}
