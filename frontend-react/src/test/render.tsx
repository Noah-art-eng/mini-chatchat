import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { I18nProvider } from "../i18n";

/** 用途：负责 renderWithI18n 的界面或数据处理职责。 */
export function renderWithI18n(ui: ReactElement) {
  return render(<I18nProvider>{ui}</I18nProvider>);
}

