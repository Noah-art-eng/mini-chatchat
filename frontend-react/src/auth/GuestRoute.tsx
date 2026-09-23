import type { ReactNode } from "react";
import { useAuth } from "./AuthContext";

type GuestRouteProps = {
  children: ReactNode;
  fallback?: ReactNode;
};

/** 用途：负责 GuestRoute 的界面或数据处理职责。 */
export function GuestRoute({ children, fallback = null }: GuestRouteProps) {
  const auth = useAuth();

  if (!auth.session.isGuest) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
