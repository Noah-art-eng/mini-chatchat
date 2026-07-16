import type { ReactNode } from "react";

type AppLayoutProps = {
  sidebar: ReactNode;
  main: ReactNode;
  aside: ReactNode;
};

export function AppLayout({ sidebar, main, aside }: AppLayoutProps) {
  return (
    <div className="app-layout">
      <aside className="app-sidebar">{sidebar}</aside>
      <main className="app-main">{main}</main>
      <aside className="app-aside">{aside}</aside>
    </div>
  );
}
