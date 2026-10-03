import type { ReactNode } from "react";
import { useAuth } from "./AuthContext";

type GuestRouteProps = {
  children: ReactNode;
  fallback?: ReactNode;
};

export function GuestRoute({ children, fallback = null }: GuestRouteProps) {
  const auth = useAuth();

  if (!auth.session.isGuest) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
